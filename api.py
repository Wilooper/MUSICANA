from flask import Flask, request, jsonify, send_file,render_template
from flask_cors import CORS
from ytmusicapi import YTMusic,OAuthCredentials
from pytubefix import YouTube
from pytubefix.exceptions import AgeRestrictedError, VideoUnavailable
import os
import tempfile
import logging
from urllib.parse import quote
import requests
from downloader import start_async_download, get_download_status, get_download_file
from flask_caching import Cache
from lyrics import start_lyrica
import subprocess
import time
import requests
import uuid
import re
import hashlib
import json
from pytubefix import Search
from auth_helper import initialize_auth


ytmusic = initialize_auth()


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
#Initialize Caching
cache = Cache(app, config={
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": "cache",
    "CACHE_DEFAULT_TIMEOUT": 300
})

#authentication


ORIGIN = "https://music.youtube.com"

def get_oauth():
    """Try loading OAuth credentials."""
    try:
        return YTMusic("oauth.json")
    except Exception as e:
        print("⚠ OAuth failed:", e)
        return None


def load_header():
    try:
        with open("header.json", "r") as f:
            return json.load(f)
    except:
        return None


def extract_sapisid(cookie_string):
    """Extract SAPISID from cookies."""
    match = re.search(r"SAPISID=([^;]+)", cookie_string)
    if not match:
        raise Exception("❌ SAPISID not found in cookies!")
    return match.group(1)


def build_dynamic_auth():
    """Builds a fresh SAPISIDHASH for header.json authentication."""
    header = load_header()
    if not header:
        return None

    cookie = header.get("cookie", "")
    if not cookie:
        print("❌ No cookie string found inside header.json")
        return None

    try:
        sapisid = extract_sapisid(cookie)
    except Exception as e:
        print(e)
        return None

    timestamp = int(time.time())
    message = f"{timestamp} {sapisid} {ORIGIN}"
    digest = hashlib.sha1(message.encode()).hexdigest()

    # Insert dynamic Authorization header
    header["authorization"] = f"SAPISIDHASH {timestamp}_{digest}"
    header["origin"] = ORIGIN
    header["referer"] = ORIGIN
    header["x-goog-authuser"] = "0"
    header["user-agent"] = header.get("user-agent",
        "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome Mobile Safari")

    return header


def get_header_auth():
    """Return YTMusic instance using dynamic header auth."""
    auth = build_dynamic_auth()
    if not auth:
        return None

    try:
        return YTMusic(auth)
    except Exception as e:
        print("⚠ Header authentication failed:", e)
        return None


def initialize_auth():
    """
    MAIN FUNCTION you call in api.py:
      1. Try OAuth
      2. Try Header
      3. Use guest mode (no auth)
    """

    print("\n🔍 Checking authentication methods...\n")

    # 1️⃣ Try OAuth first
    ytm = get_oauth()
    if ytm:
        print("✅ Logged in using OAuth (oauth.json)")
        return ytm

    # 2️⃣ Try header.json
    ytm = get_header_auth()
    if ytm:
        print("✅ Logged in using header.json (SAPISIDHASH auth)")
        return ytm

    # 3️⃣ Guest mode
    print("⚠ No valid authentication file found. Running in guest mode.")
    print("   ➜ Playlist / library access will NOT work.")
    return YTMusic()  # Guest (no auth)


# Helper function to clean and format song/video data
def format_track_data(track, fetch_missing_thumbnails=False):
    """
    Universal formatter for YTMusic search/track objects:
    - Works for songs, albums, playlists, artists
    - Always provides thumbnails sorted high→low quality
    - Falls back to YouTube defaults if needed
    """
    if not isinstance(track, dict):
        return {
            "title": "",
            "videoId": "",
            "artists": [],
            "album": "",
            "duration": "",
            "thumbnails": []
        }

    # --- Extract videoId or browseId depending on type ---
    video_id = track.get("videoId") or track.get("browseId") or ""

    # --- Extract title ---
    title = track.get("title", "")
    if isinstance(title, dict):  # sometimes YTMusic wraps in dict
        title = title.get("text", "")

    # --- Extract artists safely ---
    artists = []
    if isinstance(track.get("artists"), list):
        for artist in track["artists"]:
            if isinstance(artist, dict) and "name" in artist:
                artists.append(artist["name"])

    # --- Extract album safely ---
    album = ""
    if isinstance(track.get("album"), dict):
        album = track["album"].get("name", "")

    # --- Extract duration safely ---
    duration = track.get("duration", "")

    # --- Thumbnails handling ---
    thumbnails = []
    thumbs = []
    if isinstance(track.get("thumbnails"), list):
        thumbs = track["thumbnails"]
    elif isinstance(track.get("thumbnail"), dict) and isinstance(track["thumbnail"].get("thumbnails"), list):
        thumbs = track["thumbnail"]["thumbnails"]
    elif isinstance(track.get("thumbnail"), list):  # sometimes it's already a list
        thumbs = track["thumbnail"]
    elif isinstance(track.get("thumbnailRenderer"), dict):
        mtr = track["thumbnailRenderer"].get("musicThumbnailRenderer", {})
        if isinstance(mtr, dict):
            tn = mtr.get("thumbnail", {})
            if isinstance(tn, dict) and isinstance(tn.get("thumbnails"), list):
                thumbs = tn["thumbnails"]

    if thumbs:
        thumbs = sorted(
            [t for t in thumbs if isinstance(t, dict) and t.get("url")],
            key=lambda x: x.get("width", 0) * x.get("height", 0),
            reverse=True
        )
        thumbnails = [t["url"] for t in thumbs]

    # --- Fallback to get_song() if thumbnails empty ---
    if not thumbnails and fetch_missing_thumbnails and video_id:
        try:
            song_details = ytmusic.get_song(video_id)
            thumbs = song_details.get("thumbnails") or song_details.get("videoDetails", {}).get("thumbnail", {}).get("thumbnails", [])
            if isinstance(thumbs, list):
                thumbs = sorted(
                    [t for t in thumbs if isinstance(t, dict) and t.get("url")],
                    key=lambda x: x.get("width", 0) * x.get("height", 0),
                    reverse=True
                )
                thumbnails = [t["url"] for t in thumbs]
        except Exception as e:
            logger.warning(f"Failed to fetch song details for {video_id}: {str(e)}")

    # --- Final fallback: YouTube static thumbs ---
    if not thumbnails and video_id:
        thumbnails = [
            f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        ]

    return {
        "title": title,
        "videoId": video_id,
        "artists": artists,
        "album": album,
        "duration": duration,
        "thumbnails": thumbnails
    }
# Root endpoint

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Welcome to the Enhanced YouTube Music & Video API",
        "music_endpoints": [
            "/search", "/playlist", "/song/<id>", "/stream/<id>", 
            "/song/<id>/related", "/song/<id>/lyrics", "/charts"
        ],
        "video_endpoints": [
            "/video/search", "/video/<id>/stream", "/video/<id>/download",
            "/trending?type=videos"
        ],
        "podcast_endpoints": [
            "/podcast/search", "/podcast/<id>/episodes", "/trending?type=podcasts"
        ],
        "utility_endpoints": [
            "/suggestions", "/batch", "/download/status/<job_id>", "/app"
        ]
    })


# Serve music app
@app.route("/app")
def serve_app():
    return render_template('index.html')

# Search endpoint
@app.route("/search", methods=["GET"])
@cache.cached(query_string=True)   

