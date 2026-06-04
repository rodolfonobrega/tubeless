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
    "allow_unplayable_formats": False,
    "extractor_args": {},
}

# Enable remote component download (EJS challenge solver from GitHub)
import yt_dlp.utils as utils
# Try to set allow_remote_components
opts_with_remote = {**opts, "allow_remote_components": True}

video_id = "dQw4w9WgXcQ"
url = f"https://www.youtube.com/watch?v={video_id}"

try:
    with yt_dlp.YoutubeDL(opts_with_remote) as ydl:
        info = ydl.extract_info(url, download=False)
    print(f"Title: {info.get('title')}")
    en_sub = info.get("subtitles", {}).get("en") or info.get("automatic_captions", {}).get("en")
    if en_sub:
        vtt_entry = next((e for e in en_sub if e.get("ext") == "vtt"), en_sub[0])
        sub_url = vtt_entry["url"]
        with yt_dlp.YoutubeDL(opts_with_remote) as ydl2:
            response = ydl2.urlopen(Request(sub_url))
            content = response.read().decode("utf-8")
            print(f"SUCCESS! {len(content)} bytes")
            print(content[:200])
except Exception as e:
    print(f"Error: {e}")
    # Try listing valid options
    import inspect
    init_src = inspect.getsource(yt_dlp.YoutubeDL.__init__)
    idx = init_src.find("remote_components")
    if idx != -1:
        print("Found remote_components in __init__:", init_src[idx:idx+200])
