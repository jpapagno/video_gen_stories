"""Combine the prototype image and narration into a still-image video."""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ROOT / "outputs/sleep-story/kokoro")
    args = parser.parse_args()
    image = args.folder / "map-room.png"
    audio = args.folder / "narration.wav"
    for path in (image, audio):
        if not path.exists():
            parser.error(f"Missing {path}")
    target = args.folder / "prototype.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-v", "error", "-loop", "1", "-framerate", "1",
                    "-i", str(image), "-i", str(audio), "-vf", "scale=1280:720,setsar=1",
                    "-c:v", "libx264", "-tune", "stillimage", "-preset", "fast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", str(target)], check=True)
    subprocess.run([ffmpeg, "-v", "error", "-i", str(target), "-f", "null", "-"], check=True)
    print(target)


if __name__ == "__main__":
    main()
