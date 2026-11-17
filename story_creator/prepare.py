"""Small, conservative pronunciation fixes before TTS and sentence chunking."""
import argparse
import re
from pathlib import Path

from .numbers import spell_numbers


def prepare_text(text):
    text = re.sub(r"(?m)^\s*#+\s+.*$", "", text)
    text = text.replace("*", "")
    # St. can also mean Street: expand this known proper name, not every St.
    text = re.sub(r"\bSt\.\s+(?=Jude\b)", "Saint ", text)
    titles = {"Mr": "Mister", "Mrs": "Missus", "Ms": "Miz",
              "Dr": "Doctor", "Prof": "Professor"}
    for short, spoken in titles.items():
        text = re.sub(rf"\b{short}\.?\s+(?=[A-Z])", spoken + " ", text)
    return spell_numbers(text).strip()


def prepare_file(source, target):
    source, target = Path(source), Path(target)
    text = prepare_text(source.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as output:
        output.write(text + "\n")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(prepare_file(args.input, args.out).resolve())


if __name__ == "__main__":
    main()
