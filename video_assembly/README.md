# Video assembly

## Automatic chapters and description

Use `python -m voice.collection` for new multi-story audio. Assembly automatically finds the narration's `.chapters.json`, verifies its audio hash/frame count, adds the actual intro offset and exports `.chapters.json` plus `.chapters.txt` beside the video. Internal timings use sample counts; YouTube text timestamps round down to whole seconds. No word-count timing estimate is used.

Set `description` in the assembly preset to the upload description path, for example `outputs/packaging/my-episode/description.txt`. If omitted, assembly creates/updates `description.txt` beside the video. The generated Chapters block is replaced on reruns while the rest of the description is retained. An optional `audio_chapters` path overrides sidecar discovery. Packaging prompts also receive verified chapter data from the assembly manifest.

Legacy flattened narration without a sidecar continues to assemble, but no exact chapter timings are invented. Any retrospectively estimated timestamps must be explicitly labelled approximate. Tests cover story ordering, repeated audio, gaps, intro offsets, description updates and mismatched audio rejection.

## Standard settling-in intro

Assembly prepends the recording selected in `defaults.json`, with one second of visual lead-in and a 2.8-second pause before the story. The scene stays continuous. Tiny fades at the intro edges prevent clicks; story speech does not overlap the intro. The saved intro is reused for later assemblies.

```powershell
# Generate the standard intro once with the fixed Wizard V2 speaker.
.\.venv-qwen\Scripts\python.exe -m voice narrate video_assembly/intros/hogwarts.txt --profile wizard --out outputs/voice/intros/hogwarts-wizard.wav

# Rebuild the collection and update upload metadata.
.\.venv\Scripts\python.exe -m video_assembly.add_intro --voice-python .venv-qwen/Scripts/python.exe
```

Presets can override `intro`, `intro_lead_seconds` and `intro_pause_seconds`; set `intro` to null to omit it. The default script mentions Hogwarts: choose another intro for a different setting. Missing intro audio raises a clear error. `--plan-only` reports timing. Assembly receipts record intro duration, story start time and intro audio hash. The collection rebuild preserves the previous video, writes `final-with-intro.mp4`, updates description runtime/replay timing, and records progress in `intro-job-status.json`.

The check `python -m unittest video_assembly.test_intro` verifies actual encoded intro/pause/body timing using the local scene loop.

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
