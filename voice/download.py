"""Resumable, hash-verified download of the local voice model."""
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "media/qwen/VoiceDesign"
REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"


def fetch(path):
    target = ROOT / path
    url = f"https://huggingface.co/{REPO}/resolve/main/{path}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not path.endswith(".safetensors"):
        if not target.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                target.write_bytes(response.read())
        return
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=0-0"}), timeout=60) as response:
        total = int(response.headers["Content-Range"].split("/")[-1])
    if target.exists() and target.stat().st_size == total:
        return
    folder = target.parent / (target.name + ".parts")
    folder.mkdir(exist_ok=True)
    size = 8 * 1024 * 1024

    def part(start):
        end = min(start + size, total) - 1
        output = folder / str(start)
        if output.exists() and output.stat().st_size == end - start + 1:
            return
        for attempt in range(4):
            try:
                request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(request, timeout=90) as response:
                    if response.headers.get("Content-Range") != f"bytes {start}-{end}/{total}":
                        raise ValueError("Unexpected HTTP range response")
                    data = response.read()
                if len(data) != end - start + 1:
                    raise ValueError("Incomplete model chunk")
                output.write_bytes(data)
                return
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1 + attempt)

    starts = list(range(0, total, size))
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
        for count, _ in enumerate(pool.map(part, starts), 1):
            if count % 25 == 0 or count == len(starts):
                print(f"{path}: {count}/{len(starts)} chunks", flush=True)
    temporary = target.with_suffix(".assembling")
    with temporary.open("wb") as out:
        for start in starts:
            out.write((folder / str(start)).read_bytes())
    temporary.replace(target)
    print(f"Saved {path} ({total} bytes)", flush=True)


def install(kind="design"):
    global ROOT, REPO
    if kind == "base":
        ROOT = Path(__file__).resolve().parents[1] / "media/qwen/Base"
        REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    elif kind != "design":
        raise ValueError("Unknown model kind")
    with urllib.request.urlopen(f"https://huggingface.co/api/models/{REPO}?blobs=true", timeout=60) as response:
        metadata = json.load(response)
    for entry in metadata["siblings"]:
        path = entry["rfilename"]
        if path.endswith(".md") or path.startswith("."):
            continue
        fetch(path)
        if "lfs" in entry:
            hasher = hashlib.sha256()
            with (ROOT / path).open("rb") as downloaded:
                while block := downloaded.read(8 * 1024 * 1024):
                    hasher.update(block)
            digest = hasher.hexdigest()
            if digest != entry["lfs"]["sha256"]:
                raise ValueError(f"SHA256 check failed: {path}")
            print(f"SHA256 verified: {path}", flush=True)
    (ROOT / "download-manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    install()
