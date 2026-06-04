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
    "extractor_args": {"youtube": {"player_client": ["web"], "po_token": []}},
    "js_runtimes": ["node"],
}

video_id = "dQw4w9WgXcQ"
url = f"https://www.youtube.com/watch?v={video_id}"

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)

subs = info.get("subtitles", {})
auto = info.get("automatic_captions", {})
en_sub = subs.get("en") or auto.get("en")

if en_sub:
    vtt_entry = next((e for e in en_sub if e.get("ext") == "vtt"), en_sub[0])
    sub_url = vtt_entry["url"]
    print(f"Trying: {sub_url[:80]}")
    with yt_dlp.YoutubeDL(opts) as ydl2:
        try:
            response = ydl2.urlopen(Request(sub_url))
            content = response.read().decode("utf-8")
            print(f"SUCCESS! {len(content)} bytes")
            print(content[:300])
        except Exception as e:
            print(f"FAILED: {e}")
