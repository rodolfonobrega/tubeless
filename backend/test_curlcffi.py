import sys
sys.path.insert(0, "/app")
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from curl_cffi import requests as cffi_requests

opts = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "impersonate": ImpersonateTarget("chrome"),
    "cookiefile": "/app/cookies.txt",
}

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=mmJWFvZFktI", download=False)

auto = info.get("automatic_captions", {})
en = auto.get("en") or auto.get("en-US") or next(iter(auto.values()), [])

vtt_entry = next((e for e in en if e.get("ext") == "vtt"), en[0] if en else None)
url = vtt_entry["url"]
print(f"URL: {url[:80]}")

resp = cffi_requests.get(
    url,
    impersonate="chrome124",
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.youtube.com/",
        "Accept-Language": "en-US,en;q=0.9",
    },
    timeout=30,
)
print(f"Status: {resp.status_code}")
if resp.ok:
    print(resp.text[:300])
else:
    print(resp.text[:200])
