"""Generate the standard fixed-speaker intro and rebuild the wizard collection."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def timestamp(seconds):
    seconds = round(seconds)
    return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice-python", type=Path, required=True)
    args = parser.parse_args()
    folder = ROOT / "outputs/videos/wizard-collection"
    status = folder / "intro-job-status.json"

    def update(state, **fields):
        status.write_text(json.dumps({"state": state, **fields}, indent=2), encoding="utf-8")
        print(state, fields, flush=True)

    try:
        intro = ROOT / "outputs/voice/intros/hogwarts-wizard.wav"
        if not intro.exists():
            update("generating_intro")
            subprocess.run([str(args.voice_python), "-u", "-m", "voice", "narrate",
                "video_assembly/intros/hogwarts.txt", "--profile", "wizard", "--out", str(intro)], cwd=ROOT, check=True)
        # Ensure an old design-based clip can never silently become the standard intro.
        receipt = json.loads(intro.with_suffix(".json").read_text(encoding="utf-8"))
        from voice.speaker import load_profile
        if receipt["recipe"]["workflow"] != "fixed-speaker-v1" or receipt["recipe"]["profile"] != load_profile("wizard"):
            raise ValueError("Intro does not use the approved fixed Wizard speaker")
        preset = folder / "assembly-with-intro.json"
        config = json.loads((folder / "assembly.json").read_text(encoding="utf-8"))
        config.update(output="outputs/videos/wizard-collection/final-with-intro.mp4",
                      intro="outputs/voice/intros/hogwarts-wizard.wav", intro_lead_seconds=1.0, intro_pause_seconds=2.8)
        preset.write_text(json.dumps(config, indent=2), encoding="utf-8")
        update("assembling_video")
        final = ROOT / config["output"]
        if not final.exists():
            subprocess.run([sys.executable, "-u", "-m", "video_assembly", str(preset)], cwd=ROOT, check=True)
        manifest = json.loads(final.with_suffix(".json").read_text(encoding="utf-8"))
        package = ROOT / "outputs/packaging/wizard-collection"
        metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
        # Derive from the original timing so retries cannot add the intro twice.
        base_duration = 0
        import wave
        with wave.open(str(ROOT / "outputs/voice/wizard-three-hours-fixed.wav"), "rb") as audio:
            base_duration = audio.getnframes() / audio.getframerate()
        offset = manifest["intro"]["story_start_seconds"]
        metadata.update(runtime_seconds=manifest["duration_seconds"], intro_seconds=offset,
                        first_story_start_seconds=offset, repeat_start_seconds=round(base_duration + 2 + offset),
                        video=str(final))
        (package / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        description_path = package / "description.txt"
        description = description_path.read_text(encoding="utf-8")
        from video_packaging.description import duration_label
        description = re.sub(r"Enjoy (?:\d+:\d{2}:\d{2}|\d+ (?:hours|minutes)) of",
                             f"Enjoy {duration_label(manifest['duration_seconds'])} of", description)
        description = re.sub(r"beginning at \d+:\d{2}:\d{2}", f"beginning at {timestamp(metadata['repeat_start_seconds'])}", description)
        note = "A short settling-in introduction opens the video, followed by a quiet pause before the first story."
        if note not in description:
            description = description.replace("Six original", note + "\n\nSix original", 1)
        description_path.write_text(description, encoding="utf-8")
        update("complete", video=str(final), runtime=timestamp(manifest["duration_seconds"]),
               intro_seconds=receipt["audio_seconds"], first_story_start_seconds=offset)
    except BaseException as error:
        update("failed", error=str(error))
        raise


if __name__ == "__main__":
    main()