def search_music():
    try:
        query = request.args.get("q")
        filter_type = request.args.get("filter")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        
        if not query:
            return jsonify({"error": "Missing query parameter 'q'"}), 400
        if page < 1 or page_size < 1:
            return jsonify({"error": "Invalid page or page_size"}), 400
        
        search_results = ytmusic.search(query, filter=filter_type)
        results = [
            format_track_data(result) for result in search_results
            if result.get("resultType") in ["song", "video"]
        ]
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        return jsonify({
            "query": query,
            "results": paginated_results,
            "count": len(paginated_results),
            "total_count": len(results),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(results) + page_size - 1) // page_size
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

# Playlist endpoint
@app.route("/playlist", methods=["GET"])
def get_playlist():
    try:
        playlist_id = request.args.get("id")
        limit = request.args.get("limit", 100, type=int)
        
        if not playlist_id:
            return jsonify({"error": "Missing playlist_id parameter 'id'"}), 400
        
        playlist = ytmusic.get_playlist(playlist_id, limit=limit)
        tracks = [format_track_data(track) for track in playlist.get("tracks", [])]
        return jsonify({
            "playlist_id": playlist_id,
            "title": playlist.get("title", ""),
            "description": playlist.get("description", ""),
            "track_count": playlist.get("track_count", 0),
            "tracks": tracks
        })
    except Exception as e:
        logger.error(f"Playlist error: {str(e)}")
        return jsonify({"error": f"Failed to fetch playlist: {str(e)}"}), 500

# Create playlist endpoint
@app.route("/playlist/create", methods=["POST"])
def create_playlist():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        title = data.get("title")
        description = data.get("description", "")
        privacy_status = data.get("privacy_status", "PUBLIC").upper()
        
        if not title:
            return jsonify({"error": "Missing 'title' in JSON body"}), 400
        if privacy_status not in ["PUBLIC", "PRIVATE", "UNLISTED"]:
            return jsonify({"error": "Invalid 'privacy_status'. Use 'PUBLIC', 'PRIVATE', or 'UNLISTED'"}), 400
        
        playlist_id = ytmusic.create_playlist(title, description, privacy_status=privacy_status)
        return jsonify({
            "playlist_id": playlist_id,
            "title": title,
            "description": description,
            "privacy_status": privacy_status,
            "message": "Playlist created successfully"
        })
    except Exception as e:
        logger.error(f"Create playlist error: {str(e)}")
        return jsonify({"error": f"Failed to create playlist: {str(e)}"}), 500

# Add to playlist endpoint
@app.route("/playlist/add", methods=["POST"])
def add_to_playlist():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        playlist_id = data.get("playlist_id")
        video_ids = data.get("video_ids", [])
        
        if not playlist_id:
            return jsonify({"error": "Missing 'playlist_id' in JSON body"}), 400
        if not video_ids or not isinstance(video_ids, list):
            return jsonify({"error": "'video_ids' must be a non-empty list"}), 400
        
        # Check for duplicates
        playlist = ytmusic.get_playlist(playlist_id, limit=100)
        existing_video_ids = {track.get("videoId") for track in playlist.get("tracks", [])}
        new_video_ids = [vid for vid in video_ids if vid not in existing_video_ids]
        
        if not new_video_ids:
            return jsonify({"message": "All provided video IDs are already in the playlist"}), 200
        
        result = ytmusic.add_playlist_items(playlist_id, new_video_ids)
        return jsonify({
            "playlist_id": playlist_id,
            "added_video_ids": new_video_ids,
            "result": result,
            "message": "Songs added successfully" if result else "Failed to add some or all songs"
        })
    except Exception as e:
        logger.error(f"Add to playlist error: {str(e)}")
        return jsonify({"error": f"Failed to add songs to playlist: {str(e)}"}), 500

# Remove from playlist endpoint
@app.route("/playlist/remove", methods=["POST"])
def remove_from_playlist():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        playlist_id = data.get("playlist_id")
        video_ids = data.get("video_ids", [])
        
        if not playlist_id:
            return jsonify({"error": "Missing 'playlist_id' in JSON body"}), 400
        if not video_ids or not isinstance(video_ids, list):
            return jsonify({"error": "'video_ids' must be a non-empty list"}), 400
        
        playlist = ytmusic.get_playlist(playlist_id, limit=100)
        tracks = playlist.get("tracks", [])
        set_video_ids = [track.get("setVideoId") for track in tracks if track.get("videoId") in video_ids]
        
        if not set_video_ids:
            return jsonify({"message": "None of the provided video IDs are in the playlist"}), 200
        
        result = ytmusic.remove_playlist_items(playlist_id, set_video_ids)
        return jsonify({
            "playlist_id": playlist_id,
            "removed_video_ids": video_ids,
            "result": result,
            "message": "Songs removed successfully" if result else "Failed to remove some or all songs"
        })
    except Exception as e:
        logger.error(f"Remove from playlist error: {str(e)}")
        return jsonify({"error": f"Failed to remove songs from playlist: {str(e)}"}), 500

# Song details endpoint
@app.route("/song/<video_id>", methods=["GET"])
@cache.cached(query_string=True)
def get_song_details(video_id):
    try:
        song = ytmusic.get_song(video_id)
        formatted_song = format_track_data(song)
        return jsonify(formatted_song)
    except Exception as e:
        logger.error(f"Song details error: {str(e)}")
        return jsonify({"error": f"Failed to fetch song details: {str(e)}"}), 500

# Stream URL endpoint
@app.route("/stream/<video_id>", methods=["GET"])
@cache.cached(query_string=True)
def get_stream_url(video_id):
    try:
        quality = request.args.get("quality", "medium").lower()
        quality_map = {
            "low": (0, 64),
            "medium": (64, 128),
            "high": (128, float("inf"))
        }
        if quality not in quality_map:
            return jsonify({"error": "Invalid quality. Use 'low', 'medium', or 'high'"}), 400
        
        min_bitrate, max_bitrate = quality_map[quality]
        
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        streams = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr")
        stream = None
        for s in streams:
            abr = s.abr.replace("kbps", "") if s.abr else "0"
            try:
                bitrate = float(abr)
                if min_bitrate <= bitrate <= max_bitrate:
                    stream = s
                    break
            except ValueError:
                continue
        
        if not stream:
            return jsonify({"error": f"No suitable audio stream found for quality: {quality}"}), 404
        
        return jsonify({
            "video_id": video_id,
            "stream_url": stream.url,
            "format": "mp4",
            "bitrate": stream.abr or "unknown"
        })
    except AgeRestrictedError:
        logger.error(f"Stream URL error: Video {video_id} is age-restricted")
        return jsonify({"error": "Video is age-restricted and cannot be streamed"}), 403
    except VideoUnavailable:
        logger.error(f"Stream URL error: Video {video_id} is unavailable")
        return jsonify({"error": "Video is unavailable or invalid"}), 404
    except Exception as e:
        logger.error(f"Stream URL error: {str(e)}")
        return jsonify({"error": f"Failed to fetch stream URL: {str(e)}"}), 500

# Related content endpoint with endless suggestions
@app.route("/song/<video_id>/related", methods=["GET"])
@cache.cached(query_string=True)
def get_related_content(video_id):
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        if limit < 1 or offset < 0:
            return jsonify({"error": "Invalid limit or offset"}), 400

        # Fetch related data safely
        watch_playlist = ytmusic.get_watch_playlist(videoId=video_id)

        tracks_data = []
        if isinstance(watch_playlist, dict):
            tracks_data = watch_playlist.get("tracks", [])
        elif isinstance(watch_playlist, list):
            tracks_data = watch_playlist

        related = []
        for track in tracks_data:
            if isinstance(track, dict) and track.get("videoId") and track.get("videoId") != video_id:
                related.append(format_track_data(track, fetch_missing_thumbnails=True))

        # Track duplicates
        seen_video_ids = {track["videoId"] for track in related}
        seen_titles = {
            (track["title"].lower(), tuple(sorted(a.lower() for a in track["artists"])))
            for track in related
        }

        # Expand pool if needed
        additional_songs = []
        if len(related) < limit:
            original_song = ytmusic.get_song(video_id)
            artist = original_song.get("artists", [{}])[0].get("name", "")
            title = original_song.get("title", "")
            query = f"{artist} {title} similar" if artist and title else "related songs"

            for _ in range(2):
                search_results = ytmusic.search(query, filter="songs", limit=20)
                for result in search_results:
                    if isinstance(result, dict) and result.get("videoId") and result["videoId"] not in seen_video_ids:
                        result_title = result.get("title", "").lower()
                        result_artists = tuple(sorted(a.get("name", "").lower() for a in result.get("artists", [])))
                        if (result_title, result_artists) not in seen_titles:
                            formatted_track = format_track_data(result, fetch_missing_thumbnails=True)
                            additional_songs.append(formatted_track)
                            seen_video_ids.add(result["videoId"])
                            seen_titles.add((result_title, result_artists))
                        if len(related) + len(additional_songs) >= limit:
                            break
                if len(related) + len(additional_songs) >= limit:
                    break
                if additional_songs:
                    query = f"{additional_songs[-1]['artists'][0]} similar" if additional_songs[-1]["artists"] else "related songs"

        # Merge & paginate
        all_related = related + additional_songs
        paginated_results = all_related[offset:offset + limit]

        return jsonify({
            "video_id": video_id,
            "related": paginated_results,
            "count": len(paginated_results),
            "total_count": len(all_related),
            "offset": offset,
            "next_offset": offset + limit if offset + limit < len(all_related) else None
        })

    except Exception as e:
                  logger.error(f"Related content error for  videoId {video_id}: {str(e)}")
                  logger.error(traceback.format_exc())  
                  return jsonify({"error": f"Failed to fetch related content: {str(e)}"}), 500



# --- In-memory session queues ---
session_queues = {}

def generate_queue(video_id, limit=20):
    """Helper: generate upnext queue from related songs"""
    related_resp = get_related_content(video_id)
    if hasattr(related_resp, "json"):
        related_data = related_resp.json
    else:
        related_data = related_resp.get_json()

    return related_data.get("related", [])[:limit]

# Start a new queue (auto session)
@app.route("/song/<video_id>/upnext/start", methods=["POST"])
def start_upnext(video_id):
    try:
        # Invalidate all existing sessions (new song means fresh queue)
        session_queues.clear()

        session_id = str(uuid.uuid4())  # auto-generate unique ID

        # Current song
        current_song = ytmusic.get_song(video_id)
        formatted_current = format_track_data(current_song, fetch_missing_thumbnails=True)

        # Related queue
        queue = generate_queue(video_id, limit=20)

        session_queues[session_id] = {
            "current_index": 0,
            "songs": [formatted_current] + queue
        }

        return jsonify({
            "session_id": session_id,
            "current": formatted_current,
            "queue": queue
        })
    except Exception as e:
        logger.error(f"Start UpNext error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Get current state
@app.route("/song/upnext/current/<session_id>", methods=["GET"])
def get_current_upnext(session_id):
    if session_id not in session_queues:
        return jsonify({"error": "Invalid or expired session"}), 400

    q = session_queues[session_id]
    return jsonify({
        "session_id": session_id,
        "current": q["songs"][q["current_index"]],
        "upnext": q["songs"][q["current_index"]+1:]
    })

# Move to next song
@app.route("/song/upnext/next/<session_id>", methods=["POST"])
def play_next_song(session_id):
    if session_id not in session_queues:
        return jsonify({"error": "Invalid or expired session"}), 400

    q = session_queues[session_id]
    q["current_index"] += 1

    # If queue ended, expire session
    if q["current_index"] >= len(q["songs"]):
        del session_queues[session_id]
        return jsonify({"message": "Queue finished, session ended"}), 200

    return jsonify({
        "session_id": session_id,
        "current": q["songs"][q["current_index"]],
        "upnext": q["songs"][q["current_index"]+1:]
    })




# Lyrics endpoint
lyrica_process = start_lyrica(folder_name="Lyrica")  # or "lyrica" if your folder is lowercase
@app.route("/song/<video_id>/lyrics", methods=["GET"])
def get_lyrics(video_id):
    """
    Retrieve synced lyrics for a song using the local Lyrica API.
    """
    try:
        # Step 1: Get song info from YTMusic
        song_data = ytmusic.get_song(video_id)
        title = song_data.get("videoDetails", {}).get("title", "")
        artist = song_data.get("videoDetails", {}).get("author", "")

        if not title or not artist:
            return jsonify({"error": "Could not extract song metadata"}), 400

        # Step 2: Query local Lyrica API
        lyrica_url = f"http://127.0.0.1:9999/lyrics/?artist={artist}&song={title}&timestamps=true"
        response = requests.get(lyrica_url, timeout=15)

        if response.status_code != 200:
            return jsonify({"error": f"Lyrica API failed with {response.status_code}"}), 502

        lyrica_data = response.json()
        logger.info(f"[Lyrica response] {lyrica_data}")

        # Step 3: Extract lyrics cleanly
        lyrics_list = []
        if "data" in lyrica_data:
            if "timed_lyrics" in lyrica_data["data"]:
                # Use synced/timed lyrics
                lyrics_list = [
                    {
                        "start": line.get("start_time"),
                        "end": line.get("end_time"),
                        "text": line.get("text", "")
                    }
                    for line in lyrica_data["data"]["timed_lyrics"]
                ]
            elif "lyrics" in lyrica_data["data"]:
                # Fallback: split plain lyrics into lines
                lyrics_list = [
                    {"start": None, "end": None, "text": line}
                    for line in lyrica_data["data"]["lyrics"].splitlines()
                ]

        # Step 4: Return clean API
        return jsonify({
            "video_id": video_id,
            "artist": artist,
            "title": title,
            "lyrics": lyrics_list,
            "source": lyrica_data.get("data", {}).get("source", "Lyrica API")
        })

    except Exception as e:
        logger.error(f"Lyrics endpoint error for video_id {video_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch lyrics: {str(e)}"}), 500





# Rate song endpoint
@app.route("/song/<video_id>/rate", methods=["POST"])
def rate_song(video_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        rating = data.get("rating")
        if not rating:
            return jsonify({"error": "Missing 'rating' in JSON body"}), 400
        if rating not in ["LIKE", "DISLIKE", "INDIFFERENT"]:
            return jsonify({"error": "Invalid 'rating'. Use 'LIKE', 'DISLIKE', or 'INDIFFERENT'"}), 400
        
        result = ytmusic.rate_song(video_id, rating)
        return jsonify({
            "video_id": video_id,
            "rating": rating,
            "result": result,
            "message": f"Song rated as {rating} successfully"
        })
    except Exception as e:
        logger.error(f"Rate song error: {str(e)}")
        return jsonify({"error": f"Failed to rate song: {str(e)}"}), 500

# Category/Genre search endpoint
@app.route("/browse", methods=["GET"])
@cache.cached(query_string=True)
def browse_music():
    try:
        category = request.args.get("category")
        limit = request.args.get("limit", 20, type=int)
        
        if not category:
            return jsonify({"error": "Missing category parameter"}), 400
        
        try:
            charts = ytmusic.get_charts()
            genre_results = []
            for chart in charts.get("genres", []):
                if chart.get("title", "").lower() == category.lower():
                    genre_results = chart.get("items", [])
                    break
            if not genre_results:
                genre_results = ytmusic.search(category, filter="songs")
        except Exception as e:
            logger.warning(f"Charts failed: {str(e)}, using search fallback")
            genre_results = ytmusic.search(category, filter="songs")
        
        results = [format_track_data(result) for result in genre_results if result.get("resultType") in ["song", "video"]]
        return jsonify({
            "category": category,
            "results": results[:limit],
            "count": len(results[:limit])
        })
    except Exception as e:
        logger.error(f"Browse error: {str(e)}")
        return jsonify({"error": f"Failed to fetch category results: {str(e)}"}), 500

# Mood and genre playlists endpoint
@app.route("/mood", methods=["GET"])
@cache.cached(query_string=True)
def get_mood_playlists():
    try:
        mood = request.args.get("mood")
        limit = request.args.get("limit", 20, type=int)
        
        if not mood:
            return jsonify({"error": "Missing mood parameter"}), 400
        
        mood_results = []
        try:
            mood_categories = ytmusic.get_mood_categories()
            for category in mood_categories.values():
                for playlist in category.get("playlists", []):
                    if playlist.get("title", "").lower().find(mood.lower()) != -1:
                        mood_results.append({
                            "playlist_id": playlist.get("playlistId", ""),
                            "title": playlist.get("title", ""),
                            "thumbnails": [thumb.get("url", "") for thumb in playlist.get("thumbnails", [])]
                        })
            if not mood_results:
                mood_results = ytmusic.search(mood, filter="playlists", limit=limit)
                mood_results = [
                    {
                        "playlist_id": result.get("browseId", ""),
                        "title": result.get("title", ""),
                        "thumbnails": [thumb.get("url", "") for thumb in result.get("thumbnails", [])]
                    } for result in mood_results
                ]
        except Exception as e:
            logger.warning(f"Mood categories failed: {str(e)}, using search fallback")
            mood_results = ytmusic.search(mood, filter="playlists", limit=limit)
            mood_results = [
                {
                    "playlist_id": result.get("browseId", ""),
                    "title": result.get("title", ""),
                    "thumbnails": [thumb.get("url", "") for thumb in result.get("thumbnails", [])]
                } for result in mood_results
            ]
        
        return jsonify({
            "mood": mood,
            "playlists": mood_results[:limit],
            "count": len(mood_results[:limit])
        })
    except Exception as e:
        logger.error(f"Mood playlists error: {str(e)}")
        return jsonify({"error": f"Failed to fetch mood playlists: {str(e)}"}), 500

# User library endpoint
@app.route("/user/library", methods=["GET"])
def get_user_library():
    try:
        limit = request.args.get("limit", 50, type=int)
        if limit < 1:
            return jsonify({"error": "Invalid limit parameter"}), 400
        
        try:
            library_songs = ytmusic.get_library_songs(limit=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch library songs: {str(e)}")
            library_songs = []
        
        try:
            library_playlists = ytmusic.get_library_playlists(limit=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch library playlists: {str(e)}")
            library_playlists = []
        
        songs = [format_track_data(song) for song in library_songs if song.get("videoId")]
        playlists = [
            {
                "playlist_id": playlist.get("playlistId", ""),
                "title": playlist.get("title", ""),
                "track_count": playlist.get("count", 0),
                "thumbnails": [thumb.get("url", "") for thumb in playlist.get("thumbnails", [])]
            } for playlist in library_playlists
        ]
        
        return jsonify({
            "songs": songs,
            "song_count": len(songs),
            "playlists": playlists,
            "playlist_count": len(playlists)
        })
    except Exception as e:
        logger.error(f"User library error: {str(e)}")
        return jsonify({"error": f"Failed to fetch user library: {str(e)}"}), 500

# User uploads endpoint
@app.route("/user/uploads", methods=["GET"])
def get_user_uploads():
    try:
        limit = request.args.get("limit", 50, type=int)
        if limit < 1:
            return jsonify({"error": "Invalid limit parameter"}), 400
        
        try:
            uploaded_songs = ytmusic.get_library_upload_songs(limit=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch uploaded songs: {str(e)}")
            uploaded_songs = []
        
        songs = [format_track_data(song) for song in uploaded_songs if song.get("videoId")]
        return jsonify({
            "songs": songs,
            "song_count": len(songs)
        })
    except Exception as e:
        logger.error(f"User uploads error: {str(e)}")
        return jsonify({"error": f"Failed to fetch user uploads: {str(e)}"}), 500

# Top charts endpoint
@app.route("/charts", methods=["GET"])
@cache.cached(query_string=True)
def get_top_charts():
    try:
        country = request.args.get("country", "US")
        limit = request.args.get("limit", 20, type=int)
        
        if not country or len(country) != 2:
            return jsonify({"error": "Invalid country code. Use a 2-letter ISO code (e.g., 'US')"}), 400
        
        try:
            charts = ytmusic.get_charts(country=country)
            if not isinstance(charts, dict) or "songs" not in charts or not isinstance(charts["songs"], dict):
                raise ValueError("Invalid charts response structure")
            top_songs = charts["songs"].get("items", [])
            if not top_songs:
                logger.warning(f"No chart songs found for country: {country}, falling back to search")
                top_songs = ytmusic.search("top songs", filter="songs")
        except Exception as e:
            logger.warning(f"Charts fetch failed: {str(e)}, falling back to search")
            top_songs = ytmusic.search("top songs", filter="songs")
        
        results = [format_track_data(song) for song in top_songs if song.get("videoId")]
        
        return jsonify({
            "country": country,
            "results": results[:limit],
            "count": len(results[:limit])
        })
    except Exception as e:
        logger.error(f"Charts error: {str(e)}")
        return jsonify({"error": f"Failed to fetch charts: {str(e)}"}), 500

# Search suggestions endpoint
@app.route("/suggestions", methods=["GET"])
@cache.cached(query_string=True)
def get_search_suggestions():
    try:
        query = request.args.get("q")
        if not query:
            return jsonify({"error": "Missing query parameter 'q'"}), 400
        
        suggestions = ytmusic.get_search_suggestions(query) or []
        return jsonify({
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions)
        })
    except Exception as e:
        logger.error(f"Suggestions error: {str(e)}")
        return jsonify({"error": f"Failed to fetch suggestions: {str(e)}"}), 500

# Batch request endpoint
@app.route("/batch", methods=["POST"])
def batch_request():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        video_ids = data.get("video_ids", [])
        playlist_ids = data.get("playlist_ids", [])
        limit = data.get("limit", 50, type=int)
        offset = data.get("offset", 0, type=int)
        
        if not video_ids and not playlist_ids:
            return jsonify({"error": "At least one of 'video_ids' or 'playlist_ids' must be provided"}), 400
        if limit < 1 or offset < 0:
            return jsonify({"error": "Invalid limit or offset"}), 400
        
        response = {"songs": [], "playlists": []}
        
        video_ids_paginated = video_ids[offset:offset + limit]
        for video_id in video_ids_paginated:
            try:
                song = ytmusic.get_song(video_id)
                response["songs"].append(format_track_data(song))
            except Exception as e:
                logger.warning(f"Batch song error for {video_id}: {str(e)}")
                response["songs"].append({"video_id": video_id, "error": str(e)})
        
        playlist_ids_paginated = playlist_ids[offset:offset + limit]
        for playlist_id in playlist_ids_paginated:
            try:
                playlist = ytmusic.get_playlist(playlist_id, limit=100)
                tracks = [format_track_data(track) for track in playlist.get("tracks", [])]
                response["playlists"].append({
                    "playlist_id": playlist_id,
                    "title": playlist.get("title", ""),
                    "description": playlist.get("description", ""),
                    "track_count": playlist.get("track_count", 0),
                    "tracks": tracks
                })
            except Exception as e:
                logger.warning(f"Batch playlist error for {playlist_id}: {str(e)}")
                response["playlists"].append({"playlist_id": playlist_id, "error": str(e)})
        
        return jsonify({
            "songs": response["songs"],
            "song_count": len(response["songs"]),
            "playlists": response["playlists"],
            "playlist_count": len(response["playlists"]),
            "offset": offset,
            "next_offset": offset + limit if offset + limit < max(len(video_ids), len(playlist_ids)) else None
        })
    except Exception as e:
        logger.error(f"Batch error: {str(e)}")
        return jsonify({"error": f"Batch request failed: {str(e)}"}), 500

#Download endpoint 

# Start async download with quality
@app.route("/download/<video_id>", methods=["GET"])
def start_download(video_id):
    quality = request.args.get("quality", "high").lower()
    if quality not in ["low", "medium", "high"]:
        quality = "high"
    job_id = start_async_download(video_id, quality)
    return jsonify({"job_id": job_id, "status": "processing", "progress": 0})

# Check progress
@app.route("/download/status/<job_id>", methods=["GET"])
def check_status(job_id):
    return jsonify(get_download_status(job_id))

# Fetch final file
@app.route("/download/file/<job_id>", methods=["GET"])
def fetch_file(job_id):
    file_resp = get_download_file(job_id)
    if not file_resp:
        return jsonify({"error": "File not ready"}), 404
    return file_resp

# Podcast search endpoint

@app.route("/podcast/search", methods=["GET"])
def search_podcasts():
    """
    Search for podcasts by keyword.
    Use ?query=YOUR_QUERY in query string.
    """
    try:
        query = request.args.get("query")
        limit = int(request.args.get("limit", 20))
        if not query:
            return jsonify({"error": "Missing query parameter"}), 400
        results = ytmusic.search(query, filter="podcasts", limit=limit)
        podcasts = []
        for result in results:
            if result.get("resultType") == "podcast":
                podcasts.append({
                    "title": result.get("title"),
                    "browseId": result.get("browseId"),
                    "author": result.get("author"),
                    "thumbnails": result.get("thumbnails"),
                    "description": result.get("descriptionSnippet"),
                })
        return jsonify({"query": query, "podcasts": podcasts, "count": len(podcasts)})
    except Exception as e:
        logger.error(f"Podcast search error: {str(e)}")
        return jsonify({"error": f"Failed to search podcasts: {str(e)}"}), 500

#helper

YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query="

def get_real_video_id(title):
    try:
        query = title.replace(" ", "+")
        url = YOUTUBE_SEARCH_URL + query

        html = requests.get(url, timeout=3).text

        # Find first videoId using regex
        match = re.search(r"videoId\":\"([a-zA-Z0-9_-]{11})", html)
        if match:
            return match.group(1)
    except Exception as e:
        print("Fast ID Error:", e)
    return None

@app.route('/video/search')
def video_search():
    try:
        query = request.args.get("q", "")
        duration_filter = request.args.get("duration", "any")
        upload_date = request.args.get("upload_date", "any")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))

        if not query.strip():
            return jsonify({"error": "Missing search query"}), 400

        # Fetch results using YTMusic (may lack videoId)
        search_results = ytmusic.search(query, filter="videos")

        videos = []
        for result in search_results:
            if result.get("resultType") != "video":
                continue

            # 🔥 Get videoId from YTMusic or fallback using PyTubeFix
            video_id = result.get("videoId")
            if not video_id:
                title = result.get("title", "")
                video_id = get_real_video_id(title)

            video_data = {
                "title": result.get("title", ""),
                "videoId": video_id,
                "description": result.get("description", ""),
                "thumbnails": [
                    t.get("url") for t in result.get("thumbnails", [])
                ],
                "channel": result.get("author", ""),
                "duration": result.get("duration", ""),
                "view_count": result.get("viewCount", ""),
                "upload_date": result.get("publishedTime", "")
            }

            # ⏳ Apply duration filter if needed
            if duration_filter != "any":
                duration_seconds = parse_duration_to_seconds(video_data["duration"])
                if not matches_duration_filter(duration_seconds, duration_filter):
                    continue

            videos.append(video_data)

        # 📄 Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = videos[start:end]

        return jsonify({
            "query": query,
            "videos": paginated_results,
            "count": len(paginated_results),
            "total_count": len(videos),
            "filters": {
                "duration": duration_filter,
                "upload_date": upload_date
            }
        })

    except Exception as e:
        logger.error(f"Video search error: {str(e)}")
        return jsonify({"error": f"Video search failed: {str(e)}"}), 500







# Helper functions for video filtering
def parse_duration_to_seconds(duration_str):
    """Convert duration string (e.g., '4:25') to seconds"""
    if not duration_str:
        return 0
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except:
        return 0
    return 0

def matches_duration_filter(seconds, filter_type):
    """Check if video duration matches filter criteria"""
    if filter_type == "short":
        return seconds <= 240  # 4 minutes
    elif filter_type == "medium":
        return 240 < seconds <= 1200  # 4-20 minutes
    elif filter_type == "long":
        return seconds > 1200  # 20+ minutes
    return True





@app.route("/podcast/<browseId>/episodes", methods=["GET"])
def get_podcast_episodes(browseId):
    """
    Get episodes for a podcast by using ytmusic.get_podcast.
    Accepts a playlistId (browseId) starting with MPSPPL.
    """
    try:
        podcast_data = ytmusic.get_podcast(browseId)
        if not podcast_data or "episodes" not in podcast_data:
            return jsonify({"error": "No episodes found"}), 404
        
        episodes = []
        for ep in podcast_data["episodes"]:
            episodes.append({
                "title": ep.get("title"),
                "videoId": ep.get("videoId"),
                "description": ep.get("description"),
                "duration": ep.get("duration"),
                "thumbnails": ep.get("thumbnails"),
                "date": ep.get("date"),
            })
        return jsonify({
            "browseId": browseId,
            "title": podcast_data.get("title"),
            "author": podcast_data.get("author", {}).get("name"),
            "episodes": episodes,
            "totalEpisodes": len(episodes),
        })
    except Exception as e:
        logger.error(f"Fetching podcast episodes error: {str(e)}")
        return jsonify({"error": f"Failed to fetch podcast episodes: {str(e)}"}), 500


# Enhanced video streaming with multiple quality options
@app.route("/video/<video_id>/stream", methods=["GET"])
@cache.cached(query_string=True)
def get_video_stream(video_id):
    try:
        quality = request.args.get("quality", "720p")
        format_type = request.args.get("format", "mp4")
        audio_only = request.args.get("audio_only", "false").lower() == "true"
        
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        
        if audio_only:
            # Audio-only stream
            streams = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc()
            stream = streams.first()
            stream_type = "audio"
        else:
            # Video stream with quality preference
            quality_map = {
                "144p": 144, "240p": 240, "360p": 360, "480p": 480,
                "720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160
            }
            
            target_res = quality_map.get(quality, 720)
            
            # Try to get the exact quality, then fallback to available qualities
            streams = yt.streams.filter(file_extension=format_type, progressive=True)
            stream = streams.filter(resolution=f"{target_res}p").first()
            
            if not stream:
                # Fallback to best available quality
                stream = streams.order_by("resolution").desc().first()
            
            stream_type = "video"
        
        if not stream:
            return jsonify({"error": "No suitable stream found"}), 404
            
        # Get video metadata
        video_info = {
            "video_id": video_id,
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "description": yt.description,
            "views": yt.views,
            "rating": yt.rating,
            "thumbnail": yt.thumbnail_url
        }
        
        return jsonify({
            "video_info": video_info,
            "stream": {
                "url": stream.url,
                "type": stream_type,
                "quality": stream.resolution if not audio_only else stream.abr,
                "format": stream.mime_type,
                "filesize": stream.filesize,
                "fps": stream.fps if hasattr(stream, 'fps') else None
            }
        })
        
    except Exception as e:
        logger.error(f"Video stream error: {str(e)}")
        return jsonify({"error": f"Failed to get video stream: {str(e)}"}), 500




# Enhanced trending endpoint for all content types with regional support
@app.route("/trending", methods=["GET"])
@cache.cached(query_string=True)
def get_trending_content():
    """
    Universal trending endpoint supporting:
    - Content types: songs, videos, podcasts, albums, playlists, all
    - Regional support with country codes
    - Quality filtering and pagination
    """
    try:
        content_type = request.args.get("type", "songs").lower()  # songs, videos, podcasts, albums, playlists, all
        region = request.args.get("region", "US").upper()
        limit = request.args.get("limit", 25, type=int)
        page = request.args.get("page", 1, type=int)
        
        # Validation
        valid_types = ["songs", "videos", "podcasts", "albums", "playlists", "all"]
        if content_type not in valid_types:
            return jsonify({"error": f"Invalid type. Use: {', '.join(valid_types)}"}), 400
            
        if len(region) != 2:
            return jsonify({"error": "Invalid region code. Use 2-letter ISO codes (US, GB, IN, etc.)"}), 400
            
        if limit < 1 or limit > 100:
            return jsonify({"error": "Limit must be between 1 and 100"}), 400
            
        if page < 1:
            return jsonify({"error": "Page must be greater than 0"}), 400

        trending_data = {}
        
        # Get trending content based on type
        if content_type == "all":
            # Fetch all types of trending content
            trending_data = get_all_trending_content(region, limit)
        else:
            # Fetch specific content type
            trending_data[content_type] = get_trending_by_type(content_type, region, limit)
        
        # Apply pagination
        paginated_data = {}
        start = (page - 1) * limit
        end = start + limit
        
        for content_key, content_list in trending_data.items():
            if isinstance(content_list, list):
                paginated_data[content_key] = content_list[start:end]
            else:
                paginated_data[content_key] = content_list
        
        # Calculate total counts for pagination
        total_counts = {}
        for content_key, content_list in trending_data.items():
            if isinstance(content_list, list):
                total_counts[content_key] = len(content_list)
        
        return jsonify({
            "type": content_type,
            "region": region,
            "page": page,
            "limit": limit,
            "data": paginated_data,
            "total_counts": total_counts,
            "total_pages": {
                key: (count + limit - 1) // limit 
                for key, count in total_counts.items()
            },
            "next_page": page + 1 if any(
                count > end for count in total_counts.values()
            ) else None
        })
        
    except Exception as e:
        logger.error(f"Trending content error: {str(e)}")
        return jsonify({"error": f"Failed to fetch trending content: {str(e)}"}), 500

def get_all_trending_content(region, limit):
    """Fetch all types of trending content"""
    trending_data = {}
    
    # Songs (Charts)
    try:
        charts = ytmusic.get_charts(country=region)
        if isinstance(charts, dict) and "songs" in charts:
            trending_songs = charts["songs"].get("items", [])[:limit]
            trending_data["songs"] = [
                format_track_data(song) for song in trending_songs 
                if song.get("videoId")
            ]
        else:
            # Fallback to search
            trending_songs = ytmusic.search("trending songs", filter="songs")[:limit]
            trending_data["songs"] = [
                format_track_data(song) for song in trending_songs
            ]
    except Exception as e:
        logger.warning(f"Failed to get trending songs: {str(e)}")
        trending_data["songs"] = []
    
    # Videos
    try:
        trending_videos = ytmusic.search("trending music videos", filter="videos")[:limit]
        trending_data["videos"] = [
            format_video_data(video) for video in trending_videos
            if video.get("resultType") == "video"
        ]
    except Exception as e:
        logger.warning(f"Failed to get trending videos: {str(e)}")
        trending_data["videos"] = []
    
    # Podcasts
    try:
        trending_podcasts = ytmusic.search("popular podcasts", filter="podcasts")[:limit]
        trending_data["podcasts"] = [
            format_podcast_data(podcast) for podcast in trending_podcasts
            if podcast.get("resultType") == "podcast"
        ]
    except Exception as e:
        logger.warning(f"Failed to get trending podcasts: {str(e)}")
        trending_data["podcasts"] = []
    
    # Albums
    try:
        trending_albums = ytmusic.search("new albums", filter="albums")[:limit]
        trending_data["albums"] = [
            format_album_data(album) for album in trending_albums
            if album.get("resultType") == "album"
        ]
    except Exception as e:
        logger.warning(f"Failed to get trending albums: {str(e)}")
        trending_data["albums"] = []
    
    # Playlists
    try:
        trending_playlists = ytmusic.search("popular playlists", filter="playlists")[:limit]
        trending_data["playlists"] = [
            format_playlist_data(playlist) for playlist in trending_playlists
            if playlist.get("resultType") == "playlist"
        ]
    except Exception as e:
        logger.warning(f"Failed to get trending playlists: {str(e)}")
        trending_data["playlists"] = []
    
    return trending_data

def get_trending_by_type(content_type, region, limit):
    """Fetch trending content for specific type"""
    try:
        if content_type == "songs":
            # Use charts for songs
            try:
                charts = ytmusic.get_charts(country=region)
                if isinstance(charts, dict) and "songs" in charts:
                    trending_items = charts["songs"].get("items", [])[:limit]
                else:
                    raise ValueError("Invalid charts response")
            except Exception:
                # Fallback to search
                trending_items = ytmusic.search("trending songs", filter="songs")[:limit]
            
            return [format_track_data(item) for item in trending_items if item.get("videoId")]
        
        elif content_type == "videos":
            # Search for trending videos
            trending_items = ytmusic.search("trending music videos", filter="videos")[:limit]
            return [
                format_video_data(item) for item in trending_items
                if item.get("resultType") == "video"
            ]
        
        elif content_type == "podcasts":
            # Search for popular podcasts
            trending_items = ytmusic.search("popular podcasts", filter="podcasts")[:limit]
            return [
                format_podcast_data(item) for item in trending_items
                if item.get("resultType") == "podcast"
            ]
        
        elif content_type == "albums":
            # Search for new/trending albums
            trending_items = ytmusic.search("new albums", filter="albums")[:limit]
            return [
                format_album_data(item) for item in trending_items
                if item.get("resultType") == "album"
            ]
        
        elif content_type == "playlists":
            # Search for popular playlists
            trending_items = ytmusic.search("popular playlists", filter="playlists")[:limit]
            return [
                format_playlist_data(item) for item in trending_items
                if item.get("resultType") == "playlist"
            ]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching trending {content_type}: {str(e)}")
        return []

def format_video_data(video):
    """Format video data for trending endpoint"""
    return {
        "type": "video",
        "title": video.get("title", ""),
        "videoId": video.get("videoId", ""),
        "channel": video.get("author", ""),
        "duration": video.get("duration", ""),
        "view_count": video.get("viewCount", ""),
        "thumbnails": extract_thumbnails(video),
        "description": video.get("description", ""),
        "published_time": video.get("publishedTime", "")
    }

def format_podcast_data(podcast):
    """Format podcast data for trending endpoint"""
    return {
        "type": "podcast",
        "title": podcast.get("title", ""),
        "browseId": podcast.get("browseId", ""),
        "author": podcast.get("author", ""),
        "description": podcast.get("description", ""),
        "episode_count": podcast.get("episodeCount", 0),
        "thumbnails": extract_thumbnails(podcast)
    }

def format_album_data(album):
    """Format album data for trending endpoint"""
    return {
        "type": "album",
        "title": album.get("title", ""),
        "browseId": album.get("browseId", ""),
        "artist": album.get("author", ""),
        "year": album.get("year", ""),
        "track_count": album.get("trackCount", 0),
        "thumbnails": extract_thumbnails(album),
        "explicit": album.get("isExplicit", False)
    }

def format_playlist_data(playlist):
    """Format playlist data for trending endpoint"""
    return {
        "type": "playlist",
        "title": playlist.get("title", ""),
        "playlistId": playlist.get("browseId", ""),
        "author": playlist.get("author", ""),
        "track_count": playlist.get("count", 0),
        "thumbnails": extract_thumbnails(playlist),
        "description": playlist.get("description", "")
    }

def extract_thumbnails(item):
    """Extract thumbnails from various item types"""
    thumbnails = []
    
    # Multiple possible thumbnail locations
    thumb_sources = [
        item.get("thumbnails", []),
        item.get("thumbnail", {}).get("thumbnails", []),
        item.get("thumbnail", []) if isinstance(item.get("thumbnail"), list) else []
    ]
    
    for source in thumb_sources:
        if isinstance(source, list) and source:
            thumbnails = [thumb.get("url", "") for thumb in source if thumb.get("url")]
            break
    
    # Fallback for videos
    if not thumbnails and item.get("videoId"):
        video_id = item["videoId"]
        thumbnails = [
            f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        ]
    
    return thumbnails

# Regional trending with specific categories
@app.route("/trending/regional", methods=["GET"])
@cache.cached(query_string=True)
def get_regional_trending():
    """
    Get trending content by specific regions with categories
    """
    try:
        regions = request.args.get("regions", "US").split(",")  # Support multiple regions
        category = request.args.get("category", "all")  # all, music, videos, podcasts
        limit_per_region = request.args.get("limit_per_region", 10, type=int)
        
        # Validate regions
        for region in regions:
            if len(region.strip()) != 2:
                return jsonify({"error": f"Invalid region code: {region}"}), 400
        
        regional_data = {}
        
        for region in regions:
            region = region.strip().upper()
            try:
                if category == "all":
                    regional_data[region] = get_all_trending_content(region, limit_per_region)
                else:
                    regional_data[region] = {
                        category: get_trending_by_type(category, region, limit_per_region)
                    }
            except Exception as e:
                logger.warning(f"Failed to get trending for {region}: {str(e)}")
                regional_data[region] = {"error": str(e)}
        
        return jsonify({
            "regions": regions,
            "category": category,
            "limit_per_region": limit_per_region,
            "data": regional_data
        })
        
    except Exception as e:
        logger.error(f"Regional trending error: {str(e)}")
        return jsonify({"error": f"Failed to fetch regional trending: {str(e)}"}), 500

# Trending discovery with time periods
@app.route("/trending/discovery", methods=["GET"])
@cache.cached(query_string=True)
def trending_discovery():
    """
    Advanced trending discovery with time-based queries
    """
    try:
        time_period = request.args.get("period", "today")  # today, week, month
        content_type = request.args.get("type", "songs")
        region = request.args.get("region", "US")
        limit = request.args.get("limit", 20, type=int)
        
        # Time-based query modifiers
        time_queries = {
            "today": "trending today",
            "week": "trending this week",
            "month": "popular this month"
        }
        
        if time_period not in time_queries:
            return jsonify({"error": "Invalid period. Use: today, week, month"}), 400
        
        base_query = time_queries[time_period]
        
        # Content type specific queries
        type_queries = {
            "songs": f"{base_query} songs",
            "videos": f"{base_query} music videos",
            "podcasts": f"{base_query} podcasts",
            "albums": f"new albums {time_period}",
            "playlists": f"popular playlists {time_period}"
        }
        
        search_query = type_queries.get(content_type, f"{base_query} {content_type}")
        filter_type = "songs" if content_type == "songs" else content_type
        
        # Search with time-based query
        results = ytmusic.search(search_query, filter=filter_type)[:limit]
        
        # Format results
        formatted_results = []
        for result in results:
            if content_type == "songs":
                formatted_results.append(format_track_data(result))
            elif content_type == "videos":
                formatted_results.append(format_video_data(result))
            elif content_type == "podcasts":
                formatted_results.append(format_podcast_data(result))
            elif content_type == "albums":
                formatted_results.append(format_album_data(result))
            elif content_type == "playlists":
                formatted_results.append(format_playlist_data(result))
        
        return jsonify({
            "period": time_period,
            "type": content_type,
            "region": region,
            "query": search_query,
            "results": formatted_results,
            "count": len(formatted_results)
        })
        
    except Exception as e:
        logger.error(f"Trending discovery error: {str(e)}")
        return jsonify({"error": f"Failed to fetch trending discovery: {str(e)}"}), 500

# Fixed Advanced Artist Endpoints with Robust Error Handling
@app.route("/artist/<artist_id>", methods=["GET"])
@cache.cached(query_string=True)
def get_artist_details(artist_id):
    """
    Get comprehensive artist information with robust error handling
    """
    try:
        # Get basic artist information with error handling
        try:
            artist_data = ytmusic.get_artist(artist_id)
        except Exception as e:
            logger.warning(f"Direct artist fetch failed: {str(e)}, trying fallback methods")
            # Fallback: Search for artist by ID
            search_results = ytmusic.search(artist_id, filter="artists")
            if search_results:
                artist_data = search_results[0]
            else:
                return jsonify({"error": "Artist not found"}), 404
        
        if not artist_data:
            return jsonify({"error": "Artist not found"}), 404
        
        # Extract basic artist information safely
        artist_info = safe_extract_artist_info(artist_data, artist_id)
        
        # Get artist's content sections safely
        content_sections = safe_extract_artist_content(artist_data)
        
        # Get top tracks using search fallback
        top_tracks = get_artist_top_tracks_safe(artist_id, artist_info.get("name", ""))
        
        return jsonify({
            "artist": artist_info,
            "top_tracks": top_tracks,
            "content": content_sections,
            "total_albums": len(content_sections.get("albums", [])),
            "total_singles": len(content_sections.get("singles", [])),
            "total_videos": len(content_sections.get("videos", [])),
            "total_playlists": len(content_sections.get("playlists", []))
        })
        
    except Exception as e:
        logger.error(f"Artist details error for {artist_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch artist details: {str(e)}"}), 500

@app.route("/artist/<artist_id>/albums", methods=["GET"])
@cache.cached(query_string=True)
def get_artist_albums(artist_id):
    """Get all albums from an artist with fallback search"""
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        include_singles = request.args.get("include_singles", "false").lower() == "true"
        
        if page < 1 or page_size < 1:
            return jsonify({"error": "Invalid page or page_size"}), 400
        
        # Try to get artist info first, then fallback to search
        artist_name = ""
        albums = []
        singles = []
        
        try:
            artist_data = ytmusic.get_artist(artist_id)
            artist_name = safe_get_nested(artist_data, ["name"], "") or safe_get_nested(artist_data, ["title"], "")
            content = safe_extract_artist_content(artist_data)
            albums = content.get("albums", [])
            singles = content.get("singles", [])
        except Exception as e:
            logger.warning(f"Direct artist fetch failed: {str(e)}, using search fallback")
            # Fallback: search for albums by artist ID or name
            search_results = ytmusic.search(f"artist:{artist_id}", filter="albums")
            if not search_results:
                search_results = ytmusic.search(artist_id, filter="albums")
            
            albums = [safe_format_album_data(album) for album in search_results[:20]]
        
        # Combine if requested
        all_releases = albums + (singles if include_singles else [])
        
        # Sort by year (newest first)
        all_releases.sort(key=lambda x: safe_get_year(x.get("year", 0)), reverse=True)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_releases = all_releases[start:end]
        
        return jsonify({
            "artist_id": artist_id,
            "artist_name": artist_name,
            "releases": paginated_releases,
            "count": len(paginated_releases),
            "total_count": len(all_releases),
            "albums_count": len(albums),
            "singles_count": len(singles),
            "page": page,
            "total_pages": (len(all_releases) + page_size - 1) // page_size,
            "include_singles": include_singles
        })
        
    except Exception as e:
        logger.error(f"Artist albums error for {artist_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch artist albums: {str(e)}"}), 500

