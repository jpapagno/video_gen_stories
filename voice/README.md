# Voice

Production narration uses **Wizard V2 fixed-reference cloning** with the local Qwen3-TTS 1.7B Base model. Every chunk reuses the same speaker recording and transcript. VoiceDesign no longer runs during narration.

## Render narration

For multi-story episodes use the collection runner instead of flattening all stories into one transcript:

```powershell
.venv-qwen\Scripts\python -m voice.collection story_creator/stories/wizard-three-hours-20261117/collection.json --out outputs/voice/new-collection.wav --repeat-first
```

Each story is rendered independently with the same fixed speaker, so chunks cannot cross story boundaries. The runner reuses matching completed story renders, inserts measured gaps and writes `new-collection.chapters.json` with exact start frames and an audio hash. Repeating the opening reuses its audio rather than generating it again. This is the standard collection path for automatic chapters; the single-story `voice narrate` command remains available. Do not rerun the existing collection simply to obtain timestamps unless you intend to re-render it.

From the project root after following [installation](../docs/installation.md):

```powershell
# Explicit download on a fresh installation; already installed on this laptop.
.venv\Scripts\python -m voice download

# Inspect the active default speaker; no GPU/model load.
.venv\Scripts\python -m voice profile

# Validate input/profile, then listen to a preview before a full render.
.venv\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --out outputs/voice/my-preview.wav --plan-only
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --out outputs/voice/my-preview.wav --preview-chunks 2
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --out outputs/voice/my-episode.wav
```

`--profile wizard` is the default. The profile pins `assets/voices/wizard/reference.wav`, its exact transcript, its SHA256 and `media/qwen/Base`. The reference is the original synthetic V2 low-rounded audition, not a recording of a real narrator. No new training is performed.

Text preparation belongs to `story_creator`; pass its fixed story. Narration does not rewrite or expand text.

## Identity, settings and resuming

`speaker.py` verifies the reference before inference. It creates the speaker-conditioning prompt once, saves its tensors locally, and reuses that prompt on subsequent runs. Saved prompts are keyed by profile/reference and model fingerprints, and loaded as tensor/dictionary data with `weights_only=True`. Changed reference bytes cause a clear error, rather than silently selecting another speaker.

`narrate.py` calls only `generate_voice_clone`. Settings match the approved trial: seed 42, temperature 0.7, top-p 0.9 and non-streaming input. The decoder runs on CPU while synthesis uses CUDA. Default chunks contain at most 90 words; use `--chunk-words 40` for shorter previews or up to 180 for longer sections. Chunks are joined with 0.6-second gaps. A whole 27-minute single request is not a validated production mode.

The `fixed-speaker-v1` recipe includes the model fingerprint, reference identity, text and generation settings, so old VoiceDesign chunks cannot be reused accidentally. Completed chunks resume when the same command is rerun while the final output is absent. Existing final audio is preserved. Use a new filename for re-rendering old episodes, then update the assembly preset to that new WAV. A final JSON receipt records the exact recipe and chunk cache. Existing published/exported files are not automatically changed.

A fixed speaker reference substantially reduces identity drift; it does not guarantee identical accent strength, expression, pronunciation or pace in every passage. Listen to previews and review joins before publication.

## Another voice

Design a short audition once, select it, save the matching audio/transcript, and create a new fixed profile following `profiles/wizard.json`. Narration rejects direction-only profiles. Optional historical tools remain available:

```powershell
.venv\Scripts\python -m voice download-design
.venv-qwen\Scripts\python -m voice audition --variants voice/profiles/v6-source.json --out outputs/voice/new-audition
```

The old V6 cleanup/rebuild and analysis commands remain for reproducing historical auditions, not production narration. The Python `selected_profile()` helper still refers to that legacy cleanup recipe; the CLI `voice profile` displays the production Wizard speaker. `wizard-locked.json` and `clone_test.py` preserve the approved experiment and do not control the production default.

## Check background progress

```powershell
.venv\Scripts\python -m voice.status --out outputs/voice/my-episode.wav
.venv\Scripts\python -u -m voice.status --out outputs/voice/my-episode.wav --watch
```

A background launch should save matching `.pid`, `.stdout.log` and `.stderr.log` companion files. Watch mode logs locally each hour and stops on completion/failure; it sends no chat notification. It requires the machine to stay awake.

## Verification

```powershell
.venv\Scripts\python -m unittest voice.test_speaker voice.test_status story_creator.test_prepare
```

See the [walkthrough](../docs/walkthrough.md) for story, animation and assembly stages. The upstream design-once/clone-many workflow is documented by [Qwen](https://github.com/QwenLM/Qwen3-TTS).
