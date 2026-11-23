# Video pipeline

Run commands from the repository root with the CPU environment in [installation](installation.md). Generation uses the signed-in `codex exec` CLI for writing and the separate Qwen environment for the fixed voice. The existing animation and assembly modules handle video rendering.

## Onboard a category

Supply a category config, a short test brief, and a new version. Start with [the Wizard config](../categories/wizard/v1/category.json). Paths are relative to the supplied config. Supply a story-prompt text file, a scene still, an animation preset, a voice profile, intro direction, and packaging direction. Set `words_per_minute` to the measured narration rate when you have a representative recording. Animation settings follow [the animation guide](../animation/README.md). The pipeline supplies the preset's image and output paths.

For voice, use an existing named profile or supply a profile JSON with `engine` set to `voice_clone`, a `reference_audio` path relative to the profile, the exact `reference_text`, a `reference_sha256` from `Get-FileHash`, and the local Qwen Base `model` path relative to the repo. Use an authorized reference. The same reference drives the sample intro and narration.

```powershell
.venv\Scripts\python video_pipeline.py onboard wizard --version v2 --config categories/wizard/v1/category.json --brief "A lantern in a quiet observatory" --background
```

Record the run ID. Check status until it reaches `review` or `failed`. At review, report the asset folder to the requester. Ask them to read the story and copy, listen to both WAVs, watch the loop across its seam, and inspect the thumbnail. On explicit approval, save the version:

```powershell
.venv\Scripts\python video_pipeline.py approve RUN_ID
```

Approval stores the category in `categories/CATEGORY/VERSION` with checksums and the audition's run ID. To revise the category, edit the draft inputs and start another onboarding run. Wizard v1 is seeded from the existing Wizard V2 fixed voice, bedtime prompt and Hogwarts corridor artwork.

## Produce and combine an episode

Take the category and one episode brief. Use the requested runtime as an estimate for the writer. Pass `--version` when the request specifies a version. The CLI defaults to `v1` and 20 minutes.

```powershell
.venv\Scripts\python video_pipeline.py produce wizard --brief "A forbidden observatory opens after the rain" --minutes 20 --background
.venv\Scripts\python video_pipeline.py status RUN_ID
```

Track the run in the originating chat. The Python worker snapshots the approved category, starts animation and GPT writing in parallel, then narrates the story and intro with the pinned clone and prepares packaging. The thumbnail composites a story-specific hook over the category's approved artwork. The animation uses that same approved still and the saved motion settings.

At `review`, report the run ID, folder, measured narration length, and the story, intro, loop, narration, thumbnail, title, and description. The terminal `review` state is the approval checkpoint. Start assembly when the user explicitly asks to combine the reviewed run.

```powershell
.venv\Scripts\python video_pipeline.py combine RUN_ID
```

Assembly checks that the reviewed assets match their saved hashes, loops the scene through the intro and narration, and writes `final.mp4` and `final-description.txt` beside the reviewed inputs. Report the final video after status reaches `complete`.

## Recover a failed run

Read `status.json` and the logs in the run folder. Fix the reported cause and run `video_pipeline.py resume RUN_ID` with the same CPU Python. Completed story sections and media are reused. The `.running` file contains the worker PID. If the process was forcibly killed, verify that PID has exited before removing its stale marker.

`VIDEO_CODEX` overrides the Codex CLI executable. `VIDEO_VOICE_PYTHON` overrides the Qwen Python executable. `VIDEO_THUMBNAIL_FONT` optionally selects the thumbnail font file.