@app.route("/artist/<artist_id>/top-tracks", methods=["GET"])
@cache.cached(query_string=True)
def get_artist_top_tracks_endpoint(artist_id):
    """Get artist's most popular tracks with multiple fallback methods"""
    try:
        limit = request.args.get("limit", 20, type=int)
        
        if limit < 1 or limit > 100:
            return jsonify({"error": "Limit must be between 1 and 100"}), 400
        
        # Get artist name for search fallback
        artist_name = ""
        try:
            artist_data = ytmusic.get_artist(artist_id)
            artist_name = safe_get_nested(artist_data, ["name"], "") or safe_get_nested(artist_data, ["title"], "")
        except:
            pass
        
        top_tracks = get_artist_top_tracks_safe(artist_id, artist_name, limit)
        
        return jsonify({
            "artist_id": artist_id,
            "artist_name": artist_name,
            "top_tracks": top_tracks,
            "count": len(top_tracks)
        })
        
    except Exception as e:
        logger.error(f"Artist top tracks error for {artist_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch artist top tracks: {str(e)}"}), 500

@app.route("/artist/<artist_id>/videos", methods=["GET"])
@cache.cached(query_string=True)
def get_artist_videos(artist_id):
    """Get all music videos from an artist with search fallback"""
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        
        if page < 1 or page_size < 1:
            return jsonify({"error": "Invalid page or page_size"}), 400
        
        videos = []
        artist_name = ""
        
        # Try to get from artist data first
        try:
            artist_data = ytmusic.get_artist(artist_id)
            artist_name = safe_get_nested(artist_data, ["name"], "") or safe_get_nested(artist_data, ["title"], "")
            content = safe_extract_artist_content(artist_data)
            videos = content.get("videos", [])
        except Exception as e:
            logger.warning(f"Direct artist fetch failed: {str(e)}")
        
        # Fallback: search for artist's videos
        if not videos:
            if artist_name:
                search_query = f"{artist_name} music video"
            else:
                search_query = f"artist:{artist_id} video"
            
            search_results = ytmusic.search(search_query, filter="videos")
            videos = [safe_format_video_data(video) for video in search_results if video.get("resultType") == "video"]
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_videos = videos[start:end]
        
        return jsonify({
            "artist_id": artist_id,
            "artist_name": artist_name,
            "videos": paginated_videos,
            "count": len(paginated_videos),
            "total_count": len(videos),
            "page": page,
            "total_pages": (len(videos) + page_size - 1) // page_size
        })
        
    except Exception as e:
        logger.error(f"Artist videos error for {artist_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch artist videos: {str(e)}"}), 500

