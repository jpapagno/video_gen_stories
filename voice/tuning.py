"""Conservative pacing, treble and gain processing for voice auditions."""
import argparse
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--wpm", type=float, default=136)
    parser.add_argument("--rms-db", type=float, default=-24.47)
    args = parser.parse_args()
    text = json.loads(args.settings.read_text(encoding="utf-8"))["text"]
    words = len(re.findall(r"\b\w+(?:['’-]\w+)*\b", text))
    info = sf.info(args.source)
    target_duration = words / args.wpm * 60
    tempo = info.duration / target_duration
    if not 0.7 <= tempo <= 1.3:
        raise ValueError("Required pace change is too large for this conservative audition.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(args.source),
                    "-af", f"atempo={tempo:.6f},equalizer=f=3500:t=o:w=1:g=-2,lowpass=f=9500",
                    "-c:a", "pcm_s16le", str(args.output)], check=True)
    audio, rate = sf.read(args.output, dtype="float32")
    rms = float(np.sqrt(np.mean(audio ** 2)))
    gain = min(10 ** (args.rms_db / 20) / max(rms, 1e-12), 0.95 / max(float(np.max(np.abs(audio))), 1e-12))
    sf.write(args.output, audio * gain, rate, subtype="PCM_16")
    metadata = {"source": str(args.source), "text": text, "words": words,
                "pace_target_wpm": args.wpm, "duration_seconds": len(audio) / rate,
                "atempo": tempo, "treble_eq_db": -2, "eq_hz": 3500,
                "rms_target_dbfs": args.rms_db, "gain": gain,
                "note": "Pace, brightness and loudness tuning only; no reference voice cloning or identity matching."}
    args.output.with_suffix(".tuning.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
