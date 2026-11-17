"""Append the opening story cleanly, assemble its video, and write upload metadata."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from .__main__ import main as assemble

ROOT = Path(__file__).resolve().parents[1]


def copy_audio(source, sink, frames=None):
    with wave.open(str(source), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24000):
            raise ValueError("Expected mono 24kHz PCM16 source audio")
        remaining = audio.getnframes() if frames is None else frames
        if remaining > audio.getnframes():
            raise ValueError("Requested audio exceeds source")
        while remaining:
            count = min(remaining, 24000 * 10)
            data = audio.readframes(count)
            if not data:
                raise ValueError("Unexpected end of source audio")
            sink.writeframesraw(data)
            remaining -= len(data) // 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice-python", type=Path, required=True)
    args = parser.parse_args()
    folder = ROOT / "outputs/videos/wizard-collection"
    package = ROOT / "outputs/packaging/wizard-collection"
    folder.mkdir(parents=True, exist_ok=True)
    package.mkdir(parents=True, exist_ok=True)
    status = folder / "job-status.json"

    def update(state, **data):
        status.write_text(json.dumps({"state": state, **data}, indent=2), encoding="utf-8")
        print(state, data, flush=True)

    try:
        source = ROOT / "outputs/voice/wizard-three-hours-fixed.wav"
        receipt = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
        collection = json.loads((ROOT / "story_creator/stories/wizard-three-hours-20261117/collection.json").read_text())
        first = (ROOT / collection["stories"][0]["file"]).read_text(encoding="utf-8").split()
        chunks = receipt["recipe"]["chunks"]
        cache = Path(receipt["chunk_cache"])
        if not cache.is_absolute():
            cache = ROOT / cache
        prefix_words, complete_chunks = [], 0
        for text in chunks:
            candidate = prefix_words + text.split()
            if len(candidate) > len(first):
                break
            prefix_words = candidate
            complete_chunks += 1
        if prefix_words != first[:len(prefix_words)]:
            raise ValueError("Story does not match narration receipt")
        tail = " ".join(first[len(prefix_words):])
        if tail and chunks[complete_chunks].split()[:len(tail.split())] != tail.split():
            raise ValueError("Boundary text does not match first story")
        from voice.speaker import load_profile
        profile = load_profile("wizard")
        if profile != receipt["recipe"]["profile"]:
            raise ValueError("Speaker profile differs from completed collection")
        tail_wav = folder / "opening-ending.wav"
        if tail and not tail_wav.exists():
            tail_text = folder / "opening-ending.txt"
            tail_text.write_text(tail, encoding="utf-8")
            update("rendering_boundary", words=len(tail.split()))
            subprocess.run([str(args.voice_python), "-u", "-m", "voice", "narrate", str(tail_text),
                            "--profile", "wizard", "--out", str(tail_wav)], cwd=ROOT, check=True)
        opening = folder / "opening-repeat.wav"
        if not opening.exists():
            update("reconstructing_opening")
            temporary = opening.with_suffix(".partial.wav")
            with wave.open(str(temporary), "wb") as sink:
                sink.setnchannels(1)
                sink.setsampwidth(2)
                sink.setframerate(24000)
                for index in range(complete_chunks):
                    if index:
                        sink.writeframesraw(b"\0\0" * 14400)
                    copy_audio(cache / f"{index + 1:04d}.wav", sink)
                if tail:
                    if complete_chunks:
                        sink.writeframesraw(b"\0\0" * 14400)
                    copy_audio(tail_wav, sink)
            temporary.replace(opening)
        audio_path = folder / "narration-with-opening-repeat.wav"
        with wave.open(str(source), "rb") as audio:
            original_seconds = audio.getnframes() / 24000
        if not audio_path.exists():
            update("appending_opening")
            temporary = audio_path.with_suffix(".partial.wav")
            with wave.open(str(temporary), "wb") as sink:
                sink.setnchannels(1)
                sink.setsampwidth(2)
                sink.setframerate(24000)
                copy_audio(source, sink)
                sink.writeframesraw(b"\0\0" * 48000)
                copy_audio(opening, sink)
            temporary.replace(audio_path)
        with wave.open(str(audio_path), "rb") as audio:
            seconds = audio.getnframes() / 24000
        title = "Fall Asleep at Hogwarts | 3+ Hours of Cosy Harry Potter Stories"
        titles = [row["title"] for row in collection["stories"]]
        replay = round(original_seconds + 2)
        replay_time = f"{replay // 3600}:{replay // 60 % 60:02d}:{replay % 60:02d}"
        runtime = f"{int(seconds) // 3600}:{int(seconds) // 60 % 60:02d}:{int(seconds) % 60:02d}"
        from video_packaging.description import render_description
        description = render_description(
            opening="Leave the day behind and settle into Hogwarts after hours with this cosy Harry Potter sleep-story collection for adults.",
            seconds=seconds, experience="gentle narration, familiar characters and a softly animated greenhouse scene.",
            synopsis="Six original, unofficial fan-created stories follow Neville, Hermione, Harry, Ron, Luna, Hagrid and Professor McGonagall through quiet tasks, warm conversations and peaceful evenings.",
            hashtags=("#HarryPotter", "#SleepStories", "#BedtimeStoriesForAdults"))
        if seconds < 10800:
            raise ValueError("Result is below three hours; refusing the proposed title")
        (package / "title.txt").write_text(title + "\n", encoding="utf-8")
        (package / "description.txt").write_text(description, encoding="utf-8")
        shutil.copyfile(ROOT / "outputs/packaging/lemon-balm/thumbnail.jpg", package / "thumbnail.jpg")
        (package / "metadata.json").write_text(json.dumps({"title": title, "runtime_seconds": seconds,
            "repeated_story": titles[0], "repeat_start_seconds": replay, "stories": titles,
            "thumbnail": "thumbnail.jpg", "reference_sha256": profile["reference_sha256"],
            "boundary_note": "Original completed chunks reused; only the mixed-story boundary ending was re-rendered."}, indent=2), encoding="utf-8")
        preset = folder / "assembly.json"
        preset.write_text(json.dumps({"video": "outputs/animation/lemon-balm/greenhouse-loop.mp4",
            "audio": str(audio_path.relative_to(ROOT)), "output": "outputs/videos/wizard-collection/final.mp4"}, indent=2), encoding="utf-8")
        update("assembling_video", runtime=runtime)
        final_video = folder / "final.mp4"
        if not final_video.exists():
            subprocess.run([sys.executable, "-u", "-m", "video_assembly", str(preset)], cwd=ROOT, check=True)
        update("complete", video=str(final_video), packaging=str(package), runtime=runtime)
    except BaseException as error:
        update("failed", error=str(error))
        raise


if __name__ == "__main__":
    main()
