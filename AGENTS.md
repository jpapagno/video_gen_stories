# Video pipeline agent instructions

For onboarding, production, review, assembly, or recovery, use the [pipeline guide](docs/pipeline.md) and run `video_pipeline.py` from the repository root with `.venv\Scripts\python`.

1. **Onboard.** Run `onboard` with the draft config, category, version, and audition brief. Start with `--background`. After the user explicitly approves that audition, run `approve` with its run ID and report the saved version.
2. **Produce.** Run `produce` with the approved category and the user's brief. Start with `--background` and let Python dispatch the generators. Pass the version and target minutes when specified.
3. **Track.** Capture the run ID and folder from the launch. Monitor `status` through `review` or `failed` in the originating chat. At `review`, report the folder, asset names, and measured audio duration. Leave the run at this checkpoint for the user's audit. On failure, inspect the run logs, fix recoverable causes, and use `resume` with the same run ID. Report the specific blocker if recovery stalls.
4. **Combine.** When the user explicitly requests assembly, use the reviewed production run ID from this chat. If several runs fit the request, ask which to combine. Run `combine` with that ID and report the final video and description after confirming status is `complete`.
