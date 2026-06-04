import sys
sys.path.insert(0, "/app")
from yt_dlp.networking.impersonate import ImpersonateTarget
import yt_dlp
from yt_dlp.networking import Request

opts = {
    "quiet": False,
    "no_warnings": False,
    "extract_flat": False,
    "impersonate": ImpersonateTarget("chrome"),
    "cookiefile": "/app/cookies.txt",
    "js_runtimes": {"node": {}},
    "remote_components": {"ejs:github"},
}

video_id = "dQw4w9WgXcQ"
url = f"https://www.youtube.com/watch?v={video_id}"

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)

print(f"Title: {info.get('title')}")
en_sub = info.get("subtitles", {}).get("en") or info.get("automatic_captions", {}).get("en")
if en_sub:
    vtt_entry = next((e for e in en_sub if e.get("ext") == "vtt"), en_sub[0])
    sub_url = vtt_entry["url"]
    print(f"\nTrying: {sub_url[:80]}")
    with yt_dlp.YoutubeDL(opts) as ydl2:
        try:
            response = ydl2.urlopen(Request(sub_url))
            content = response.read().decode("utf-8")
            print(f"SUCCESS! {len(content)} bytes")
            print(content[:300])
        except Exception as e:
            print(f"FAILED: {e}")
