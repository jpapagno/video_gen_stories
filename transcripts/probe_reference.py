"""Probe a few late-video positions to distinguish caption coverage from video duration."""
import concurrent.futures
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import soundfile as sf
import yt_dlp

from . import ROOT
from voice.features import speech_regions


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=DqE40ZHyF7E"
    folder = ROOT / "media/transcript-research"
    folder.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True, "format": "bestaudio"}) as ydl:
        info = ydl.extract_info(url, download=False)
    # The transient signed media URL is never written or printed.
    media_url = info["url"]

    def probe(start):
        path = folder / f"late-{start}.wav"
        if not path.exists():
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-ss", str(start),
                            "-i", media_url, "-t", "12", "-ac", "1", "-ar", "16000", str(path)],
                           check=True, capture_output=True)
        x, sr = sf.read(path)
        regions, _ = speech_regions(x, sr)
        return {"start_seconds": start, "duration_seconds": len(x) / sr,
                "detected_speech_seconds": sum(b - a for a, b in regions), "regions": regions}

    probes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in [pool.submit(probe, t) for t in (10440, 12600, 16200)]:
            try:
                result = future.result()
                probes.append(result)
                print(json.dumps(result), flush=True)
            except Exception:
                probes.append({"error": "Late audio probe failed; do not infer absence of speech from caption gaps alone."})
    result = {"url": url, "title": info["title"], "channel": info.get("channel"),
              "duration_seconds": info["duration"], "chapters": info.get("chapters"), "probes": probes,
              "limitation": "Sparse 12-second probes cannot establish that an entire uncaptained tail is speech-free."}
    (folder / "reference-metadata.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
