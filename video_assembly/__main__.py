import argparse
import hashlib
import json
import subprocess
import time
import wave
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]


def video_info(path):
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
    try:
        info = next(reader)
        return {k: info.get(k) for k in ("size", "fps", "duration", "codec", "audio_codec")}
    finally:
        reader.close()


def plan(config):
    video, audio, output = (ROOT / config[k] for k in ("video", "audio", "output"))
    if video.resolve() == output.resolve() or audio.resolve() == output.resolve():
        raise ValueError("Output cannot replace an input")
    with wave.open(str(audio), "rb") as source:
        duration = source.getnframes() / source.getframerate()
    info = video_info(video)
    if duration <= 0 or not info["duration"] or info["duration"] <= 0:
        raise ValueError("Both sources must have a positive duration")
    return video, audio, output, duration, info


def main():
    parser = argparse.ArgumentParser(description="Loop an animated scene under finished WAV narration")
    parser.add_argument("preset", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    video, audio, output, duration, source_info = plan(config)
    print(json.dumps({"output": str(output), "narration_minutes": round(duration / 60, 2),
                      "video_loop_seconds": source_info["duration"], "video_stream_copy": True}, indent=2), flush=True)
    if args.plan_only:
        return
    if output.exists():
        raise FileExistsError(f"Preserving existing {output}; choose a new output")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".partial.mp4")
    start = time.monotonic()
    # Explicit maps discard any accidental audio in the animation. Do not loop
    # narration, add music, burn captions or silently pad the episode's runtime.
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "warning", "-y",
               "-stream_loop", "-1", "-i", str(video), "-i", str(audio),
               "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "192k", "-t", str(duration),
               "-movflags", "+faststart", str(temporary)]
    with output.with_suffix(".assembly.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, stderr=log, check=True)
    info = video_info(temporary)
    if abs(info["duration"] - duration) > .25 or not info["audio_codec"]:
        raise ValueError("Output duration/audio verification failed; partial file retained")
    temporary.replace(output)
    manifest = {"status": "complete", "preset": config, "output": str(output),
                "duration_seconds": info["duration"], "narration_duration_seconds": duration,
                "video": info, "elapsed_seconds": round(time.monotonic() - start, 2),
                "sources": {"audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
                            "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()},
                "features": {"spoken_narration": True, "looped_scene": True,
                             "music": False, "rain_sound_effects": False, "burned_captions": False}}
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    main()
