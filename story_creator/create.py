"""One prompt, one local generation, unedited text and a request receipt."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import HOME, client
from .prepare import prepare_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--gpu-layers", type=int, default=0)
    args = parser.parse_args()
    prompt = args.prompt.read_text(encoding="utf-8").strip()
    folder = HOME / "stories" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True, exist_ok=False)
    payload = {"model": args.model, "prompt": prompt, "stream": True,
               "think": False, "keep_alive": 0,
               "options": {"num_ctx": 8192, "num_predict": 7600, "num_thread": 4,
                           "num_gpu": args.gpu_layers, "temperature": 0.8, "top_p": 0.95,
                           "top_k": 20, "seed": 42, "repeat_penalty": 1.0,
                           "presence_penalty": 0.0, "frequency_penalty": 0.0}}
    receipt = {"request": payload, "runtime": client.get("/api/version"),
               "installed_models": client.get("/api/tags"), "status": "running"}
    (folder / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    metadata = folder / "generation.json"
    metadata.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(str(folder), flush=True)
    try:
        final = None
        with (folder / "raw-story.txt").open("w", encoding="utf-8") as sink:
            with client.request("/api/generate", payload, timeout=900) as response:
                for line in response:
                    event = json.loads(line)
                    if event.get("error"):
                        raise RuntimeError(event["error"])
                    sink.write(event.get("response", ""))
                    sink.flush()
                    if event.get("done"):
                        final = event
        if final is None:
            raise RuntimeError("Disconnected before completion; partial prose retained")
        for field in ("response", "thinking", "context"):
            final.pop(field, None)
        receipt.update(generation_status="complete", generation=final)
        text = (folder / "raw-story.txt").read_text(encoding="utf-8")
        words = len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", text))
        receipt.update(status="preparing", generation=final, words_including_title=words,
                       estimated_minutes_at_136_wpm=round(words / 136, 2),
                       truncated=final.get("done_reason") == "length")
        prepare_file(folder / "raw-story.txt", folder / "fixed-story.txt")
        receipt.update(status="complete", preparation_status="complete",
                       raw_story="raw-story.txt", fixed_story="fixed-story.txt")
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        metadata.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
