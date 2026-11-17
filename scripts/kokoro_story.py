"""Render reviewed narration with local Kokoro. No cloud voice API calls."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from sleep_story_lib.story import load_story
from sleep_story_lib.timeline import build_timeline, join_wavs

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story", type=Path, default=ROOT / "stories/hogwarts-night/prototype.json")
    parser.add_argument("--models", type=Path, default=ROOT / "media/kokoro")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/sleep-story/kokoro")
    parser.add_argument("--voice", default="bm_george")
    parser.add_argument("--speed", type=float, default=0.85)
    args = parser.parse_args()
    if not 0.5 <= args.speed <= 1.5:
        parser.error("Speed must be between 0.5 and 1.5.")
    story = load_story(args.story)
    model = args.models / "kokoro-v1.0.onnx"
    voices = args.models / "voices-v1.0.bin"
    for path in (model, voices):
        if not path.exists():
            parser.error(f"Missing model asset: {path}. See Kokoro setup in story README.")
    engine = Kokoro(str(model), str(voices))
    model_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (model, voices)}
    args.out.mkdir(parents=True, exist_ok=True)
    cache = args.out / "cache"
    cache.mkdir(exist_ok=True)
    chapter_paths = []
    paragraphs = []
    cursor = 0.0
    for chapter in story["chapters"]:
        parts = []
        for index, text in enumerate(chapter["text"].split("\n\n")):
            signature = {"text": text, "voice": args.voice, "speed": args.speed,
                         "language": "en-gb", "models": model_hashes, "runtime": "kokoro-onnx-0.6.1"}
            digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
            path = cache / f"{digest}.wav"
            if not path.exists():
                print(f"Rendering {chapter['id']}, paragraph {index + 1}", flush=True)
                samples, rate = engine.create(text, voice=args.voice, speed=args.speed, lang="en-gb")
                if rate != 24000 or not np.isfinite(samples).all() or len(samples) == 0:
                    raise ValueError("Invalid Kokoro output.")
                sf.write(path, samples, rate, subtype="PCM_16")
            samples, rate = sf.read(path, dtype="float32")
            # Gentle paragraph spacing; no fake three-hour padding.
            gap = 1.2 if index < len(chapter["text"].split("\n\n")) - 1 else 2.0
            duration = len(samples) / rate
            paragraphs.append({"chapter_id": chapter["id"], "paragraph": index + 1,
                               "start_seconds": cursor, "speech_end_seconds": cursor + duration,
                               "following_pause_seconds": gap, "text": text})
            parts.extend([samples, np.zeros(round(rate * gap), dtype=np.float32)])
            cursor += duration + gap
        chapter_path = args.out / f"{chapter['id']}.wav"
        sf.write(chapter_path, np.concatenate(parts), 24000, subtype="PCM_16")
        chapter_paths.append(chapter_path)
    wav = args.out / "narration.wav"
    join_wavs(chapter_paths, wav)
    timeline = build_timeline(story, chapter_paths)
    timeline.update({"provider": "local-kokoro", "voice": args.voice, "speed": args.speed,
                     "model_hashes": model_hashes, "paragraphs": paragraphs,
                     "image": "map-room.png", "image_scope": "One concept image for prototype; chapter scene briefs remain in scenes."})
    (args.out / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    samples, rate = sf.read(wav)
    sf.write(args.out / "narration.mp3", samples, rate, format="MP3")
    print(json.dumps({"audio": str(wav), "duration_minutes": timeline["duration_seconds"] / 60,
                      "peak": float(np.max(np.abs(samples))), "cloud_voice_requests": 0}, indent=2))
    if story["kind"] == "episode" and not timeline["meets_full_episode_minimum"]:
        raise ValueError("Full episode is under three hours; retained for revision.")


if __name__ == "__main__":
    main()
