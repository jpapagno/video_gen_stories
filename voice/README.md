# Voice

Purpose: infer narration locally from prepared text using Qwen3-TTS VoiceDesign. A profile is a natural-language direction and seed, not separately trained voice weights.

## Fresh installation and first narration

Follow [installation](../docs/installation.md) for CPU and CUDA Python environments, then download the official [VoiceDesign model](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign):

```powershell
.venv\Scripts\python -m voice download
.venv\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-preview.wav --plan-only
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-preview.wav --preview-chunks 2
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-episode.wav
```

Weights are stored at `media/qwen/VoiceDesign` and excluded from GitHub. Downloading is explicit; inference loads local files only. Full narration requires CUDA. The decoder runs on CPU to reduce GPU memory use. Listen to the preview before the full render.

Chunks contain roughly 90 words and are joined with 0.6-second gaps. If interrupted before the final WAV exists, rerun the same command with unchanged text, profile and output to reuse cached chunks. Use a new output filename after revisions. Independent chunks can vary in voice identity and pacing.

## Tune the narrator

The default narration profile is `wizard`, pointing to `v2-low-rounded` in `profiles/v6-source.json`. Historical V2/V6 names do not represent different downloaded models. `voice profile` displays the separately selected V6-clean audition recipe, not the default narration profile.

Create `voice/profiles/my-narrator.json` with exactly one variant:

```json
[
  {
    "name": "my-narrator",
    "seed": 42,
    "instruction": "A warm adult narrator with a gentle British English accent. Soft rounded tone, unhurried phrasing, clear consonants, natural relaxed speech and restrained expression."
  }
]
```

Use lowercase letters, digits and hyphens in names. Describe timbre, accent, pace, expressiveness and articulation. Change one characteristic at a time and keep the same seed for comparisons:

```powershell
.venv-qwen\Scripts\python -m voice audition --variants voice/profiles/my-narrator.json --out outputs/voice/auditions/my-narrator
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile my-narrator --out outputs/voice/my-narrator-preview.wav --preview-chunks 2
```

Auditions use a built-in passage; previews test your story. Try another seed for a different interpretation. Direction is approximate, not an exact speed or pitch control. Correct difficult pronunciations in the prepared text and listen again.

Temperature 0.8, top-p 0.9, chunk size and gap duration are currently set in `narrate.py`, without CLI controls. If editing those values, preserve the old version and use a new output filename. Narration does not apply the historical V6-clean processing chain. `voice rebuild` requires omitted local reference artifacts and is not a fresh-clone check.

Return to the [overview](../README.md) or [walkthrough](../docs/walkthrough.md).

## Historical tools and implementation notes

## Fixed Wizard identity experiment

`wizard-locked.json` pins the original 16.4-second V2 audition plus its exact transcript and SHA256. It is separate from the current `wizard` VoiceDesign profile; existing narration behavior is not silently changed.

```powershell
# Download the separate official 1.7B Base model, then run a small comparison.
.\.venv-qwen\Scripts\python.exe -u -m voice.clone_test --download-model

# Subsequent runs use local model files and reuse completed trial outputs.
.\.venv-qwen\Scripts\python.exe -u -m voice.clone_test
```

The test extracts a clone prompt once and reuses it across three different passages, then synthesizes the same combined text in one request. Compare `separate-chunks.wav` against `one-go.wav` under `outputs/voice/clone-test/`. Each render records its input, duration and elapsed time. This tests reference-based consistency and a short one-request render, not whether a 27-minute request is reliable. The longer story would require a much larger codec-token budget, more generation memory and a longer uninterrupted run; retries would redo all its audio. The test is resumable but voice quality still requires listening. The current background job writes `outputs/voice/clone-test-job.stdout.log` and `.stderr.log`.