@app.route("/artist/<artist_id>/related", methods=["GET"])
@cache.cached(query_string=True)
def get_related_artists(artist_id):
    """Get artists similar to the specified artist with search fallback"""
    try:
        limit = request.args.get("limit", 20, type=int)
        
        if limit < 1 or limit > 50:
            return jsonify({"error": "Limit must be between 1 and 50"}), 400
        
        related_artists = []
        artist_name = ""
        
        # Try to get from artist data first
        try:
            artist_data = ytmusic.get_artist(artist_id)
            artist_name = safe_get_nested(artist_data, ["name"], "") or safe_get_nested(artist_data, ["title"], "")
            content = safe_extract_artist_content(artist_data)
            related_artists = content.get("related_artists", [])
        except Exception as e:
            logger.warning(f"Direct artist fetch failed: {str(e)}")
        
        # Fallback: search for similar artists
        if not related_artists:
            if artist_name:
                search_queries = [
                    f"artists like {artist_name}",
                    f"{artist_name} similar artists",
                    f"{artist_name} related"
                ]
            else:
                search_queries = [f"similar to {artist_id}"]
            
            for query in search_queries:
                try:
                    search_results = ytmusic.search(query, filter="artists")
                    related_artists = [safe_format_artist_basic_info(artist) for artist in search_results 
                                     if artist.get("resultType") == "artist" and artist.get("browseId") != artist_id]
                    if related_artists:
                        break
                except:
                    continue
        
        return jsonify({
            "artist_id": artist_id,
            "artist_name": artist_name,
            "related_artists": related_artists[:limit],
            "count": len(related_artists[:limit])
        })
        
    except Exception as e:
        logger.error(f"Related artists error for {artist_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch related artists: {str(e)}"}), 500

