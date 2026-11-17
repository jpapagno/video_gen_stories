"""Keep one generated chapter block in an upload description."""
import re


def update_description(path, chapter_text, approximate=False):
    # Viewer-facing label selected by the channel owner. Internal manifests
    # retain the repeat identity and exact source audio.
    chapter_text = re.sub(r" — repeat(?=\n|$)", " — Part 2", chapter_text)
    heading = "Chapters (approximate story transitions):" if approximate else "Chapters:"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = r"(?m)^Chapters(?: \(approximate story transitions\))?:\n(?:\d+:\d{2}(?::\d{2})?[^\n]*\n?)+"
    text = re.sub(pattern, "", text).rstrip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n\n" + heading + "\n" + chapter_text.strip() + "\n", encoding="utf-8")
