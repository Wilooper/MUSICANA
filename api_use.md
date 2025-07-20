YouTube Music API Documentation

This document provides a comprehensive overview of the RESTful API endpoints implemented in the Flask-based YouTube Music application. The API leverages the ytmusicapi and pytubefix libraries to interact with YouTube Music, enabling functionalities such as searching for music, managing playlists, retrieving song details, streaming audio, and more. All endpoints support JSON responses and include appropriate error handling.

Base URL

The base URL for all API endpoints is: http://<host>:5000, where <host> is typically 0.0.0.0 or localhost when running locally, and the default port is 5000.

Authentication

The API uses ytmusicapi for authentication, attempting OAuth with oauth.json or falling back to header-based authentication. Ensure proper configuration of oauth.json for authenticated endpoints like user library access or playlist modifications.

Endpoints

1. Root Endpoint





Purpose: Provides a welcome message listing available endpoints.



Method: GET



URL: /



Parameters: None



Response:





200 OK:

{
  "message": "Welcome to the YouTube Music API. Use /search, /playlist, /song/<video_id>, /stream/<video_id>, /song/<video_id>/related, /song/<video_id>/lyrics, /browse, /user/library, /charts, /suggestions, /batch, /download/<video_id>, /user/recent, /playlist/create, /playlist/add, /playlist/remove, /user/uploads, /mood, or /song/<video_id>/rate."
}



Errors: None

2. Serve Music App





Purpose: Serves the music_app.html file for the frontend application.



Method: GET



URL: /app



Parameters: None



Response:





200 OK: Returns the music_app.html file.



Errors:





500 Internal Server Error: If the file cannot be served.

3. Search Music





Purpose: Searches for songs or videos based on a query.



Method: GET



URL: /search



Parameters:





q (string, required): Search query.



filter (string, optional): Filter type (e.g., "songs", "videos").



page (integer, optional, default=1): Page number for pagination.



page_size (integer, optional, default=20): Number of results per page.



Response:





200 OK:

{
  "query": "<search_query>",
  "results": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_results>,
  "total_count": <total_results>,
  "page": <current_page>,
  "page_size": <page_size>,
  "total_pages": <total_pages>
}



400 Bad Request:

{"error": "Missing query parameter 'q'"}

{"error": "Invalid page or page_size"}



500 Internal Server Error:

{"error": "Search failed: <error_message>"}

4. Get Playlist





Purpose: Retrieves details and tracks of a specified playlist.



Method: GET



URL: /playlist



Parameters:





id (string, required): Playlist ID.



limit (integer, optional, default=100): Maximum number of tracks to retrieve.



Response:





200 OK:

{
  "playlist_id": "<playlist_id>",
  "title": "<playlist_title>",
  "description": "<playlist_description>",
  "track_count": <number_of_tracks>,
  "tracks": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ]
}



400 Bad Request:

{"error": "Missing playlist_id parameter 'id'"}



500 Internal Server Error:

{"error": "Failed to fetch playlist: <error_message>"}

5. Create Playlist





Purpose: Creates a new playlist.



Method: POST



URL: /playlist/create



Request Body (JSON):

{
  "title": "<playlist_title>",
  "description": "<playlist_description>",
  "privacy_status": "<PUBLIC|PRIVATE|UNLISTED>"
}



Response:





200 OK:

{
  "playlist_id": "<new_playlist_id>",
  "title": "<playlist_title>",
  "description": "<playlist_description>",
  "privacy_status": "<privacy_status>",
  "message": "Playlist created successfully"
}



400 Bad Request:

{"error": "Missing JSON body"}

{"error": "Missing 'title' in JSON body"}

{"error": "Invalid 'privacy_status'. Use 'PUBLIC', 'PRIVATE', or 'UNLISTED'"}



500 Internal Server Error:

{"error": "Failed to create playlist: <error_message>"}

6. Add to Playlist





Purpose: Adds songs to an existing playlist.



Method: POST



URL: /playlist/add



Request Body (JSON):

