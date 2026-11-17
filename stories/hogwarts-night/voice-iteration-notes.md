# Reference-guided voice auditions

Reference: https://www.youtube.com/watch?v=DqE40ZHyF7E — The Sleepy Shack, A Day at Hogwarts: Gryffindor Students' Adventures. Local analysis uses 02:00–03:00. No reference audio or transcript is included in the generated narration or shipped artifacts. Local reference media remains in ignored `media/`.

These are independently designed Qwen voices and conservative audio processing, not a clone of the channel's speaker. Acoustic measurements cannot establish accent, timbre or perceptual identity similarity. The reference includes background audio, and its estimated pace comes from automatic captions.

| Sample | Median voiced pitch | Pitch p10–p90 | Upper-band energy ratio | RMS dBFS |
| --- | --- | --- | --- | --- |
| Reference | 106.3 Hz | 95.8–122.2 Hz | .01177 | -24.47 |
| Original Qwen, untreated | 113.9 Hz | 95.8–131.6 Hz | .01510 | -22.25 |
| V1, original with tuning | 107.5 Hz | 95.8–133.1 Hz | .01011 | -24.48 |
| V2, lower/rounded with tuning | 106.9 Hz | 93.6–125.6 Hz | .01092 | -24.48 |
| V3, soft/airy with tuning | 111.3 Hz | 91.7–142.3 Hz | .01630 | -24.48 |

V2 is the recommended audition based on measured pitch, pitch range and spectral balance. This is not a claim that it perceptually matches the reference. Listen before locking the narrator. All three tuned clips are about 18.95 seconds for the same 43 words, targeting approximately 136 words/minute. No pitch shifting was applied: atempo preserves pitch; small differences in measured F0 after processing can come from pitch-estimator confidence and changed frames.

Files: `outputs/sleep-story/qwen/reference-iterations`. Prompts and seeds: `qwen-reference-variants.json`. Raw files are preserved alongside tuned versions and JSON settings. The existing original Qwen audition is preserved. Tuned versions receive a -2 dB treble bell around 3.5 kHz, a 9.5 kHz lowpass, pitch-preserving pacing adjustment and level matching.

## Reproduce

```powershell
.venv-qwen\Scripts\python scripts/qwen_voice_demo.py --variants stories/hogwarts-night/qwen-reference-variants.json --out outputs/sleep-story/qwen/reference-iterations --decoder-cpu
.venv\Scripts\python scripts/tune_sleep_audition.py outputs/sleep-story/qwen/reference-iterations/v2-low-rounded.wav outputs/sleep-story/qwen/reference-iterations/v2-low-rounded-tuned.wav --settings outputs/sleep-story/qwen/reference-iterations/v2-low-rounded.json
```

The renderer preserves existing named WAVs. Use a different output directory to regenerate. All inference is local, with no ElevenLabs or hosted speech requests.

## Hardware finding

The initial attempt with longer prompts and the decoder on GPU was aborted after very slow generation. GPU memory was nearly full and clocks were heavily reduced. Moving the audio decoder to CPU float32 freed about 700 MB GPU memory. Qwen's tokenizer wrapper device must also be set to CPU so audio codes follow the decoder. Shorter prompts and a 400-token limit bound these auditions. A 40-second pause/resume of the rendering process restored normal GPU memory clocks; no driver or system power settings were changed. Both final raw clips ended well below the token-length cap.

For long-form consistency, this audition can later serve as a designed reference for Qwen's Base model. Re-running VoiceDesign independently for every paragraph is not a guarantee of stable speaker identity.
