import sys
sys.path.insert(0, "/app")
import yt_dlp
import requests
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

auto = info.get("automatic_captions", {})
subs = info.get("subtitles", {})

# Find English subtitle URL
lang_data = subs.get("en") or subs.get("en-US") or auto.get("en") or auto.get("en-US")
if not lang_data:
    # Try any language
    lang_data = next(iter((subs or auto).values()), None)

print(f"Found {len(lang_data)} formats")
for e in lang_data:
    print(f"  {e.get('ext')}: {str(e.get('url',''))[:100]}")

# Find json3 or vtt format
url = None
for e in lang_data:
    if e.get("ext") == "json3":
        url = e["url"]
        break
if not url:
    url = lang_data[0]["url"]

print(f"\nDownloading: {url[:80]}...")

# Download with requests using cookies from file
import http.cookiejar
jar = http.cookiejar.MozillaCookieJar("/app/cookies.txt")
try:
    jar.load(ignore_discard=True, ignore_expires=True)
except Exception as e:
    print(f"Cookie load error: {e}")

session = requests.Session()
session.cookies = jar
session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
session.headers["Referer"] = "https://www.youtube.com/"

resp = session.get(url, timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    print(f"Content length: {len(resp.text)}")
    print(resp.text[:200])
