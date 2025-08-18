# downloader_module.py
import os
import requests
import subprocess
import tempfile
from flask import send_file
from pytubefix import YouTube

def download_song_for_client(video_id):
    """
    Downloads YouTube audio, embeds cover + metadata, 
    returns a Flask send_file response so the user downloads it directly.
    """
    yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
    title = yt.title
    artists = yt.author or "Unknown"
    cover_url = yt.thumbnail_url

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_file = os.path.join(tmpdir, "audio.mp4")
        final_file = os.path.join(tmpdir, f"{title}.m4a")
        cover_file = os.path.join(tmpdir, "cover.jpg")

        # Step 1: download audio
        stream = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc().first()
        if not stream:
            raise Exception("No audio stream found")
        stream.download(output_path=tmpdir, filename="audio.mp4")

        # Step 2: download cover
        if cover_url:
            r = requests.get(cover_url, stream=True)
            if r.status_code == 200:
                with open(cover_file, "wb") as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)

        # Step 3: convert with metadata + cover
        cmd = [
            "ffmpeg", "-y", "-i", raw_file,
        ]
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
            "-metadata", f"artist={artists}",
            "-metadata", "comment=Downloaded via API",
            final_file
        ]

        subprocess.run(cmd, check=True)

        # Step 4: send file to client (browser download)
        return send_file(
            final_file,
            as_attachment=True,
            download_name=f"{title}.m4a",
            mimetype="audio/m4a"
        )
