from flask import Flask, request, jsonify, send_file
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



# Initialize YTMusic with OAuth or fallback to header-based authentication
try:
    ytmusic = YTMusic('oauth.json', oauth_credentials=OAuthCredentials(client_id='1025031628526-p57dae03qh9tr5ohrjq3qh5p2m695pro.apps.googleusercontent.com',client_secret='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'))
except Exception as e:
    logger.warning(f"OAuth initialization failed: {str(e)}, attempting header-based authentication")
    try:
        ytmusic = YTMusic()
    except Exception as e:
        logger.error(f"Failed to initialize YTMusic: {str(e)}")
        raise Exception("YTMusic initialization failed. Ensure oauth.json is correctly configured or use header authentication.")

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
    return jsonify({"message": "Welcome to the YouTube Music API. Use /search, /playlist, /song/<video_id>, /stream/<video_id>, /song/<video_id>/related, /song/<video_id>/lyrics, /browse, /user/library, /charts, /suggestions, /batch, /download/<video_id>, /user/recent, /playlist/create, /playlist/add, /playlist/remove, /user/uploads, /mood, or /song/<video_id>/rate."})

# Serve music app
@app.route("/app")
def serve_app():
    return send_file("music_app.html")

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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


