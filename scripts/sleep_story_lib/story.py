import json
import re
from pathlib import Path


def words(text):
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def load_story(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("kind") not in ("prototype", "episode"):
        raise ValueError("Story kind must be prototype or episode.")
    if not data.get("title") or not data.get("chapters"):
        raise ValueError("A title and chapters are required.")
    ids = set()
    for chapter in data["chapters"]:
        ident = chapter.get("id", "")
        if not re.fullmatch(r"[a-z0-9-]+", ident) or ident in ids:
            raise ValueError("Chapter IDs must be unique safe slugs.")
        ids.add(ident)
        if not chapter.get("text", "").strip() or not chapter.get("title"):
            raise ValueError(f"Missing narration/title: {ident}")
        if not chapter.get("scene", {}).get("brief"):
            raise ValueError(f"Missing scene brief: {ident}")
    return data


def estimate(story):
    text = "\n\n".join(c["text"] for c in story["chapters"])
    count = words(text)
    return {"title": story["title"], "kind": story["kind"], "words": count,
            "characters": sum(len(c["text"]) for c in story["chapters"]),
            "estimated_minutes": round(count / story["estimated_words_per_minute"], 2),
            "timing_status": "estimate only; measure synthesized audio",
            "scenes": len(story["chapters"])}


def export_script(story, path):
    lines = [f"# {story['title']}", "", "Prototype narration for review. Headings are not spoken.", ""]
    for chapter in story["chapters"]:
        lines.extend([f"## {chapter['title']}", "", chapter["text"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return Path(path)


def chunks(text, limit=3500):
    """Preserve every character; prefer paragraph or sentence boundaries."""
    result = []
    while len(text) > limit:
        split = text.rfind("\n\n", 0, limit + 1)
        if split < limit // 3:
            split = text.rfind(". ", 0, limit)
            split = split + 1 if split >= 0 else -1
        if split < limit // 3:
            split = text.rfind(" ", 0, limit + 1)
        if split <= 0:
            split = limit
        result.append(text[:split])
        text = text[split:]
    if text:
        result.append(text)
    return result
