"""Make a quiet periodic camera/light loop from a still; CPU encoding only."""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    if args.seconds < 2:
        parser.error("Loop must be at least two seconds")
    fps = 24
    frames = args.seconds * fps
    cycle_frames = frames - 1
    cycle_seconds = cycle_frames / fps
    # Periodic curves return continuously across the loop boundary. No one-way
    # zoom, cuts, fades to black or random flicker that would reveal a reset.
    filters = (
        "scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
        f"zoompan=z='1.02+0.004*(1-cos(2*PI*on/{cycle_frames}))':"
        f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s=1920x1080:fps={fps},"
        f"eq=brightness='0.002*sin(2*PI*t/{cycle_seconds})+0.001*sin(4*PI*t/{cycle_seconds})':eval=frame,"
        "format=yuv420p"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "warning",
                    "-n", "-i", str(args.image), "-vf", filters,
                    "-frames:v", str(frames), "-an", "-c:v", "libx264",
                    "-preset", "fast", "-crf", "18", "-threads", "2",
                    "-filter_threads", "2", "-movflags", "+faststart", str(args.output)], check=True)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
