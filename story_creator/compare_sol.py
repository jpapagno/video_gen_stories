"""One fresh Codex text-generation trial; retain raw output and usage events."""
import json
import shutil
import subprocess
import time
from pathlib import Path

from . import HOME
from .prepare import prepare_file


def main():
    folder = HOME / "comparisons" / time.strftime("%Y%m%d-%H%M%S")
    folder.mkdir(parents=True)
    prompt = (HOME / "prompts/wizard-bedtime.txt").read_text(encoding="utf-8").strip()
    (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
    command = [shutil.which("codex"), "exec", "--ignore-user-config", "--ephemeral",
               "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
               "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="low"',
               "--json", "--output-last-message", str(folder / "raw-story.txt"), "-"]
    print(folder, flush=True)
    start = time.monotonic()
    with (folder / "events.jsonl").open("w", encoding="utf-8") as events, (folder / "stderr.log").open("w", encoding="utf-8") as errors:
        process = subprocess.run(command, input=prompt, text=True, encoding="utf-8",
                                 stdout=events, stderr=errors, cwd=folder)
    receipt = {"model": "gpt-6.1-sol", "reasoning_effort": "low", "requested_ui_equivalent": "Light",
               "elapsed_seconds": time.monotonic() - start, "exit_code": process.returncode,
               "credit_charge": "Not exposed as an authoritative charge by this runner"}
    for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("type") == "turn.completed":
            receipt["usage"] = event.get("usage")
    if process.returncode == 0 and (folder / "raw-story.txt").exists():
        prepare_file(folder / "raw-story.txt", folder / "fixed-story.txt")
        receipt["words_including_title"] = len((folder / "raw-story.txt").read_text(encoding="utf-8").split())
    (folder / "generation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
