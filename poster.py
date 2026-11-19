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

def convert_cookies_to_netscape(json_cookies):
    lines = ["# Netscape HTTP Cookie File\n"]
    data = json.loads(json_cookies)
    # Handle both list and dict with nested cookies
    if isinstance(data, dict):
        cookies = data.get("cookies", data.get("cookie", []))
    else:
        cookies = data
    for cookie in cookies:
        if isinstance(cookie, str):
            continue
        domain = cookie.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = cookie.get("path", "/")
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        expiry = str(int(cookie.get("expirationDate", 0)))
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
    return "".join(lines)
    
def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    cookies_content = os.environ.get("YOUTUBE_COOKIES", "")
    print(f"DEBUG: Cookies length: {len(cookies_content)}")
    netscape = convert_cookies_to_netscape(cookies_content)
    print(f"DEBUG: Netscape cookies lines: {len(netscape.splitlines())}")
    with open("cookies.txt", "w") as f:
        f.write(netscape)
    
    ydl_opts = {
        "format": "mp4",
        "outtmpl": f"{video_id}.mp4",
        "quiet": True,
        "cookiefile": "cookies.txt",
    }
    print(f"DEBUG: Downloading video {video_id}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"DEBUG: Download complete")
    return f"{video_id}.mp4"

def post_to_instagram(video_path, caption):
    import pyotp
    
    cl = Client()
    session_file = Path("session.json")
    totp_secret = os.environ.get("INSTAGRAM_TOTP_SECRET", "").strip().replace(" ", "").replace("-", "").rstrip("=").upper()
    print(f"DEBUG: TOTP secret length: {len(totp_secret)}")
    totp = None
    if totp_secret:
        padded = totp_secret + "=" * (-len(totp_secret) % 8)
        print(f"DEBUG: Padded TOTP length: {len(padded)}")
        totp = pyotp.TOTP(padded)
    
    if session_file.exists():
        print("DEBUG: Loading existing session")
        cl.load_settings(session_file)
    
    print("DEBUG: Attempting Instagram login")
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        print("DEBUG: Login successful")
    except Exception as e:
        print(f"DEBUG: Login exception: {type(e).__name__}: {e}")
        if "TwoFactorRequired" in str(type(e).__name__):
            if totp is None:
                raise ValueError("INSTAGRAM_TOTP_SECRET is required for two-factor authentication")
            print("DEBUG: Attempting 2FA login")
            cl.two_factor_login(totp.now())
            print("DEBUG: 2FA login successful")
        else:
            raise
    
    cl.dump_settings(session_file)
    print(f"DEBUG: Uploading video {video_path}")
    cl.clip_upload(Path(video_path), caption)
    print("DEBUG: Upload complete")
    cl.logout()

def main():
    posted = load_posted()
    shorts = get_shorts()
    print(f"DEBUG: Found {len(shorts)} shorts, {len(posted)} already posted")
    
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
