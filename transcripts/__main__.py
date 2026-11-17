import argparse
import json
import random
from pathlib import Path

from . import HOME
from . import client
from .pipeline import benchmark, draft, review, revise


def main():
    parser = argparse.ArgumentParser(description="Local scene-by-scene bedtime-story drafting; nothing is auto-accepted.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pull")
    commands.add_parser("sample", help="Run the current measured third-person quiet-task experiment")
    commands.add_parser("legacy-sample", help="Replay the historical second-person arrival experiment")
    d = commands.add_parser("draft")
    d.add_argument("scene")
    d.add_argument("--prompt", choices=["a", "b"], default="b")
    d.add_argument("--case")
    b = commands.add_parser("benchmark")
    b.add_argument("--cases", nargs="+", default=["arrival"])
    b.add_argument("--review", action="store_true")
    for command in ("review", "revise"):
        p = commands.add_parser(command)
        p.add_argument("draft", type=Path)
    args = parser.parse_args()
    if args.command == "pull":
        print(json.dumps(client.pull(), indent=2))
    elif args.command == "sample":
        from .reference_trial import main as sample
        print(sample())
    elif args.command == "legacy-sample":
        from .segmented import sample
        print(sample())
    elif args.command == "draft":
        case = benchmark(args.case) if args.case else None
        if case and case["scene_id"] != args.scene:
            parser.error("Benchmark case must correspond to the requested scene")
        print(draft(args.scene, args.prompt, case))
    elif args.command == "review":
        print(json.dumps(review(args.draft), indent=2))
    elif args.command == "revise":
        print(revise(args.draft))
    elif args.command == "benchmark":
        output = HOME / "benchmarks"
        output.mkdir(exist_ok=True)
        for case_id in args.cases:
            case = benchmark(case_id)
            paths = [draft(case["scene_id"], variant, case) for variant in ("a", "b")]
            if args.review:
                for path in paths:
                    review(path)
            random.Random(734).shuffle(paths)
            lines = [f"# Blind comparison: {case_id}", "", "Compare readability aloud, relevant detail, gentle movement, continuity, calm and repetition. Both samples are local drafts, not approved story text.", ""]
            mapping = {}
            for number, path in enumerate(paths, 1):
                label = f"Sample {number}"
                mapping[label] = str(path.relative_to(HOME))
                lines += [f"## {label}", "", path.read_text(encoding="utf-8"), ""]
            (output / f"{case_id}-blind.md").write_text("\n".join(lines), encoding="utf-8")
            (output / f"{case_id}-mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
            print(f"Blind comparison: {output / (case_id + '-blind.md')}", flush=True)


if __name__ == "__main__":
    main()
