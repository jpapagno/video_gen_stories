# Something About Us vs our blues proof

Reference: official Daft Punk Something About Us video, https://www.youtube.com/watch?v=sOS9aOIXPEk . Selected 01:25–01:40 after surveying the video. This is one deliberately selected emotional/character-focused excerpt, not a representative sample of the complete film. Proof: entire 15-second v1.

Both passed through the same audio/visual analyzer. Reference cut candidates were visually reviewed: seven automatic candidates became five verified shot changes. 2.96 and 11.4 seconds are character actions, not edits. The continuous reframing around 3–4 seconds is not a cut. Excerpt edges truncate first/last shots.

| Metric | Daft Punk excerpt | Blues proof |
|---|---:|---:|
| Cuts / shots | 5 / 6 | 1 / 2 |
| Median visible shot span | 2.58 s | 7.50 s |
| Mean HSV brightness, 0–1 | 0.318 | 0.322 |
| Mean HSV saturation, 0–1 | 0.555 | 0.388 |
| Median global displacement proxy | 0.094 px/sample | 0.023 px/sample |
| Median residual motion p90 | 0.709 px/sample | 0.073 px/sample |
| Low residual motion samples | 26.9% | 90.4% |

Global/residual motion uses 320×180 images sampled about 12 times/sec, partial affine RANSAC registration, and optical flow. p90 describes the upper tenth of sampled motion residuals. Low-residual threshold is 0.15 px/sample, chosen for this experiment. These are heuristic image measurements, not calibrated character/camera separation. Local effects, depth, compression, missed cuts and registration failures can affect them. All comparisons exclude reviewed cut-crossing pairs in this registration analysis. Existing quarter-second legacy optical flow is retained separately and can include cuts.

Brightness is HSV value, not perceptual luminance. Similar averages do not establish equivalent contrast, palette, lighting or composition. Saturation should not simply be increased to hit the number.

## What the reference is doing

Six compositions: two detail shots, three face-focused shots (one reframes to include a second character), and one wide ensemble. Hands rise and lower, a head turns, gaze changes, a head dips and a fist moves. The shot can hold while a character performs an action. Our proof has one alternate facial drawing blended in and out; it has no hand gesture, torso turn or independent head animation.

## Targets for the next proof (creative targets, not statistical rules)

- Six planned compositions in 15 seconds with roughly 1–4.6 second visible spans. Preserve pauses instead of uniform cuts.
- Add at least three distinct character actions: a hand gesture, a head/gaze turn, and an expression change. Use separate drawings or a rig with held keys and transitions.
- Include an insert/detail shot and a wide scene, alongside close-ups. Our current assets do not cover this acting range; generate/design pose sheets before rendering.
- Evaluate residual motion inside reviewed character regions and compare that with background regions. The current global registration is only a first proxy.
- Keep the established artwork/palette; matching movement and staging matters more than tuning a global color number.
- Recheck the result against this excerpt and a second quieter excerpt before treating any metric as a style rule.

## Limits

We have not measured unique drawing frequency, exact hold duration, precise character coverage or reviewed lyric timing. Low-residual samples are not literally held drawings. Beats detected on short excerpts can differ from full-song analysis; do not use the apparent 100% beat alignment of the proof's single cut as a quality score. No Daft Punk imagery/audio is used in the generated blues video. Analysis contact sheets are local study materials.

Data: daft-comparison.json. Visual annotation record: daft-annotations.json. Re-run the reviewed comparison with scripts/compare_style.py; automatic extraction with scripts/analyze.py.