@app.route("/artist/search", methods=["GET"])
@cache.cached(query_string=True)
def search_artists():
    """Search for artists with enhanced filtering"""
    try:
        query = request.args.get("q")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        
        if not query:
            return jsonify({"error": "Missing query parameter 'q'"}), 400
            
        if page < 1 or page_size < 1:
            return jsonify({"error": "Invalid page or page_size"}), 400
        
        # Search for artists
        search_results = ytmusic.search(query, filter="artists")
        
        artists = []
        for result in search_results:
            if result.get("resultType") == "artist":
                artist_info = safe_format_artist_basic_info(result)
                artists.append(artist_info)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_artists = artists[start:end]
        
        return jsonify({
            "query": query,
            "artists": paginated_artists,
            "count": len(paginated_artists),
            "total_count": len(artists),
            "page": page,
            "total_pages": (len(artists) + page_size - 1) // page_size
        })
        
    except Exception as e:
        logger.error(f"Artist search error: {str(e)}")
        return jsonify({"error": f"Failed to search artists: {str(e)}"}), 500

# Safe helper functions for robust data extraction
def safe_get_nested(data, keys, default=None):
    """Safely get nested dictionary values"""
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError, AttributeError):
        return default

def safe_extract_artist_info(artist_data, artist_id):
    """Extract artist information with multiple fallback methods"""
    return {
        "artist_id": artist_id,
        "name": (
            safe_get_nested(artist_data, ["name"]) or
            safe_get_nested(artist_data, ["title"]) or
            safe_get_nested(artist_data, ["header", "title"]) or
            ""
        ),
        "description": safe_extract_description(artist_data),
        "thumbnails": safe_extract_thumbnails_artist(artist_data),
        "statistics": safe_extract_statistics(artist_data),
        "verified": bool(safe_get_nested(artist_data, ["channelId"]) or safe_get_nested(artist_data, ["browseId"])),
        "channel_id": safe_get_nested(artist_data, ["channelId"], ""),
        "browse_id": safe_get_nested(artist_data, ["browseId"], artist_id)
    }

