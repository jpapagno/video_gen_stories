"""Check a background voice render; optional hourly local status logging."""
import argparse
import json
import re
import subprocess
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(output, active):
    stem = output.with_suffix("")
    stdout = Path(str(stem) + ".stdout.log")
    stderr = Path(str(stem) + ".stderr.log")
    log = stdout.read_text(encoding="utf-8", errors="replace") if stdout.exists() else ""
    errors = stderr.read_text(encoding="utf-8", errors="replace") if stderr.exists() else ""
    matches = re.findall(r"Rendering (\d+)/(\d+)", log)
    current, total = map(int, matches[-1]) if matches else (0, 0)
    caches = sorted(output.parent.glob(output.stem + "-chunks-*"), key=lambda p: p.stat().st_mtime)
    cache = caches[-1] if caches else None
    files = sorted(cache.glob("[0-9][0-9][0-9][0-9].wav")) if cache else []
    if cache and (cache / "recipe.json").exists():
        total = len(json.loads((cache / "recipe.json").read_text(encoding="utf-8"))["chunks"])
    duration = None
    complete = False
    if output.exists():
        try:
            with wave.open(str(output), "rb") as audio:
                duration = audio.getnframes() / audio.getframerate()
                complete = duration > 0
        except (wave.Error, EOFError):
            pass
    state = "complete" if complete else "running" if active else "stopped_incomplete"
    if not complete and "Traceback (most recent call last)" in errors:
        state = "failed"
    now = time.time()
    started = stdout.stat().st_ctime if stdout.exists() else None
    remaining = None
    # Use intervals between finished chunks, excluding initial model loading.
    if len(files) >= 2 and total > len(files):
        interval = (files[-1].stat().st_mtime - files[0].stat().st_mtime) / (len(files) - 1)
        if interval > 0:
            remaining = max(0, interval * (total - len(files)) - (now - files[-1].stat().st_mtime)) / 60
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "state": state,
            "output": str(output), "completed_chunks": len(files), "total_chunks": total,
            "current_chunk": current, "percent_chunks_complete": round(100 * len(files) / total, 1) if total else None,
            "elapsed_minutes": round((now - started) / 60, 1) if started else None,
            "estimated_remaining_minutes": round(remaining, 1) if remaining is not None and state == "running" else None,
            "minutes_since_last_chunk": round((now - files[-1].stat().st_mtime) / 60, 1) if files else None,
            "audio_minutes": round(duration / 60, 2) if duration else None,
            "error_log_tail": errors.splitlines()[-8:] if state in ("failed", "stopped_incomplete") else []}


def process_active(output):
    pid_file = output.with_suffix(".pid")
    if not pid_file.exists():
        return False
    pid = int(pid_file.read_text().strip())
    name = output.name.replace("'", "''")
    command = (f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
               f"if ($p.Name -eq 'python.exe' -and $p.CommandLine.Contains('{name}')) {{ 'active' }}")
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Unable to query render process: " + result.stderr)
    return result.stdout.strip() == "active"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/voice/last-pot-of-lemon-balm-wizard.wav")
    parser.add_argument("--watch", action="store_true", help="Write local status once an hour until complete or stopped")
    parser.add_argument("--interval-minutes", type=float, default=60)
    args = parser.parse_args()
    if args.interval_minutes <= 0:
        parser.error("Interval must be positive")
    output = args.out.resolve()
    while True:
        status = inspect(output, process_active(output))
        print(json.dumps(status, indent=2), flush=True)
        if not args.watch:
            break
        history = output.with_suffix(".status.jsonl")
        with history.open("a", encoding="utf-8") as sink:
            sink.write(json.dumps(status) + "\n")
        output.with_suffix(".status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        if status["state"] != "running":
            break
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()
