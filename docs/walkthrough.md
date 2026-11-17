# Make an episode from start to finish

Complete [installation](installation.md) first. Run these commands in the repository root. Use a unique episode name or new output filenames for later runs.

## 1. Write and prepare the story

Open `story_creator/prompts/wizard-bedtime.txt`, paste it into your preferred GPT interface with **GPT Sol 6.1 / Light** selected, and review the result. Save narration prose alone as UTF-8 `episodes/my-episode/raw-story.txt` (create the folder first). Remove the title if it should not be spoken.

```powershell
.venv\Scripts\python -m story_creator.prepare episodes/my-episode/raw-story.txt --out episodes/my-episode/fixed-story.txt
```

Listenability, ending completeness and names need human review. See [story creation](../story_creator/README.md) for adapting the prompt.

## 2. Preview, then render narration

```powershell
.venv\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-episode-preview.wav --plan-only
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-episode-preview.wav --preview-chunks 2
.venv-qwen\Scripts\python -m voice narrate episodes/my-episode/fixed-story.txt --profile wizard --out outputs/voice/my-episode.wav
```

Listen to the preview before the full run. See [voice tuning](../voice/README.md) to change the narrator. Failed renders can resume by rerunning the same command with unchanged text/profile/output while the final WAV is absent.

## 3. Make the visual loop

For a first test, use the included greenhouse image and preset:

```powershell
.venv\Scripts\python -m animation animation/scenes/lemon-balm.json
```

For your own artwork, follow the [scene-image prompt and preset instructions](../animation/README.md). The supplied loop output is `outputs/animation/lemon-balm/greenhouse-loop.mp4`.

## 4. Stitch voice and video

Create `video_assembly/presets/my-episode.json`:

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

Watch the beginning, several joins and the ending of the final MP4. The companion `final.json` records runtime and actual features.

## 5. Create the title, thumbnail and description

Copy `video_packaging/episodes/lemon-balm.json` to `video_packaging/episodes/my-episode.json`. Update every story fact and set `story` to `episodes/my-episode/fixed-story.txt` and `assembly_manifest` to `outputs/videos/my-episode/final.json`.

```powershell
.venv\Scripts\python -m video_packaging video_packaging/episodes/my-episode.json --out outputs/packaging/my-episode/generation-prompt.md
```

Paste the generated prompt into GPT, select a title/concept, then give the chosen image prompt to your image-generation tool. Review the thumbnail at small size and verify the description against the actual episode. See [packaging](../video_packaging/README.md). Uploading is manual.