{
  "playlist_id": "<playlist_id>",
  "video_ids": ["<video_id1>", "<video_id2>"]
}



Response:





200 OK:

{
  "playlist_id": "<playlist_id>",
  "added_video_ids": ["<video_id1>", "<video_id2>"],
  "result": "<result>",
  "message": "<Songs added successfully|Failed to add some or all songs>"
}

{"message": "All provided video IDs are already in the playlist"}



400 Bad Request:

{"error": "Missing JSON body"}

{"error": "Missing 'playlist_id' in JSON body"}

{"error": "'video_ids' must be a non-empty list"}



500 Internal Server Error:

{"error": "Failed to add songs to playlist: <error_message>"}

7. Remove from Playlist





Purpose: Removes songs from an existing playlist.



Method: POST



URL: /playlist/remove



Request Body (JSON):

{
  "playlist_id": "<playlist_id>",
  "video_ids": ["<video_id1>", "<video_id2>"]
}



Response:





200 OK:

{
  "playlist_id": "<playlist_id>",
  "removed_video_ids": ["<video_id1>", "<video_id2>"],
  "result": "<result>",
  "message": "<Songs removed successfully|Failed to remove some or all songs>"
}

{"message": "None of the provided video IDs are in the playlist"}



400 Bad Request:

{"error": "Missing JSON body"}

{"error": "Missing 'playlist_id' in JSON body"}

{"error": "'video_ids' must be a non-empty list"}



500 Internal Server Error:

{"error": "Failed to remove songs from playlist: <error_message>"}

8. Get Song Details





Purpose: Retrieves details for a specific song or video.



Method: GET



URL: /song/<video_id>



Parameters:





video_id (string, required): YouTube video ID.



Response:





200 OK:

{
  "title": "<song_title>",
  "videoId": "<video_id>",
  "artists": ["<artist_name>"],
  "album": "<album_name>",
  "duration": "<duration>",
  "thumbnails": ["<thumbnail_url>"]
}



500 Internal Server Error:

{"error": "Failed to fetch song details: <error_message>"}

9. Get Stream URL





Purpose: Retrieves the streaming URL for a song or video.



Method: GET



URL: /stream/<video_id>



Parameters:





video_id (string, required): YouTube video ID.



quality (string, optional, default="medium"): Audio quality ("low", "medium", "high").



Response:





200 OK:

{
  "video_id": "<video_id>",
  "stream_url": "<stream_url>",
  "format": "mp4",
  "bitrate": "<bitrate>"
}



400 Bad Request:

{"error": "Invalid quality. Use 'low', 'medium', or 'high'"}



403 Forbidden:

{"error": "Video is age-restricted and cannot be streamed"}



404 Not Found:

{"error": "No suitable audio stream found for quality: <quality>"}

{"error": "Video is unavailable or invalid"}



500 Internal Server Error:

{"error": "Failed to fetch stream URL: <error_message>"}

10. Get Related Content





Purpose: Retrieves related songs or videos for a given video ID.



Method: GET



URL: /song/<video_id>/related



Parameters:





video_id (string, required): YouTube video ID.



limit (integer, optional, default=50): Maximum number of related tracks.



offset (integer, optional, default=0): Starting index for pagination.



Response:





200 OK:

{
  "video_id": "<video_id>",
  "related": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_results>,
  "total_count": <total_related>,
  "offset": <current_offset>,
  "next_offset": <next_offset|null>
}



400 Bad Request:

{"error": "Invalid limit or offset"}



500 Internal Server Error:

{"error": "Failed to fetch related content: <error_message>"}

11. Get Lyrics





Purpose: Retrieves lyrics for a specific song.



Method: GET



URL: /song/<video_id>/lyrics



Parameters:





video_id (string, required): YouTube video ID.



Response:





200 OK:

{
  "video_id": "<video_id>",
  "lyrics": "<lyrics_text>"
}



404 Not Found:

{"error": "Song details unavailable for lyrics lookup"}

{"error": "Lyrics not found"}



500 Internal Server Error:

