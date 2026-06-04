import sys
sys.path.insert(0, "/app")
from yt_dlp.networking.impersonate import ImpersonateTarget
import yt_dlp
import tempfile, os, glob as glob_mod

opts = {
    "quiet": False,
    "no_warnings": False,
    "verbose": True,
    "extract_flat": False,
    "retries": 2,
    "impersonate": ImpersonateTarget("chrome"),
    "js_runtimes": {"node": {}},
    "remote_components": {"ejs:github"},
    "extractor_args": {
        "youtubepot-bgutilhttp": {"base_url": ["http://host.docker.internal:4416"]},
    },
    "writesubtitles": True,
    "writeautomaticsub": True,
    "skip_download": True,
    "subtitleslangs": ["en", "pt", "pt-BR"],
    "subtitlesformat": "vtt",
}

with tempfile.TemporaryDirectory() as tmpdir:
    opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=True)

    vtt_files = glob_mod.glob(os.path.join(tmpdir, "*.vtt"))
    if vtt_files:
        print(f"\nSUCCESS: {vtt_files[0]}")
        print(open(vtt_files[0]).read()[:200])
    else:
        print("\nFAILED: no vtt files")
