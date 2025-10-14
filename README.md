

# MUSICANA

**MUSICANA** is a free music API and site powered by YouTube Music (ytmusicapi) and Lyrica (lyrics API).  
While a simple web interface is included, the main focus of MUSICANA is its flexible and powerful RESTful API for music search, streaming, playlists, lyrics, and more.

---

## Key Features

- **Comprehensive Music API:**  
  - Search for songs, videos, albums, and artists.
  - Stream music directly via API endpoints.
  - Manage playlists (create, add/remove tracks).
  - Retrieve synced lyrics (via Lyrica API).
  - Browse charts, moods, user library, and uploads.
  - Download tracks with metadata and lyrics embedded.

- **Easy Integration:**  
  Build music apps/sites in any language using HTTP requests.

---

## Quick Start

### 1. Install Dependencies

Requires Python 3.x

```bash
pip install flask flask-cors flask-caching ytmusicapi pytubefix requests
```

### 2. Configure Authentication

- Place your OAuth credentials in `oauth.json` (required for user library and playlist actions).

### 3. Start the API Server

```bash
python api.py
```
Default base URL: `http://localhost:5000`

---

## Example API Usage

- **Search Songs:**  
  ```
  curl "http://localhost:5000/search?q=queen&filter=songs&page=1&page_size=5"
  ```

- **Stream a Song:**  
  ```
  curl "http://localhost:5000/stream/dQw4w9WgXcQ?quality=high"
  ```

- **Get Lyrics:**  
  ```
  curl "http://localhost:5000/song/dQw4w9WgXcQ/lyrics"
  ```

- **Create a Playlist:**  
  ```
  curl -X POST "http://localhost:5000/playlist/create" \
    -H "Content-Type: application/json" \
    -d '{"title": "My Playlist", "privacy_status": "PUBLIC"}'
  ```

- **Add Songs to a Playlist:**  
  ```
  curl -X POST "http://localhost:5000/playlist/add" \
    -H "Content-Type: application/json" \
    -d '{"playlist_id": "PL123456", "video_ids": ["dQw4w9WgXcQ", "a1b2c3d4e5"]}'
  ```

---

## API Reference

- `GET /search` — Search for music.
- `GET /stream/<video_id>` — Get streaming URL for songs.
- `GET /song/<video_id>/lyrics` — Retrieve synced lyrics.
- `GET /playlist/<playlist_id>` — Get playlist details.
- `POST /playlist/create` — Create a playlist.
- `POST /playlist/add` — Add tracks to playlist.
- `POST /playlist/remove` — Remove tracks from playlist.
- `GET /charts` — Get top charts.
- `GET /user/library` — Get user's saved songs.
- `GET /mood` — Get mood-based playlists.
- `GET /download/<video_id>` — Download song (with tags/lyrics).

**See full endpoint documentation in [`api_use.md`](api_use.md) and [`Api_guide.md`](Api_guide.md).**

---

## Notes

- **Caching:** All responses are cached for 5 minutes.
- **Lyrics:** Lyrica server must be running on port 9999 for lyrics.
- **Error Handling:** Standard HTTP error codes, with JSON error messages.
- **Duplicates:** Adding already existing songs to a playlist will be skipped.

---

## License & Credits

- Uses [ytmusicapi](https://github.com/sigma67/ytmusicapi) for YouTube Music access.
- Lyrics powered by Lyrica (custom API).
- Project by [Wilooper](https://github.com/Wilooper).

---

**For full API details and advanced usage, see [`api_use.md`](api_use.md) and [`Api_guide.md`](Api_guide.md).**
