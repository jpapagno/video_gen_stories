# Sleep story prototype

Current state: local Kokoro prototype. No ElevenLabs audio has been requested. Final episodes must be at least three hours; this short audition is exempt.

## Local Kokoro narration

```powershell
.venv\Scripts\python -m pip install -r requirements-kokoro.txt
New-Item -ItemType Directory -Force media/kokoro
curl.exe -L --fail --output media/kokoro/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl.exe -L --fail --output media/kokoro/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
.venv\Scripts\python scripts/kokoro_story.py --voice bm_george --speed 0.85
```

After installation and the one-time model downloads, speech runs locally with no voice API key or credit usage. Model assets live in ignored `media/kokoro`. Text remains unchanged. The renderer adds 1.2-second paragraph pauses and 2-second chapter pauses, caches speech by content and model hashes, and exports WAV, MP3, measured scene boundaries, and paragraph timing in `outputs/sleep-story/kokoro`. Kokoro does not provide character alignment here. The original ElevenLabs adapter remains available but is not invoked.

Image prompt: `image-prompt.md`. The one concept image represents the map room; it is not a set of chapter-specific images. No ambience or music has been mixed into the narration.

Optional still-image video preview (uses the project's existing imageio-ffmpeg dependency):

```powershell
.venv\Scripts\python scripts/render_sleep_preview.py
```

Creates `outputs/sleep-story/kokoro/prototype.mp4` at 1280x720 with AAC narration. This audition holds the one generated concept image throughout; it does not implement the later chapter dissolves. The encoder also decodes the output to verify that it is readable.

Upstream runtime/model setup: https://github.com/thewh1teagle/kokoro-onnx

Read `groundwork.md` for the separate story, narration, scene, and long-form foundations. Read `prototype-script.md` for the complete short narration. `prototype.json` is the editable source of truth; headings and scene briefs are not spoken.

## Prepare locally (zero API requests)

```powershell
.venv\Scripts\python scripts/sleep_story.py prepare
.venv\Scripts\python -m unittest discover -s scripts -p test_sleep_story.py
```

## Generate only after the transcript is approved

Create `.env` from `.env.example` and enter your own ElevenLabs API key there. The file is ignored by Git. Never put the key in frontend code. The default voice ID is the stock George voice shown in ElevenLabs documentation; availability must be checked against your account when generating.

```powershell
.venv\Scripts\python scripts/sleep_story.py generate --approved-script --max-characters 10000
```

This command consumes account credits. There is deliberately no synthesis on prepare, application startup, build, or test. The local character ceiling is not a dollar or credit estimate, because account/model pricing varies. The code does not upgrade plans or enable billing.

The adapter uses the official with-timestamps endpoint and 24 kHz signed 16-bit mono PCM, wrapped in WAV without a resampling dependency. Successful responses are cached by voice, text, neighboring text, model, settings, and format. Run sequentially in one process. Do not run simultaneous generation jobs into the same output directory. There is no automatic retry after a failed or timed-out request, because a provider may have billed a request before the connection failed.

Outputs: `outputs/sleep-story/narration.wav`, one WAV per chapter, chunk-level character alignments, and `timeline.json` with actual frame-measured scene boundaries. Alignment timestamps are relative to each cached chunk. Scene transition durations are editorial instructions; the audio remains continuous. Image generation, dissolves, ambience mixing, loudness mastering, and video encoding are not implemented in this narration prototype.

For full episodes, write and validate the complete script, set `kind` to `episode`, and choose an explicit larger character ceiling. The audio is retained if the runtime check fails so the script can be expanded; a failed episode is not silently padded or repeated.

Reference: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
