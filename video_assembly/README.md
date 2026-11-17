# Video assembly

Purpose: stitch finished narration and a silent looping scene into a watchable episode. Install the CPU dependencies from [installation](../docs/installation.md).

## Create an episode preset

Save `video_assembly/presets/my-episode.json`:

```json
{
  "video": "outputs/animation/lemon-balm/greenhouse-loop.mp4",
  "audio": "outputs/voice/my-episode.wav",
  "output": "outputs/videos/my-episode/final.mp4"
}
```

```powershell
.venv\Scripts\python -m video_assembly video_assembly/presets/my-episode.json --plan-only
.venv\Scripts\python -m video_assembly video_assembly/presets/my-episode.json
```

Both inputs must exist even for planning. The WAV must contain the full narration; the MP4 must be a playable loop. The supplied animation renderer produces compatible H.264 video. Outputs are the final MP4, `.assembly.log` and companion `.json` receipt. That receipt supplies measured runtime and features to packaging.

Watch the beginning, several loop joins and ending; listen for clipped words and unexpected gaps. Choose another output filename for revisions. Failure may leave a `.partial.mp4` and encoder log for diagnosis. The module does not lengthen the narration by repeating it.

Return to the [overview](../README.md) or [walkthrough](../docs/walkthrough.md).

Combine an existing silent scene loop with finished WAV narration:

```powershell
.\.venv\Scripts\python.exe -m video_assembly video_assembly/presets/lemon-balm.json --plan-only
.\.venv\Scripts\python.exe -m video_assembly video_assembly/presets/lemon-balm.json
```

The scene repeats until the narration ends. Video is copied without another render; audio is encoded to AAC. Explicit stream selection ignores any source-video audio. The final MP4 is checked for an audio stream and a duration within 0.25 seconds of narration, then a receipt records source hashes and output properties. Encoding logs and incomplete files are retained on failure. Existing final outputs are preserved.

Edit a copy of the preset for another episode. Paths are relative to the project root. Requirements: stdlib Python and imageio-ffmpeg. No model calls, GPU inference, publishing, music mixing or captions are included. Current prototype is approximately 27 minutes; making a three-hour episode requires three hours of source audio rather than silently repeating the story.