The intended design-once/clone-many approach is documented by [Qwen](https://github.com/QwenLM/Qwen3-TTS). No model is trained or fine-tuned here. Fixed-reference conditioning should reduce identity drift; it does not enforce identical expression or guarantee flawless pronunciation.

## Check a background render

```powershell
# Current wizard story: no model loading or GPU work.
.\.venv\Scripts\python.exe -m voice.status

# Any render using matching .pid/.stdout.log/.stderr.log companion files.
.\.venv\Scripts\python.exe -m voice.status --out outputs/voice/NAME.wav

# Hourly local checks, stopping when complete, failed or no longer running.
.\.venv\Scripts\python.exe -u -m voice.status --watch
```

`voice/status.py` reports completed/total chunks, elapsed time, estimated remaining time, process state and errors. Completion requires a readable, nonempty final WAV; process exit alone is not success. Estimates use completed chunk intervals and can change. Watch mode writes `.status.json` (latest) and `.status.jsonl` (history) beside the output. It is a local process, not a scheduled Codex agent: it uses no model credits, sends no chat notifications, and cannot check while the computer sleeps. The current render's watcher logs are `outputs/voice/wizard-status-watcher.stdout.log` and `.stderr.log`.

Selected narrator: **V6 clean**, using local Qwen3-TTS VoiceDesign plus the saved V6 processing recipe. No specially trained V6 model weights exist. The selected audition is `outputs/sleep-story/qwen/metric-match/v6-clean.wav`.

## Entry points

From the project root:

```powershell
# Read settings; no rendering, downloads, or heavyweight imports.
.venv\Scripts\python -m voice profile

# Rebuild the exact selected clean audition; CPU only, using existing local artifacts.
.venv\Scripts\python -m voice rebuild

# Generate a raw Qwen audition with the selected underlying voice direction.
.venv-qwen\Scripts\python -m voice audition

# Download/resume official model assets and verify their hashes.
.venv\Scripts\python -m voice download

# Render a saved story locally (raw V6 direction; no audition cleanup).
.venv-qwen\Scripts\python -m voice narrate transcripts/drafts/simple-20261116T045228Z/story.txt --out outputs/voice/quiet-hours.wav

# Listen to a short test first; use a separate output filename.
.venv-qwen\Scripts\python -m voice narrate transcripts/drafts/simple-20261116T045228Z/story.txt --out outputs/voice/quiet-hours-preview.wav --preview-chunks 2
```

Text preparation now belongs to `story_creator`, immediately after story generation. Narration reads the supplied file as-is; pass `story_creator/stories/quiet-hours/fixed-story.txt` for the existing story. That folder also preserves `raw-story.txt`. Each audio chunk cache includes `spoken-text.txt`. Use a new output filename after changing text; existing outputs are preserved. See `story_creator/README.md` for creation and preparation commands.

Python API:

```python
from voice import selected_profile, rebuild_selected_voice

profile = selected_profile()
clean_wav = rebuild_selected_voice()
```

`audition` generates the raw source voice; `rebuild` reproduces the processed V6 clean sample. The latter checks its original V6 replay before rebuilding. These are explicit operations; importing the package does not download models or render audio.

## Code ownership

| File | Responsibility |
| --- | --- |
| `profiles/v6-clean.json` | Selected voice, model paths, voice direction and processing settings |
| `profiles/v6-source.json` | Exact underlying Qwen voice-design prompt and seed |
| `audition.py` | Qwen model loading, GPU generation, CPU decoder and WAV export |
| `cleanup.py` | Selected V6 clean recipe and reproducibility check |
| `processing.py` | Pitch mapping, micro-prosody, pauses, EQ, de-essing and dynamics |
| `features.py` | Speech detection, pitch, spectral, loudness and timing measurements |
| `download.py` | Resumable model download with SHA256 verification |
| `refinement.py` | Historical V6/V7 audition experiments |
| `tuning.py`, `basic_analysis.py` | Earlier audition tools retained for reproducibility |

The old commands in `scripts/` are small compatibility launchers. The implementation now lives here.

## Assets and environments

Large model weights remain at `media/qwen/VoiceDesign`, the speech detector at `media/voice-analysis/silero_vad.onnx`, and generated audio under `outputs/`. They are ignored by Git. They were not copied into the code package or downloaded again.

The main `.venv` handles CPU analysis and cleanup. `.venv-qwen` handles model inference. Root dependency files remain supported; this folder also has `requirements-analysis.txt` and `requirements-qwen.txt`. The Qwen CUDA installation command is:

```powershell
uv pip install --python .venv-qwen/Scripts/python.exe torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu130
uv pip install --python .venv-qwen/Scripts/python.exe qwen-tts==0.1.1
```

## Current scope

The selected short audition and its exact cleanup are implemented and verified. The cleanup currently depends on the saved comparison report, raw audition and local reference-analysis audio. `narrate` now supports bounded text chunks, cached chunk files for resuming, and joining them with 0.6-second gaps. It uses the saved V6 source direction, not the audition-specific cleanup. Independent VoiceDesign chunks do not guarantee a stable identity. The next step for consistent long-form voice is a reusable designed reference voice. The narrator command has passed a text-only planning check on the story (41 chunks); full synthesis and listening validation remain untested. It does not download models, rewrite prose or invoke hosted speech APIs.

Synthetic aspiration is disabled in the selected clean recipe. Historical experiments retain their old noise-layer code to reproduce the original bug and auditions.
