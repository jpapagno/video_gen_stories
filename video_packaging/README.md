# Video packaging

## Description house style

Use the short format in `description.py` and `prompts/package.md`: opening + broad measured duration and listening experience; optional settling-intro sentence; one synopsis paragraph; subscribe to **SleepyStorykeeper**; three hashtags; then chapters. Blank lines separate the sections. There is no duplicate story list, feature list, technical/model commentary, replay explanation, separate AI disclosure or extra disclaimer paragraph. Unofficial fan-created status stays in the synopsis. Provenance stays in metadata.

For videos at least three hours, display verified whole hours rounded down (3:08 becomes “3 hours”). Shorter videos use whole minutes rounded down. Chapter timestamps and hashtags remain plain text for YouTube to link automatically. Returned opening-story chapters display “— Part 2”; internal chapter manifests retain their repeat source. Legacy chapter estimates remain explicitly labelled approximate.

## Prompt GPT for titles, thumbnail and description

1. Copy `episodes/lemon-balm.json` to `episodes/my-episode.json`. Update the story path, assembly manifest, channel, episode name, universe, main character, narration and visuals. Set music, rain audio and caption flags truthfully; animated rain does not imply rain sound.
2. Build the prompt from the project root:

```powershell
.venv\Scripts\python -m video_packaging video_packaging/episodes/my-episode.json --out outputs/packaging/my-episode/generation-prompt.md
```

3. Paste the complete generated Markdown into GPT. Start with your preferred **GPT Sol 6.1 / Light** setup if available. Model selection is manual; this command makes no GPT requests.
4. Compare the requested five titles and three thumbnail concepts. Choose a specific hook the actual episode delivers; ask for revisions while retaining factual constraints.
5. Give the selected image prompt to your image-generation tool. Save the thumbnail and chosen title/description beside the package output.
6. Inspect the thumbnail at phone size for subject clarity, contrast and readable optional text. Verify runtime and description claims against the final episode, then upload manually.

The reusable prompt lives in `prompts/package.md`; version edits to develop a new style. Research examples are dated observations, not live performance data. Without a completed assembly manifest, measured runtime is unknown; do not invent it. Conflicting feature flags raise an error so the brief can be corrected.

Thumbnail art is separate from the scene background. The module builds instructions and does not generate images, upload to YouTube or guarantee audience performance.

Return to the [overview](../README.md) or [walkthrough](../docs/walkthrough.md).

This module owns prompts, researched examples and title/description/thumbnail assets. It does not assemble media, invoke paid models automatically, upload videos or change YouTube settings.

```powershell
.\.venv\Scripts\python.exe -m video_packaging video_packaging/episodes/lemon-balm.json --out outputs/packaging/lemon-balm/generation-prompt.md
```

The command combines the reusable `prompts/package.md` template, episode facts, full story and research notes. If a completed assembly manifest exists, it includes measured runtime and checks factual sound/visual claims. The output can be given to an LLM without extra scaffolding. It asks for five titles, three thumbnail concepts, one image prompt, a description and a rationale. Existing prompt files are preserved; use a new filename to rebuild.

For another episode, copy the brief JSON, select its story and assembly manifest, and update the facts. This deliberately optimises for curiosity and relevance while requiring the actual video to fulfil its promise. No invented CTR predictions or medical sleep guarantees. Public view counts are reference observations, not evidence that packaging caused success. Actual audience testing is needed to select a winner.
