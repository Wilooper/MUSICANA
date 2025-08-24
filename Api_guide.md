now mix 1st one and second one and create a readme.md so I can directly copy paste it intoy repo

```markdown
# YouTube Music API

A powerful Flask-based API providing access to YouTube Music features including search, streaming, playlists, lyrics, charts, and more. This API leverages `ytmusicapi` and `pytubefix` with OAuth authentication, caching, and comprehensive error handling.

---

## Base URL

```
http://localhost:5000
```

---

## Features

- Search songs, albums, playlists, artists with pagination and filters.
- Stream audio with quality options.
- Full playlist management (create, add, remove, get).
- Sync lyrics integration via Lyrica API.
- Get related songs and recommendations.
- Top charts by country.
- Mood-based and genre-based browsing.
- User library and uploaded songs management.
- Batch processing for efficiency.
- CORS enabled and filesystem caching for performance.

---

## Authentication

Requires OAuth credentials configured in `oauth.json`. Falls back to header-based authentication if OAuth fails.

---

## API Endpoints

### Root & Info

- **GET /**  
  Welcome message listing available API endpoints.

- **GET /app**  
  Serves the integrated music web frontend (music_app.html).

---

### Search & Suggestions

- **GET /search**  
  Search YouTube Music content by query and filter.

  **Parameters:**  
  - `q` (required): Search keyword  
  - `filter` (optional): `songs`, `albums`, `artists`, `playlists`  
  - `page` (optional, default=1): Page number  
  - `page_size` (optional, default=20): Items per page

- **GET /suggestions**  
  Get search autocomplete suggestions.

  **Parameters:**  
  - `q` (required): Partial search string

---

### Song & Playback

- **GET /song/<video_id>**  
  Get detailed data about a song.

- **GET /stream/<video_id>**  
  Get direct audio stream URL (mp4) for a given quality.

  **Parameters:**  
  - `quality` (optional, default=medium): `low`, `medium`, `high`

- **GET /song/<video_id>/related**  
  Get related and similar songs with pagination.

  **Parameters:**  
  - `limit` (optional, default=50)  
  - `offset` (optional, default=0)

- **GET /song/<video_id>/lyrics**  
  Retrieve synced lyrics from local Lyrica API.

- **POST /song/<video_id>/rate**  
  Rate a song.

  **Body JSON:**  
  - `rating`: `LIKE`, `DISLIKE`, or `INDIFFERENT`

- **GET /download/<video_id>**  
  Download the audio file for a song.

---

### Playlist Management

- **GET /playlist**  
  Retrieve a playlist and its tracks.

  **Parameters:**  
  - `id` (required): Playlist ID  
  - `limit` (optional, default=100): Max tracks

- **POST /playlist/create**  
  Create a new playlist.

  **Body JSON:**  
  - `title` (required)  
  - `description` (optional)  
  - `privacy_status` (optional, default=PUBLIC): `PUBLIC`, `PRIVATE`, `UNLISTED`

- **POST /playlist/add**  
  Add songs to a playlist.

  **Body JSON:**  
  - `playlist_id` (required)  
  - `video_ids` (required): Array of video IDs

- **POST /playlist/remove**  
  Remove songs from a playlist.

  **Body JSON:**  
  - `playlist_id` (required)  
  - `video_ids` (required): Array of video IDs

---

### Browse & Discovery

- **GET /browse**  
  Browse by category/genre.

  **Parameters:**  
  - `category` (required)  
  - `limit` (optional, default=20)

- **GET /mood**  
  Get playlists by mood.

  **Parameters:**  
  - `mood` (required)  
  - `limit` (optional, default=20)

- **GET /charts**  
  Top charts by country.

  **Parameters:**  
  - `country` (optional, default=US): 2-letter ISO code  
  - `limit` (optional, default=20)

---

### User Library

- **GET /user/library**  
  Get user's liked songs and playlists.

  **Parameters:**  
  - `limit` (optional, default=50)

- **GET /user/uploads**  
  Get user's uploaded songs.

  **Parameters:**  
  - `limit` (optional, default=50)

---

### Batch Requests

- **POST /batch**  
  Process multiple video and playlist IDs in a single request.

  **Body JSON:**  
  - `video_ids` (optional): Array of video IDs  
  - `playlist_ids` (optional): Array of playlist IDs  
  - `limit` (optional, default=50)  
  - `offset` (optional, default=0)

---

## HTTP Status Codes

| Code | Meaning                       | Description                                    |
|-------|------------------------------|------------------------------------------------|
| 200   | Success                      | Request processed successfully.                |
| 400   | Bad Request                 | Missing or invalid parameters.                  |
| 403   | Forbidden                   | Access restricted (age or permissions).        |
| 404   | Not Found                   | Resource does not exist or is unavailable.      |
| 500   | Internal Server Error       | Unexpected server error.                         |
| 502   | Bad Gateway                 | External API (e.g., Lyrica) failure.            |

Error responses contain JSON with an `"error"` key describing the issue.

---

## Example Usage

### Search Songs

```
curl "http://localhost:5000/search?q=queen&filter=songs&page=1&page_size=5"
```

### Get Streaming URL

```
curl "http://localhost:5000/stream/dQw4w9WgXcQ?quality=high"
```

### Create Playlist

```
curl -X POST "http://localhost:5000/playlist/create" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Playlist", "privacy_status": "PUBLIC"}'
```

### Add Songs to Playlist

```
curl -X POST "http://localhost:5000/playlist/add" \
  -H "Content-Type: application/json" \
  -d '{"playlist_id": "PL123456", "video_ids": ["dQw4w9WgXcQ", "a1b2c3d4e5"]}'
```

---

## Setup & Dependencies

- Python 3.x
- Flask
- flask-cors
- flask-caching
- ytmusicapi
- pytubefix
- requests

Install dependencies:

```
pip install flask flask-cors flask-caching ytmusicapi pytubefix requests
```

Configure OAuth credentials in `oauth.json`.

Run the API with:

```
python api.py
```

---

## Notes

- **Caching:** Responses are cached for 5 minutes to improve performance.
- **Lyrica API:** For lyrics, ensure the Lyrica server is running locally on port 9999.
- **Error Handling:** Always check HTTP status and error messages.
- **Playlist duplicates:** Adding already existing videos will be skipped.

---

This README provides a complete overview of the API for quick onboarding and development. Use it as a reference to integrate YouTube Music features seamlessly into your app or service.

```

Citations:
[1] api.py https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/85582760/ac6257ba-0969-45e6-bee0-a2d4c9bf7ae2/api.py
