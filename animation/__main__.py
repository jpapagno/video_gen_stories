"""python -m animation animation/scenes/lemon-balm.json"""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from .layers import SceneLayers

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Render a layered, seamless ambient scene on CPU")
    parser.add_argument("scene", type=Path)
    args = parser.parse_args()
    config = json.loads(args.scene.read_text(encoding="utf-8"))
    w, h, fps = config["width"], config["height"], config["fps"]
    if w % 2 or h % 2 or min(w, h, fps, config["seconds"]) <= 0:
        parser.error("Positive dimensions, fps and duration required; dimensions must be even")
    image, output = ROOT / config["image"], ROOT / config["output"]
    if output.exists():
        raise FileExistsError(f"Preserving {output}; change scene output to render another version")
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    decoded = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(image),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], check=True, capture_output=True)
    base = np.frombuffer(decoded.stdout, np.uint8).reshape(h, w, 3)
    layers = SceneLayers(base, config)
    frame_count = round(fps * config["seconds"])
    temporary = output.with_suffix(".partial.mp4")
    start = time.monotonic()
    first = layers.frame(0)
    assert np.array_equal(first, layers.frame(1)), "Layer loop endpoints differ"
    with output.with_suffix(".render.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "warning", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-threads", "2",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary)], stdin=subprocess.PIPE, stderr=log)
        try:
            for number in range(frame_count):
                process.stdin.write(layers.frame(number / frame_count).tobytes())
                if number % fps == 0:
                    print(f"Rendered {number // fps}/{config['seconds']} seconds", flush=True)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f"Encoding failed; see {output.with_suffix('.render.log')}")
        except BaseException:
            if process.poll() is None:
                process.kill()
                process.wait()
            raise
    temporary.replace(output)
    effects = ["local lantern flame and glow"]
    if config["rain_drops"] and config["rain_strength"]:
        effects.append("glass-masked moving rain")
    if config["fern_sway_pixels"]:
        effects.append("foreground fern sway")
    effects.extend(config.get("landscape_motion", {}))
    report = {"scene": config, "source_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
              "frames": frame_count, "elapsed_seconds": round(time.monotonic() - start, 2),
              "loop_endpoint_pixels_equal": True, "camera": "locked", "audio": False,
              "effects": effects,
              "renderer": "CPU numpy/scipy compositing; ffmpeg libx264"}
    output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output.resolve(), flush=True)


if __name__ == "__main__":
    main()