def safe_extract_description(artist_data):
    """Extract artist description safely"""
    description = (
        safe_get_nested(artist_data, ["description"]) or
        safe_get_nested(artist_data, ["header", "description"]) or
        safe_get_nested(artist_data, ["description", "text"]) or
        ""
    )
    
    if isinstance(description, dict):
        description = description.get("text", "")
    
    return str(description)

def safe_extract_thumbnails_artist(artist_data):
    """Extract artist thumbnails safely"""
    thumbnail_paths = [
        ["thumbnails"],
        ["header", "thumbnails"],
        ["thumbnail", "thumbnails"],
        ["musicImmersiveHeaderRenderer", "thumbnail", "thumbnails"]
    ]
    
    for path in thumbnail_paths:
        thumbs = safe_get_nested(artist_data, path, [])
        if isinstance(thumbs, list) and thumbs:
            sorted_thumbs = sorted(
                [t for t in thumbs if isinstance(t, dict) and t.get("url")],
                key=lambda x: (x.get("width", 0) * x.get("height", 0)),
                reverse=True
            )
            if sorted_thumbs:
                return [t["url"] for t in sorted_thumbs]
    
    return []

def safe_extract_statistics(artist_data):
    """Extract artist statistics safely"""
    return {
        "subscriber_count": safe_get_nested(artist_data, ["stats", "subscriberCount"]),
        "view_count": safe_get_nested(artist_data, ["stats", "viewCount"]),
        "video_count": safe_get_nested(artist_data, ["stats", "videoCount"])
    }

