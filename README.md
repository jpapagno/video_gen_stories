# Sleepy Storykeeper

Turn a bedtime-story brief into a narrated ambient video. [`video_pipeline.py`](video_pipeline.py) is the entry point for onboarding a category and producing episodes from it.

![Sleepy Storykeeper banner](sleepy-storykeeper-banner.png)

## Setup

Follow the [installation guide](docs/installation.md). Run the commands below in PowerShell from the repository root. Generation uses the signed-in Codex CLI for GPT writing and the separate Qwen environment with an NVIDIA CUDA GPU for narration.

## 1. Onboard a category

A category bundles the story prompt, fixed voice reference, scene artwork, animation settings, and directions for the intro and YouTube packaging. Start with the [Wizard category config](categories/wizard/v1/category.json) or use an existing category as a template. Wizard v1 is already available for production.

```powershell
.venv\Scripts\python video_pipeline.py onboard wizard --version v2 --config categories/wizard/v1/category.json --brief "A lantern left burning in a quiet Hogwarts observatory" --background
.venv\Scripts\python video_pipeline.py status RUN_ID
```

The first command prints a run ID and folder. Once status reaches `review`, read the audition story and copy, listen to the intro and narration, watch the loop across its seam, and inspect the thumbnail. If the audition passes, approve that run to save the category version under `categories/CATEGORY/VERSION`.

```powershell
.venv\Scripts\python video_pipeline.py approve RUN_ID
```

## 2. Produce an episode

Supply an approved category and one brief. The example uses Wizard v1 and targets about 20 minutes. Pass `--version` to select another approved version.

```powershell
.venv\Scripts\python video_pipeline.py produce wizard --brief "A forbidden observatory opens after the rain" --minutes 20 --background
.venv\Scripts\python video_pipeline.py status RUN_ID
```

Python snapshots the approved category and launches GPT writing and animation in parallel. The worker uses the fixed clone for the narration and intro, renders a loop from the category artwork, adds a story-specific hook to the thumbnail, and writes the title and description. The run reaches `review` when those assets are ready together under `outputs/pipeline/RUN_ID`. Use the measured WAV duration in the status report when reviewing timing.

After reviewing the assets, combine that same run. The pipeline checks the reviewed files against their saved hashes and writes `final.mp4` and `final-description.txt` in the run folder.

```powershell
.venv\Scripts\python video_pipeline.py combine RUN_ID
```

## Reference

- [Pipeline guide](docs/pipeline.md) covers category inputs, review, and resuming a failed run.
- [Manual walkthrough](docs/walkthrough.md) covers the individual story, voice, animation, packaging, and assembly tools.
- [Legacy music-video experiment](docs/legacy-music-video.md) covers the optional Three.js/Vite preview in `src/`.

Run the Python test suite with:

```powershell
.venv\Scripts\python -m unittest discover
```
