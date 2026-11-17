# Local transcript workshop

For the current GPT prompt workflow, start with [story_creator](../story_creator/README.md). This directory preserves earlier local-model experiments.

The current experiment is deliberately simple: one prompt, one complete local story, then human review. The earlier scene pipeline and measured-format experiments below are preserved for reference; they are not required for this route.

```powershell
# CUDA backend is installed locally. Vulkan device detection stalled on this laptop.
.\transcripts\start-server.ps1 -Gpu
.venv\Scripts\python -m transcripts.simple_story transcripts/prompts/wizard-bedtime-simple.txt --gpu-layers 24
```

Change the prompt file to try another story type. The runner saves the exact prompt, request settings, model digest, raw streamed story and completion timing in a new `drafts/simple-*` folder. It does not rewrite or automatically extend the output. The first Qwen3.5 9B trial produced 3,307 words including the title against a requested 4,080, ending naturally: about 24.3 estimated narration minutes. CUDA offloaded 24/33 layers to a 6 GB RTX 2060 Max-Q; total request time was 9.1 minutes, of which 6.5 minutes was output generation. These are observed trial results, not guaranteed future speed or duration.

This module drafts the original Hogwarts sleep story scene by scene. Qwen3.5 4B writes locally through a project-owned Ollama server. Writing and voice synthesis are separate stages. Nothing is automatically accepted or sent to a hosted writing API.

## Editorial process

1. `story-bible.md` fixes the voice, characters, magic, object continuity and ending rules.
2. `outline.json` plans 12 chapters and 36 scenes, approximately 27,000 words. At the provisional voice pace of 136 words/minute this is roughly 198.5 minutes; actual audio duration is the final check.
3. `prompts/scene-a.md` is a lean brief. `scene-b.md` adds provisional examples and more editorial direction. Both get the same scene/context and sampling settings.
4. `benchmark.json` defines arrival, a quiet task, a transition, and the ending. These later-scene contexts are hypothetical benchmark fixtures, not accepted continuity.
5. Draft prose, exact prompts, options, model digest, runtime version, output timing and automated checks are saved together in `drafts/`.
6. A separate local editor uses six 0–4 rubric scores and cites evidence. Its review is an estimate, and evidence is checked against the actual draft. No score approves the story automatically.
7. Blind comparison files hide the prompt labels in the reading copy. Human preference selects a prompt; then test it on the remaining benchmark scenes before freezing it for the whole episode.
8. Only reviewed prose belongs in `chapters/`. Update the continuity facts and previous ending explicitly after acceptance. Production generation blocks scenes whose predecessors have not been accepted.

## Local setup

```powershell
# Official portable Ollama; CPU-only files are extracted to ignored runtime/.
uv run --no-project --python 3.12 --with remotezip python -m transcripts.runtime
.\transcripts\start-server.ps1
.venv\Scripts\python -m transcripts pull
```

The runtime installer uses the pinned official Ollama v0.40.16 Windows release, selective ZIP extraction, ZIP CRC checks, and a local per-file hash manifest. The executable's Windows signature was checked during setup. The large model resides in ignored `media/ollama-models`. Downloading runtime/model files requires a connection; generation runs on the local server at `127.0.0.1:11435`. Cloud features are disabled for this server, and the Python adapter rejects non-local endpoints and cloud-model suffixes. No cloud fallback is implemented.

Initial inference uses four CPU threads and an 8K context to avoid the laptop GPU throttling encountered during voice work. CPU performance is measured on the actual draft; hardware and generation options affect speed and reproducibility.

## Commands

```powershell
# First controlled A/B comparison. Generates two scenes and two local reviews.
.venv\Scripts\python -m transcripts benchmark --cases arrival --review

# Remaining benchmark cases; run after assessing the first pair.
.venv\Scripts\python -m transcripts benchmark --cases quiet-task transition ending --review

# Focused arrival experiment, added after the first A/B failure.
.venv\Scripts\python -m transcripts sample

# An explicit production scene, once predecessors/continuity permit it.
.venv\Scripts\python -m transcripts draft ch01-s01 --prompt b

# Review or create a separate revised version of a saved draft.
.venv\Scripts\python -m transcripts review transcripts/drafts/RUN/story.txt
.venv\Scripts\python -m transcripts revise transcripts/drafts/RUN/story.txt

# Offline workflow checks; no generation or model load.
.venv\Scripts\python -m unittest transcripts.test_pipeline
```

Draft cache keys include prompt text, story context, model digest, runtime, settings and workflow version. Identical completed writing requests reuse the saved draft; reviews can be re-run explicitly. Streaming partial text is retained if a run fails. A token-limit ending is flagged as possible truncation. No automatic retry, silent padding, looped ending or automatic acceptance is performed. Revisions are separate files and do not alter accepted continuity. A fixed seed supports controlled comparisons but does not guarantee identical output across hardware/runtime changes.

`validation.py` checks word bounds, output wrappers, repeated sentences/phrases and overlap with accepted prose. It flags viewpoint, comfort-word frequency and unplanned canon-character references for review. It cannot prove continuity, readability, originality or literary quality. The local reviewer has the same limitations as a small LLM; trust exact evidence and human judgment over its numeric score.

The existing 632-word prototype is preserved in `stories/hogwarts-night/`. It has not been silently replaced by generated benchmark text. No full three-hour transcript is claimed yet.

Original A/B runs inherited the model's presence penalty of 1.5. After reviewing those results, the defaults were changed to explicit presence/frequency penalties of 0 and repeat penalty 1.0. The focused experiment overrides these settings explicitly. This changes both prompting and sampling, so its improvement cannot be attributed solely to shorter blocks. Each original run retains its original recipe. Focused-block runs retain each block's exact prompt, options and generation metadata.

The compact optional Vulkan runtime backend was installed as a fallback, but the initial drafting runs use CPU (`num_gpu: 0`). It is not enabled by `start-server.ps1`.

To stop only this project's managed server, run `./transcripts/stop-server.ps1`; it verifies the recorded PID's executable and serve command before stopping it. The server can be restarted with `start-server.ps1`.