def safe_extract_artist_content(artist_data):
    """Extract artist content sections safely"""
    content_sections = {
        "albums": [],
        "singles": [],
        "videos": [],
        "playlists": [],
        "related_artists": []
    }
    
    sections = safe_get_nested(artist_data, ["sections"], [])
    if not isinstance(sections, list):
        return content_sections
    
    for section in sections:
        if not isinstance(section, dict):
            continue
            
        header = str(safe_get_nested(section, ["header"], "")).lower()
        contents = safe_get_nested(section, ["contents"], [])
        
        if "album" in header and "single" not in header:
            content_sections["albums"] = safe_format_albums_list(contents)
        elif "single" in header or "ep" in header:
            content_sections["singles"] = safe_format_albums_list(contents)
        elif "video" in header:
            content_sections["videos"] = safe_format_videos_list(contents)
        elif "playlist" in header:
            content_sections["playlists"] = safe_format_playlists_list(contents)
        elif "artist" in header or "similar" in header:
            content_sections["related_artists"] = safe_format_artists_list(contents)
    
    return content_sections

def safe_format_albums_list(contents):
    """Format albums list safely"""
    albums = []
    for item in contents:
        if isinstance(item, dict):
            album = {
                "title": safe_get_nested(item, ["title"], ""),
                "browse_id": safe_get_nested(item, ["browseId"], ""),
                "year": safe_get_nested(item, ["year"], ""),
                "type": safe_get_nested(item, ["type"], "Album"),
                "thumbnails": safe_extract_thumbnails_generic(item),
                "explicit": safe_get_nested(item, ["isExplicit"], False)
            }
            albums.append(album)
    return albums

