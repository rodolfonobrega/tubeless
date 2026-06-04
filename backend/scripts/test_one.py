import asyncio, sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
from app.services.transcript_service import TranscriptService

VID = '_cAfSxeu_nY'

svc = TranscriptService()
raw, segs, lang, _, meta = asyncio.run(svc.fetch_transcript(VID))
title = meta.get('title', '')
print(f'title={title!r}')
print(f'segments={len(segs)}')
if segs:
    print(f'first={segs[0].text!r}')
else:
    print('NO SEGMENTS')
