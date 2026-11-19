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
    
    # Write cookies to temp file
    cookies_content = os.environ.get("YOUTUBE_COOKIES", "")
    with open("cookies.txt", "w") as f:
        f.write(cookies_content)
    
    ydl_opts = {
        "format": "mp4",
        "outtmpl": f"{video_id}.mp4",
        "quiet": True,
        "cookiefile": "cookies.txt",
    }
def post_to_instagram(video_path, caption):
    import pyotp
    
    cl = Client()
    session_file = Path("session.json")
    totp_secret = os.environ.get("INSTAGRAM_TOTP_SECRET", "")
    import base64
    padded = totp_secret + '=' * (-len(totp_secret) % 8)
    print(f"TOTP secret length: {len(totp_secret)}, value: '{totp_secret}'")
    totp = pyotp.TOTP(padded)
    
    if session_file.exists():
        cl.load_settings(session_file)
    
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
    except Exception as e:
        if "TwoFactorRequired" in str(type(e).__name__):
            cl.two_factor_login(totp.now())
        else:
            raise
    
    cl.dump_settings(session_file)
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
