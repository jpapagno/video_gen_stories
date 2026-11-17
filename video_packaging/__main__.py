import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path(__file__).resolve().parent


def build(brief):
    facts = json.loads(brief.read_text(encoding="utf-8"))
    story = (ROOT / facts["story"]).read_text(encoding="utf-8")
    manifest = ROOT / facts["assembly_manifest"]
    if manifest.exists():
        video = json.loads(manifest.read_text(encoding="utf-8"))
        if video.get("status") != "complete":
            raise ValueError("Assembly manifest is not complete")
        facts.update(measured_runtime_seconds=video["duration_seconds"],
                     verified_video_features=video["features"])
        for key in ("music", "rain_sound_effects", "burned_captions"):
            if facts[key] != video["features"][key]:
                raise ValueError(f"Brief contradicts verified video feature: {key}")
    else:
        facts["measured_runtime_seconds"] = None
    research = (HOME / "research/patterns.md").read_text(encoding="utf-8")
    research += "\n\n" + (HOME / "research/examples.json").read_text(encoding="utf-8")
    template = (HOME / "prompts/package.md").read_text(encoding="utf-8")
    # One substitution pass: story text cannot introduce additional placeholders.
    import re
    values = {"FACTS": json.dumps(facts, indent=2), "STORY": story, "RESEARCH": research}
    return re.sub(r"\{\{(FACTS|STORY|RESEARCH)\}\}", lambda m: values[m[1]], template)


def main():
    parser = argparse.ArgumentParser(description="Build a ready-to-use packaging prompt; no API calls")
    parser.add_argument("brief", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    prompt = build(args.brief)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as target:
        target.write(prompt)
    print(args.out.resolve())


if __name__ == "__main__":
    main()
