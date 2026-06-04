import sys
sys.path.insert(0, "/app")
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

opts = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "impersonate": ImpersonateTarget("chrome"),
    "cookiefile": "/app/cookies.txt",
}

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=mmJWFvZFktI", download=False)

subs = info.get("subtitles", {})
auto = info.get("automatic_captions", {})
print("subtitles langs:", list(subs.keys())[:5])
print("auto_captions langs:", list(auto.keys())[:5])

# Show what a subtitle entry looks like
for lang, entries in list((subs or auto).items())[:1]:
    print(f"\nLang: {lang}, entries: {len(entries)}")
    for e in entries[:3]:
        print(f"  format={e.get('ext')}, url={str(e.get('url',''))[:80]}")
