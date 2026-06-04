"""Quick test to verify transcript DOM scraping works after stylesheet unblock fix."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.transcript_service import TranscriptService

VIDEOS = ["RpHFoxiryY0", "b5EWWdzzOpc", "4UWzpJkxPkE"]

async def main():
    svc = TranscriptService()
    for vid in VIDEOS:
        try:
            raw, segs, lang, _, meta = await svc.fetch_transcript(vid)
            title = meta.get("title", "") or vid
            if segs:
                print(f"OK    {vid}  lang={lang}  segments={len(segs)}  title={title!r}")
            else:
                print(f"FAIL  {vid}  no segments  title={title!r}")
        except Exception as e:
            print(f"ERR   {vid}  {e}")

if __name__ == "__main__":
    asyncio.run(main())
