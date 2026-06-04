import asyncio, sys
sys.path.insert(0, "/app")
from app.services.transcript_service import TranscriptService

async def test():
    svc = TranscriptService()
    raw, segs, lang, chapters, meta = await svc.fetch_transcript("mmJWFvZFktI")
    title = meta["title"]
    print(f"title: {title}")
    print(f"lang: {lang}, segments: {len(segs)}")

asyncio.run(test())
