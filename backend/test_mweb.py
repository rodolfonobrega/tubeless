import sys
sys.path.insert(0, "/app")
from yt_dlp.networking.impersonate import ImpersonateTarget
import yt_dlp
from yt_dlp.networking import Request

video_id = "dQw4w9WgXcQ"
url = f"https://www.youtube.com/watch?v={video_id}"

# Try different player clients - mweb, tv_embedded, mediaconnect
for client in ["mweb", "tv_embedded", "web_creator"]:
    print(f"\n--- Testing client: {client} ---")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "impersonate": ImpersonateTarget("chrome"),
        "cookiefile": "/app/cookies.txt",
        "js_runtimes": {"node": {}},
        "remote_components": {"ejs:github"},
        "extractor_args": {"youtube": {"player_client": [client]}},
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        en_sub = info.get("subtitles", {}).get("en") or info.get("automatic_captions", {}).get("en")
        if not en_sub:
            print("No subtitles found")
            continue

        vtt_entry = next((e for e in en_sub if e.get("ext") == "vtt"), en_sub[0])
        sub_url = vtt_entry["url"]

        with yt_dlp.YoutubeDL(opts) as ydl2:
            response = ydl2.urlopen(Request(sub_url))
            content = response.read().decode("utf-8")
            print(f"SUCCESS! {len(content)} bytes")
            print(content[:200])
            break
    except Exception as e:
        print(f"Failed: {str(e)[:100]}")
