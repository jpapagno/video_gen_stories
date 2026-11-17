# Story creator

## Preferred workflow: GPT prompt to transcript

This module turns a writing prompt into narration text and prepares that text for speech. Your preferred setup is **GPT Sol 6.1 / Light**, selected manually in your GPT interface. This is a model-selection preference, not an API identifier configured in this project. No GPT API calls are implemented here.

1. Copy [the saved story prompt](prompts/wizard-bedtime.txt) into GPT. Select the model and Light setting in your interface.
2. Review the result for continuity, dialogue clarity, repetition and a complete ending. Requested word count is approximate; the rendered narration determines actual runtime.
3. Save narration prose alone as UTF-8 `episodes/my-episode/raw-story.txt`. Create that folder first. Remove commentary and any title you do not want spoken.
4. Create a separate prepared copy:

```powershell
.venv\Scripts\python -m story_creator.prepare episodes/my-episode/raw-story.txt --out episodes/my-episode/fixed-story.txt
```

Review names and ambiguous numeric expressions, then pass the prepared file to [voice narration](../voice/README.md). Preparation does not fix story logic or incomplete endings. Keep the original text and prompt.

## Create your own prompt

Copy the saved prompt to a new text file. Change the setting, small cast, central quiet task, approximate length, viewpoint and peaceful ending. Keep clear speaker attribution and natural prose for listening. Try a short story first, then revise one instruction at a time based on what you hear.

```text
Write an original bedtime story for adults, approximately [WORDS] words.
Setting: [PLACE AND PERIOD]. Cast: [SMALL CAST]. Viewpoint: [VIEWPOINT].
Introduce a gentle unfinished task or question: [TASK].
Use connected events, concrete sensory details and natural dialogue with clear
speaker attribution. Keep stakes low, avoid danger and repetitive padding,
and gradually settle toward [PEACEFUL ENDING].
Return only the complete story, with no commentary or outline.
```

`prompts/` stores writing instructions; `prepare.py` and `numbers.py` prepare text; `create.py` and `client.py` implement the optional local writer below. GPT output is saved manually, so record the model/settings beside your prompt yourself. The local writer's generation receipts are not created for manual GPT sessions.

Return to the [overview](../README.md) or [complete walkthrough](../docs/walkthrough.md).

## Optional local Qwen writer

One local model request creates a story; a deterministic text-preparation step follows it. No scene pipeline, automatic rewrite, or speech generation runs here.

From the project root:

```powershell
# Reuse the installed local Ollama runtime/server.
.\transcripts\start-server.ps1 -Gpu
.\.venv\Scripts\python.exe -m story_creator story_creator/prompts/wizard-bedtime.txt --gpu-layers 24
```

Each new folder in `story_creator/stories/` contains:

- `prompt.txt`: the supplied prompt.
- `raw-story.txt`: untouched streamed model output, retained even if generation fails.
- `fixed-story.txt`: prepared text, written only after generation finishes successfully.
- `generation.json`: request, model identity, timing, completion and preparation status.

Preparation removes Markdown headings/emphasis and expands known pronunciation traps, such as `St. Jude` to `Saint Jude`, `Mr. Thorne` to `Mister Thorne`, and `Mrs Wren` (with or without a period) to `Missus Wren`. Standard standalone digits are spelled out, including integers, decimals, ordinals, percentages, simple number ranges, full-month dates and clock times. For example, `November 6` becomes `November the sixth`, `Room 42` becomes `Room forty-two`, and `3:15` becomes `quarter past three`. Ambiguous numeric formats and identifiers still need review; this is not a universal pronunciation parser. It does not rewrite dialogue, names or invented words. Speaker clarity is requested in the creation prompt. Ambiguous abbreviations remain unchanged. A token-limit stop is recorded as truncated and still produces a prepared copy for inspection; preparation does not repair incomplete prose.

The existing story is preserved in `stories/quiet-hours/`, with its original generation receipt copied as `generation-original.json`.

```powershell
# Prepare an existing raw story without model inference. Refuses to overwrite.
.\.venv\Scripts\python.exe -m story_creator.prepare INPUT.txt --out FIXED.txt

# Voice consumes the fixed story without applying further text preparation.
.\.venv-qwen\Scripts\python.exe -m voice narrate story_creator/stories/quiet-hours/fixed-story.txt --out outputs/voice/quiet-hours-fixed-preview.wav --preview-chunks 2

# Offline text checks.
.\.venv\Scripts\python.exe -m unittest story_creator.test_prepare
```

Edit the prompt file for different story types. `config.json` supplies the local server endpoint; command arguments select the model and GPU layers. Older `transcripts.simple_story` and `voice.text` commands forward to this module for compatibility. The legacy transcript experiments and voice model assets remain in their existing locations.
