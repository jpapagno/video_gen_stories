"""Render stories independently and assemble exact sample-count chapter boundaries."""
import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

from .speaker import load_profile
from video_assembly.chapters import file_hash

ROOT = Path(__file__).resolve().parents[1]


def join_stories(stories, output, gap_seconds=2.):
    if output.exists():
        raise FileExistsError(output)
    if gap_seconds < 0 or not stories:
        raise ValueError("Need stories and a nonnegative gap")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".partial.wav")
    rows, cursor = [], 0
    with wave.open(str(temporary), "wb") as sink:
        sink.setnchannels(1)
        sink.setsampwidth(2)
        sink.setframerate(24000)
        for index, (title, path) in enumerate(stories):
            if index:
                gap = round(gap_seconds * 24000)
                sink.writeframesraw(b"\0\0" * gap)
                cursor += gap
            rows.append({"title": title, "start_frame": cursor, "source_audio": str(path)})
            with wave.open(str(path), "rb") as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 24000):
                    raise ValueError("Story audio must be mono PCM16 at 24kHz")
                while data := source.readframes(240000):
                    sink.writeframesraw(data)
                    cursor += len(data) // 2
    temporary.replace(output)
    manifest = {"sample_rate": 24000, "total_frames": cursor, "audio_sha256": file_hash(output), "chapters": rows}
    output.with_suffix(".chapters.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", type=Path, help="Collection JSON containing stories with title and file")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", default="wizard")
    parser.add_argument("--repeat-first", action="store_true")
    parser.add_argument("--gap-seconds", type=float, default=2.)
    parser.add_argument("--voice-python", default=sys.executable)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    profile = load_profile(args.profile)
    collection = json.loads(args.collection.read_text(encoding="utf-8"))
    stories = []
    folder = args.out.parent / (args.out.stem + "-stories")
    folder.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(collection["stories"], 1):
        audio = folder / f"{index:02d}.wav"
        text = ROOT / row["file"]
        if not audio.exists():
            subprocess.run([args.voice_python, "-u", "-m", "voice", "narrate", str(text),
                            "--profile", args.profile, "--out", str(audio)], check=True, cwd=ROOT)
        receipt = json.loads(audio.with_suffix(".json").read_text(encoding="utf-8"))
        if receipt["recipe"]["profile"] != profile or " ".join(receipt["recipe"]["chunks"]).split() != text.read_text(encoding="utf-8").split():
            raise ValueError("Saved story audio does not match the requested speaker/text")
        stories.append((row["title"], audio))
    if args.repeat_first:
        stories.append((stories[0][0] + " — repeat", stories[0][1]))
    manifest = join_stories(stories, args.out, args.gap_seconds)
    print(f"Saved {args.out}: {len(manifest['chapters'])} exact chapter boundaries", flush=True)


if __name__ == "__main__":
    main()
