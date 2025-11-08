import sys
import os
import requests
import time
#songinput = input('enter song name:-')
API_URL = 'http://127.0.0.1:5000'
def song(song_name ,terminal = True):
    API_URL = 'http://127.0.0.1:5000'
    response = requests.get(f"{API_URL}/search", params={"q": song_name})
    data = response.json()
    song_ini = data['results'][0]
    title = song_ini.get('title','unknown Title')
    video_id = song_ini.get('videoId')
    stream_res = requests.get(f"{API_URL}/stream/{video_id}")
    stream_data = stream_res.json()
    stream_url = stream_data.get("stream_url")
    print(f'NOW PLAYING "{title}"……')
    if terminal:
       os.system(f"mpv  '{stream_url}'")
    else:
       os.system(f'mpv --no-terminal "{stream_url}"&')
    
def lyrics(song_name):
    response = requests.get(f"{API_URL}/search", params={"q": song_name})
    data = response.json()
    song_ini = data['results'][0]
    video_id = song_ini.get('videoId')
    main = requests.get(f"{API_URL}/song/{video_id}/lyrics")
    data = main.json()
    artist = data.get('artist')
    title = data.get('title')
    source = data.get('source')
     
    print(artist)
    print(title)
    print(source)
    timed = data["lyrics"]
    prev = 0
    for line in timed or data.get('lyrics'):
        start = line["start"] / 1000
        time.sleep(max(start - prev, 0))
        print(line["text"])
        prev = start
