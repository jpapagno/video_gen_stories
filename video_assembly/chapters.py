"""Validate measured audio boundaries and export final-video chapter times."""
import hashlib
import json
import math
import wave
from fractions import Fraction


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(8 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()


def load_audio_chapters(audio, explicit=None):
    path = explicit or audio.with_suffix(".chapters.json")
    if not path.exists():
        if explicit:
            raise FileNotFoundError(path)
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    with wave.open(str(audio), "rb") as source:
        rate, frames = source.getframerate(), source.getnframes()
    if (data["sample_rate"], data["total_frames"]) != (rate, frames) or data["audio_sha256"] != file_hash(audio):
        raise ValueError("Chapter manifest does not match audio; regenerate it")
    previous = -1
    for chapter in data["chapters"]:
        frame = chapter["start_frame"]
        if not isinstance(frame, int) or not previous < frame < frames or not chapter["title"].strip():
            raise ValueError("Invalid or unordered chapter boundary")
        previous = frame
    if not data["chapters"] or data["chapters"][0]["start_frame"] != 0:
        raise ValueError("Audio chapters must begin at frame zero")
    return data


def timestamp(seconds):
    seconds = math.floor(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def export_chapters(output, audio_chapters, intro, description=None):
    if audio_chapters is None:
        return None
    rate = audio_chapters["sample_rate"]
    offset = Fraction(round(intro["story_start_seconds"] * rate), rate)
    rows = []
    if offset:
        rows.append({"title": "Welcome & settling in", "start_seconds": 0., "timestamp": "0:00"})
    for chapter in audio_chapters["chapters"]:
        start = offset + Fraction(chapter["start_frame"], rate)
        rows.append({"title": chapter["title"], "start_frame_in_narration": chapter["start_frame"],
                     "start_seconds": float(start), "timestamp": timestamp(start)})
    text = "\n".join(f"{r['timestamp']} {r['title']}" for r in rows) + "\n"
    result = {"precision": "measured audio sample boundaries; display timestamps rounded down",
              "sample_rate": rate, "intro_offset_seconds": float(offset), "chapters": rows}
    output.with_suffix(".chapters.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    output.with_suffix(".chapters.txt").write_text(text, encoding="utf-8")
    if description:
        from video_packaging.chapters import update_description
        update_description(description, text)
    return result
