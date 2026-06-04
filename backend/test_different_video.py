import sys
sys.path.insert(0, "/app")
from yt_dlp.networking.impersonate import ImpersonateTarget
import yt_dlp

# Try a different video and use ydl's own urlopen to download the VTT
opts = {
    "quiet": False,
    "no_warnings": False,
    "extract_flat": False,
    "impersonate": ImpersonateTarget("chrome"),
    "cookiefile": "/app/cookies.txt",
}

# Try a very popular video with known subtitles
video_id = "dQw4w9WgXcQ"  # Rick Astley - has manual subtitles
url = f"https://www.youtube.com/watch?v={video_id}"

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)

subs = info.get("subtitles", {})
auto = info.get("automatic_captions", {})
en_sub = subs.get("en") or subs.get("en-US") or auto.get("en") or auto.get("en-US")
print(f"Title: {info.get('title')}")
print(f"Manual sub langs: {list(subs.keys())[:5]}")
print(f"Auto sub langs: {list(auto.keys())[:5]}")

if en_sub:
    # Pick VTT url and download directly with ydl.urlopen
    vtt_entry = next((e for e in en_sub if e.get("ext") == "vtt"), en_sub[0])
    sub_url = vtt_entry["url"]
    print(f"\nTrying direct urlopen for: {sub_url[:80]}")

    with yt_dlp.YoutubeDL(opts) as ydl2:
        try:
            from yt_dlp.networking import Request
            response = ydl2.urlopen(Request(sub_url))
            content = response.read().decode("utf-8")
            print(f"SUCCESS! Downloaded {len(content)} bytes")
            print(content[:200])
        except Exception as e:
            print(f"FAILED: {e}")