{"error": "Lyrics API request failed: <status_code>"}

{"error": "Failed to fetch lyrics: <error_message>"}

12. Rate Song





Purpose: Rates a song with "LIKE", "DISLIKE", or "INDIFFERENT".



Method: POST



URL: /song/<video_id>/rate



Parameters:





video_id (string, required): YouTube video ID.



Request Body (JSON):

{
  "rating": "<LIKE|DISLIKE|INDIFFERENT>"
}



Response:





200 OK:

{
  "video_id": "<video_id>",
  "rating": "<rating>",
  "result": "<result>",
  "message": "Song rated as <rating> successfully"
}



400 Bad Request:

{"error": "Missing JSON body"}

{"error": "Missing 'rating' in JSON body"}

{"error": "Invalid 'rating'. Use 'LIKE', 'DISLIKE', or 'INDIFFERENT'"}



500 Internal Server Error:

{"error": "Failed to rate song: <error_message>"}

13. Browse Music by Category/Genre





Purpose: Retrieves songs based on a specified category or genre.



Method: GET



URL: /browse



Parameters:





category (string, required): Category or genre name.



limit (integer, optional, default=20): Maximum number of results.



Response:





200 OK:

{
  "category": "<category_name>",
  "results": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_results>
}



400 Bad Request:

{"error": "Missing category parameter"}



500 Internal Server Error:

{"error": "Failed to fetch category results: <error_message>"}

14. Get Mood Playlists





Purpose: Retrieves playlists based on a specified mood.



Method: GET



URL: /mood



Parameters:





mood (string, required): Mood name (e.g., "chill", "upbeat").



limit (integer, optional, default=20): Maximum number of playlists.



Response:





200 OK:

