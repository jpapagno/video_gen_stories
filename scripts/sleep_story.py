"""Sleep-story pipeline. Default operation is local and never calls ElevenLabs."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sleep_story_lib.story import load_story, export_script, estimate
from sleep_story_lib.audio import generate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "generate"])
    parser.add_argument("--story", type=Path, default=ROOT / "stories/hogwarts-night/prototype.json")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/sleep-story")
    parser.add_argument("--approved-script", action="store_true", help="Explicitly authorize paid/credit-consuming synthesis of this script")
    parser.add_argument("--max-characters", type=int, default=10000, help="Local total request character ceiling, not a provider credit guarantee")
    args = parser.parse_args()
    story = load_story(args.story)
    if args.command == "prepare":
        path = export_script(story, args.story.with_name("prototype-script.md"))
        print(json.dumps({**estimate(story), "transcript": str(path), "network_requests": 0}, indent=2))
        return
    if not args.approved_script:
        parser.error("Generation requires --approved-script after transcript review. No request sent.")
    # Minimal dotenv support; existing environment always wins. Never print secrets.
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
    generate(story, args.out, args.max_characters)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