def safe_format_videos_list(contents):
    """Format videos list safely"""
    videos = []
    for item in contents:
        if isinstance(item, dict):
            video = safe_format_video_data(item)
            videos.append(video)
    return videos

def safe_format_playlists_list(contents):
    """Format playlists list safely"""
    playlists = []
    for item in contents:
        if isinstance(item, dict):
            playlist = {
                "title": safe_get_nested(item, ["title"], ""),
                "browse_id": safe_get_nested(item, ["browseId"], ""),
                "track_count": safe_get_nested(item, ["count"], 0),
                "thumbnails": safe_extract_thumbnails_generic(item)
            }
            playlists.append(playlist)
    return playlists

def safe_format_artists_list(contents):
    """Format artists list safely"""
    artists = []
    for item in contents:
        if isinstance(item, dict):
            artist = safe_format_artist_basic_info(item)
            artists.append(artist)
    return artists

def safe_format_video_data(video):
    """Format video data safely"""
    return {
        "title": safe_get_nested(video, ["title"], ""),
        "video_id": safe_get_nested(video, ["videoId"], ""),
        "channel": safe_get_nested(video, ["author"], "") or safe_get_nested(video, ["channel"], ""),
        "duration": safe_get_nested(video, ["duration"], ""),
        "view_count": safe_get_nested(video, ["viewCount"], ""),
        "thumbnails": safe_extract_thumbnails_generic(video),
        "published_time": safe_get_nested(video, ["publishedTime"], "")
    }

def safe_format_album_data(album):
    """Format album data safely"""
    return {
        "title": safe_get_nested(album, ["title"], ""),
        "browse_id": safe_get_nested(album, ["browseId"], ""),
        "year": safe_get_nested(album, ["year"], ""),
        "type": safe_get_nested(album, ["type"], "Album"),
        "artist": safe_get_nested(album, ["author"], "") or safe_get_nested(album, ["artist"], ""),
        "thumbnails": safe_extract_thumbnails_generic(album),
        "explicit": safe_get_nested(album, ["isExplicit"], False)
    }

def safe_format_artist_basic_info(artist_data):
    """Format basic artist information safely"""
    return {
        "name": (
            safe_get_nested(artist_data, ["artist"]) or
            safe_get_nested(artist_data, ["title"]) or
            safe_get_nested(artist_data, ["name"]) or
            ""
        ),
        "browse_id": safe_get_nested(artist_data, ["browseId"], ""),
        "subscriber_count": safe_get_nested(artist_data, ["subscriberCount"], ""),
        "thumbnails": safe_extract_thumbnails_generic(artist_data)
    }

def safe_extract_thumbnails_generic(item):
    """Extract thumbnails from any item type safely"""
    thumbnail_paths = [
        ["thumbnails"],
        ["thumbnail", "thumbnails"],
        ["thumbnail"]
    ]
    
    for path in thumbnail_paths:
        thumbs = safe_get_nested(item, path, [])
        if isinstance(thumbs, list) and thumbs:
            sorted_thumbs = sorted(
                [t for t in thumbs if isinstance(t, dict) and t.get("url")],
                key=lambda x: (x.get("width", 0) * x.get("height", 0)),
                reverse=True
            )
            if sorted_thumbs:
                return [t["url"] for t in sorted_thumbs]
    
    return []

def get_artist_top_tracks_safe(artist_id, artist_name, limit=20):
    """Get artist's top tracks with multiple fallback methods"""
    top_tracks = []
    
    # Method 1: Try to get from artist sections
    try:
        artist_data = ytmusic.get_artist(artist_id)
        sections = safe_get_nested(artist_data, ["sections"], [])
        for section in sections:
            header = str(safe_get_nested(section, ["header"], "")).lower()
            if any(word in header for word in ["song", "track", "popular", "top"]):
                contents = safe_get_nested(section, ["contents"], [])
                for track in contents:
                    if isinstance(track, dict) and track.get("videoId"):
                        top_tracks.append(format_track_data(track))
                        if len(top_tracks) >= limit:
                            break
            if len(top_tracks) >= limit:
                break
    except Exception as e:
        logger.warning(f"Failed to get tracks from artist sections: {str(e)}")
    

    # Method 2: Search for popular songs by artist
    if not top_tracks and artist_name:
        try:
            search_queries = [
                f"{artist_name} popular songs",
                f"{artist_name} best songs",
                f"{artist_name} top hits",
                artist_name  # Just the artist name
            ]
            
            for query in search_queries:
                search_results = ytmusic.search(query, filter="songs")
                for track in search_results:
                    if track.get("resultType") == "song":
                        formatted_track = format_track_data(track)
                        # Check if this artist is in the track's artists
                        if any(artist_name.lower() in artist.lower() for artist in formatted_track.get("artists", [])):
                            top_tracks.append(formatted_track)
                            if len(top_tracks) >= limit:
                                break
                if len(top_tracks) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Failed to search for artist tracks: {str(e)}")
    
    return top_tracks[:limit]

def safe_get_year(year_value):
    """Safely convert year value to integer"""
    if isinstance(year_value, int):
        return year_value
    try:
        return int(str(year_value))
    except:
        return 0


@app.route("/podcast/episode/<videoId>/play", methods=["GET"])
def play_podcast_episode(videoId):
    """
    Returns a playable stream URL for a podcast episode, given its videoId.
    """
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={videoId}")
        stream = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc().first()
        if not stream:
            return jsonify({"error": "Audio stream not found"}), 404
        return jsonify({
            "title": yt.title,
            "stream_url": stream.url,
            "videoId": videoId,
            "author": yt.author
        })
    except Exception as e:
        logger.error(f"Episode playback error: {str(e)}")
        return jsonify({"error": f"Failed to play episode: {str(e)}"}), 500






if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