{
  "mood": "<mood_name>",
  "playlists": [
    {
      "playlist_id": "<playlist_id>",
      "title": "<playlist_title>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_playlists>
}



400 Bad Request:

{"error": "Missing mood parameter"}



500 Internal Server Error:

{"error": "Failed to fetch mood playlists: <error_message>"}

15. Get User Library





Purpose: Retrieves the user's library songs and playlists.



Method: GET



URL: /user/library



Parameters:





limit (integer, optional, default=50): Maximum number of songs/playlists.



Response:





200 OK:

{
  "songs": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "song_count": <number_of_songs>,
  "playlists": [
    {
      "playlist_id": "<playlist_id>",
      "title": "<playlist_title>",
      "track_count": <number_of_tracks>,
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "playlist_count": <number_of_playlists>
}



400 Bad Request:

{"error": "Invalid limit parameter"}



500 Internal Server Error:

{"error": "Failed to fetch user library: <error_message>"}

16. Get User Uploads





Purpose: Retrieves the user's uploaded songs.



Method: GET



URL: /user/uploads



Parameters:





limit (integer, optional, default=50): Maximum number of songs.



Response:





200 OK:

{
  "songs": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "song_count": <number_of_songs>
}



400 Bad Request:

{"error": "Invalid limit parameter"}



500 Internal Server Error:

{"error": "Failed to fetch user uploads: <error_message>"}

17. Get Top Charts





Purpose: Retrieves top songs for a specified country.



Method: GET



URL: /charts



Parameters:





country (string, optional, default="US"): 2-letter ISO country code.



limit (integer, optional, default=20): Maximum number of songs.



Response:





200 OK:

{
  "country": "<country_code>",
  "results": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": [" Ascending [0:0]
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_results>
}



400 Bad Request:

{"error": "Invalid country code. Use a 2-letter ISO code (e.g., 'US')"}



500 Internal Server Error:

{"error": "Failed to fetch charts: <error_message>"}

18. Get Search Suggestions





Purpose: Retrieves search suggestions for a given query.



Method: GET



URL: /suggestions



Parameters:





q (string, required): Search query.



Response:





200 OK:

{
  "query": "<search_query>",
  "suggestions": ["<suggestion1>", "<suggestion2>"],
  "count": <number_of_suggestions>
}



400 Bad Request:

{"error": "Missing query parameter 'q'"}



500 Internal Server Error:

{"error": "Failed to fetch suggestions: <error_message>"}

19. Batch Request





Purpose: Retrieves details for multiple songs and playlists in a single request.



Method: POST



URL: /batch



Request Body (JSON):

{
  "video_ids": ["<video_id1>", "<video_id2>"],
  "playlist_ids": ["<playlist_id1>", "<playlist_id2>"],
  "limit": <integer>,
  "offset": <integer>
}



Response:





200 OK:

{
  "songs": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    },
    {
      "video_id": "<video_id>",
      "error": "<error_message>"
    }
  ],
  "song_count": <number_of_songs>,
  "playlists": [
    {
      "playlist_id": "<playlist_id>",
      "title": "<playlist_title>",
      "description": "<playlist_description>",
      "track_count": <number_of_tracks>,
      "tracks": [
        {
          "title": "<song_title>",
          "videoId": "<video_id>",
          "artists": ["<artist_name>"],
          "album": "<album_name>",
          "duration": "<duration>",
          "thumbnails": ["<thumbnail_url>"]
        }
      ]
    },
    {
      "playlist_id": "<playlist_id>",
      "error": "<error_message>"
    }
  ],
  "playlist_count": <number_of_playlists>,
  "offset": <current_offset>,
  "next_offset": <next_offset|null>
}



400 Bad Request:

{"error": "Missing JSON body"}

{"error": "At least one of 'video_ids' or 'playlist_ids' must be provided"}

{"error": "Invalid limit or offset"}



500 Internal Server Error:

{"error": "Batch request failed: <error_message>"}

20. Download Audio





Purpose: Downloads an audio file for a specified video.



Method: GET



URL: /download/<video_id>



Parameters:





video_id (string, required): YouTube video ID.



format (string, optional, default="mp4"): File format (only "mp4" supported).



Response:





200 OK:

{
  "video_id": "<video_id>",
  "download_url": "file://<download_path>/<filename>",
  "format": "mp4",
  "filename": "<video_id>.mp4"
}



400 Bad Request:

{"error": "Only 'mp4' format is supported without ffmpeg"}



403 Forbidden:

{"error": "Video is age-restricted and cannot be downloaded"}



404 Not Found:

{"error": "No suitable audio stream found"}

{"error": "Video is unavailable or invalid"}



500 Internal Server Error:

{"error": "Failed to download audio: <error_message>"}

21. Get Recently Played





Purpose: Retrieves the user's recently played tracks.



Method: GET



URL: /user/recent



Parameters:





limit (integer, optional, default=20): Maximum number of tracks.



Response:





200 OK:

{
  "results": [
    {
      "title": "<song_title>",
      "videoId": "<video_id>",
      "artists": ["<artist_name>"],
      "album": "<album_name>",
      "duration": "<duration>",
      "thumbnails": ["<thumbnail_url>"]
    }
  ],
  "count": <number_of_results>
}



500 Internal Server Error:

{"error": "Failed to fetch recently played tracks: <error_message>"}

Notes





CORS: The API is configured to allow requests from http://127.0.0.1:8080 and http://localhost:8080.



Error Handling: All endpoints include comprehensive error handling, logging errors for debugging purposes.



Dependencies: Requires ytmusicapi, pytubefix, flask, flask-cors, and requests libraries.



File Downloads: The /download/<video_id> endpoint stores files in /sdcard/Download and returns a file URL.



Authentication: Some endpoints (e.g., /user/library, /playlist/create) require valid YouTube Music authentication via oauth.json or header-based authentication.

Error Codes





200 OK: Request successful.



400 Bad Request: Invalid or missing parameters.



403 Forbidden: Access denied (e.g., age-restricted content).



404 Not Found: Resource not found (e.g., invalid video ID or no lyrics available).



500 Internal Server Error: Server-side error with a descriptive message.

This documentation provides a clear and structured guide to interacting with the YouTube Music API, ensuring developers can effectively utilize its functionalities.
