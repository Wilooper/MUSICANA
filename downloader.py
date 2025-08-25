import os
import requests
import subprocess
import tempfile
import threading
import uuid
import time
import shutil
import re
from flask import send_file
from pytubefix import YouTube
from ytmusicapi import YTMusic

ytmusic = YTMusic()

# Job storage
DOWNLOAD_JOBS = {}
CLEANUP_INTERVAL = 300      # check every 5 min
JOB_EXPIRY = 600            # remove jobs older than 10 min


def fetch_lyrics(video_id):
    """Fetch lyrics from local Lyrica API"""
    try:
        song = ytmusic.get_song(video_id)
        title = song.get("videoDetails", {}).get("title", "")
        artist = song.get("videoDetails", {}).get("author", "")

        lyrica_url = f"http://127.0.0.1:9999/lyrics/?artist={artist}&song={title}"
        r = requests.get(lyrica_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "data" in data and "lyrics" in data["data"]:
                return data["data"]["lyrics"]
        return ""
    except Exception:
        return ""


def on_progress(stream, chunk, bytes_remaining, job_id):
    """Track pytubefix download progress"""
    job = DOWNLOAD_JOBS.get(job_id)
    if not job:
        return
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percent = int(bytes_downloaded * 100 / total_size)
    job["progress"] = percent // 2  # download is half (0–50)


def process_download(job_id, video_id, quality):
    """Background worker for downloading and embedding metadata"""
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}",
                     on_progress_callback=lambda s, c, r: on_progress(s, c, r, job_id))
        title = yt.title
        artist = yt.author or "Unknown"
        cover_url = yt.thumbnail_url

        # Album from YTMusic
        song_meta = ytmusic.get_song(video_id)
        album = ""
        try:
            album = song_meta.get("microformat", {}).get("microformatDataRenderer", {}).get("category", "")
            if not album:
                album = song_meta.get("videoDetails", {}).get("title", "")
        except Exception:
            album = "Unknown"

        # Lyrics
        lyrics = fetch_lyrics(video_id)

        tmpdir = tempfile.mkdtemp()
        raw_file = os.path.join(tmpdir, "audio.mp4")
        final_file = os.path.join(tmpdir, f"{title}.m4a")
        cover_file = os.path.join(tmpdir, "cover.jpg")

        # Step 1: select stream based on quality
        streams = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc()
        if not streams:
            raise Exception("No audio streams found")

        if quality == "low":
            stream = min(streams, key=lambda s: int(s.abr.replace("kbps", "")) if s.abr else 999)
        elif quality == "medium":
            stream = min(streams, key=lambda s: abs(128 - (int(s.abr.replace("kbps", "")) if s.abr else 128)))
        else:  # high/best
            stream = streams.first()

        stream.download(output_path=tmpdir, filename="audio.mp4")

        # Step 2: download cover
        if cover_url:
            r = requests.get(cover_url, stream=True)
            if r.status_code == 200:
                with open(cover_file, "wb") as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)

        # Step 3: ffmpeg embed metadata
        cmd = ["ffmpeg", "-y", "-i", raw_file]
        if os.path.exists(cover_file):
            cmd += [
                "-i", cover_file,
                "-map", "0:a", "-map", "1:v",
                "-c:a", "aac", "-c:v", "png",
                "-disposition:v:0", "attached_pic",
            ]
        else:
            cmd += ["-c:a", "aac", "-vn"]

        cmd += [
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
            "-metadata", f"album={album}",
            "-metadata", f"lyrics={lyrics}",
            "-metadata", "comment=Downloaded via API",
            final_file
        ]

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        # Track FFmpeg conversion progress
        duration = None
        for line in process.stderr:
            if "Duration" in line:
                match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
                if match:
                    h, m, s = map(float, match.groups())
                    duration = h * 3600 + m * 60 + s
            if "time=" in line and duration:
                match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if match:
                    h, m, s = map(float, match.groups())
                    current = h * 3600 + m * 60 + s
                    percent = int((current / duration) * 50)
                    DOWNLOAD_JOBS[job_id]["progress"] = 50 + percent

        process.wait()

        DOWNLOAD_JOBS[job_id]["status"] = "completed"
        DOWNLOAD_JOBS[job_id]["progress"] = 100
        DOWNLOAD_JOBS[job_id]["file"] = final_file
        DOWNLOAD_JOBS[job_id]["tmpdir"] = tmpdir
    except Exception as e:
        DOWNLOAD_JOBS[job_id]["status"] = "failed"
        DOWNLOAD_JOBS[job_id]["error"] = str(e)


def start_async_download(video_id, quality="high"):
    """Start a background download job and return job_id"""
    job_id = str(uuid.uuid4())
    DOWNLOAD_JOBS[job_id] = {
        "status": "processing",
        "progress": 0,
        "file": None,
        "error": None,
        "timestamp": time.time(),
        "tmpdir": None
    }
    thread = threading.Thread(target=process_download, args=(job_id, video_id, quality))
    thread.start()
    return job_id


def get_download_status(job_id):
    """Check job status"""
    job = DOWNLOAD_JOBS.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job


def get_download_file(job_id):
    """Return file if ready"""
    job = DOWNLOAD_JOBS.get(job_id)
    if not job or job["status"] != "completed":
        return None
    return send_file(
        job["file"],
        as_attachment=True,
        download_name=os.path.basename(job["file"]),
        mimetype="audio/m4a"
    )


def cleanup_old_jobs():
    """Background cleanup of old jobs"""
    while True:
        now = time.time()
        expired = [jid for jid, job in DOWNLOAD_JOBS.items()
                   if now - job["timestamp"] > JOB_EXPIRY and job["status"] in ["completed", "failed"]]

        for jid in expired:
            job = DOWNLOAD_JOBS[jid]
            if job.get("tmpdir") and os.path.exists(job["tmpdir"]):
                try:
                    shutil.rmtree(job["tmpdir"])
                except Exception:
                    pass
            del DOWNLOAD_JOBS[jid]

        time.sleep(CLEANUP_INTERVAL)


# Start cleanup thread
threading.Thread(target=cleanup_old_jobs, daemon=True).start()
