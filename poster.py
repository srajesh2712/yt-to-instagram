import os
import json
import yt_dlp
from instagrapi import Client
from pathlib import Path

CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]
IG_USERNAME = os.environ["INSTAGRAM_USERNAME"]
IG_PASSWORD = os.environ["INSTAGRAM_PASSWORD"]
LOG_FILE = "posted.json"

def load_posted():
    if Path(LOG_FILE).exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def save_posted(posted):
    with open(LOG_FILE, "w") as f:
        json.dump(posted, f)

def get_shorts():
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_end": 1000,
    }
    url = f"https://www.youtube.com/{CHANNEL_ID}/shorts"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get("entries", [])
        return list(reversed(entries))  # oldest first

def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "format": "mp4",
        "outtmpl": f"{video_id}.mp4",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return f"{video_id}.mp4"

def post_to_instagram(video_path, caption):
    cl = Client()
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.clip_upload(Path(video_path), caption)
    cl.logout()

def main():
    posted = load_posted()
    shorts = get_shorts()
    
    for video in shorts:
        video_id = video.get("id")
        if video_id in posted:
            continue
        
        caption = video.get("title", "")
        print(f"Posting: {caption}")
        
        video_path = download_video(video_id)
        post_to_instagram(video_path, caption)
        
        posted.append(video_id)
        save_posted(posted)
        
        Path(video_path).unlink()
        print("Done!")
        break  # one per day

if __name__ == "__main__":
    main()
