"""Command-line entry point: python -m voice."""
import argparse
import json
import runpy
import sys
from pathlib import Path

from . import ROOT, selected_profile


def main():
    parser = argparse.ArgumentParser(description="Local Qwen voice module; default profile is V6 clean.")
    parser.add_argument("command", choices=["profile", "rebuild", "audition", "narrate", "download", "measure", "match", "refine", "tune"])
    args, rest = parser.parse_known_args()
    if args.command == "profile":
        if rest:
            parser.error("profile does not accept additional arguments")
        print(json.dumps(selected_profile(), indent=2))
        return
    modules = {"rebuild": "cleanup", "audition": "audition", "narrate": "narrate", "download": "download", "measure": "features",
               "match": "processing", "refine": "refinement", "tune": "tuning"}
    if args.command in ("rebuild", "download", "refine") and rest:
        parser.error(f"{args.command} does not accept additional arguments")
    if args.command == "audition":
        if "--variants" not in rest:
            rest.extend(["--variants", str(Path(__file__).parent / "profiles/v6-source.json")])
        if "--out" not in rest:
            rest.extend(["--out", str(ROOT / "outputs/voice/raw-v6")])
        if "--decoder-cpu" not in rest:
            rest.append("--decoder-cpu")
    sys.argv = [f"voice.{modules[args.command]}", *rest]
    runpy.run_module(f"voice.{modules[args.command]}", run_name="__main__")


if __name__ == "__main__":
    main()
