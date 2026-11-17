"""Download one local Ollama model; no inference or story pipeline."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--status", type=Path, required=True)
    args = parser.parse_args()

    def save(**fields):
        args.status.write_text(json.dumps({"model": args.model,
            "updated_at": datetime.now(timezone.utc).isoformat(), **fields}, indent=2), encoding="utf-8")

    save(state="downloading")
    last = None
    try:
        with client.request("/api/pull", {"model": args.model, "stream": True}, timeout=900) as response:
            for line in response:
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError(event["error"])
                total, completed = event.get("total", 0), event.get("completed", 0)
                save(state="downloading", progress=event)
                marker = (event.get("status"), event.get("digest"), int(completed * 100 / total) if total else None)
                if marker != last:
                    print(json.dumps(event), flush=True)
                    last = marker
        models = client.get("/api/tags")["models"]
        installed = next((m for m in models if m["name"] == args.model), None)
        if not installed:
            raise RuntimeError("Pull ended but model was not found in local registry")
        save(state="complete", installed=installed)
        print("Download complete; no model loaded or story generated.", flush=True)
    except Exception as error:
        save(state="failed", error=str(error))
        raise


if __name__ == "__main__":
    main()
