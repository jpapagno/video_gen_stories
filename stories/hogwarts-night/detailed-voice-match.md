# Detailed voice matching results

Recommended measured candidate: V6, `outputs/sleep-story/qwen/metric-match/v6-balanced-match.wav`. V7 is a more textured alternative. Each is approximately 19 seconds.

27 of 35 descriptive measurements moved closer to the reference in V6. These metrics are correlated and this count is not a perceptual similarity percentage. The reference spans 60 seconds; each audition has different words and is 19 seconds. New measurements use a consistent full-clip Praat/Silero protocol, unlike the earlier first-25-second pyin analysis.

Processing: pitch-quantile mapping with preserved micro-prosody, slower speech within phrases, shorter gaps, bounded multi-band EQ, dynamic de-essing, smooth envelope correction, peak reduction and LUFS matching. A small synthetic aspiration proxy was tested; no reference audio was mixed into generated speech.

| Measurement | Reference | Before | V6 | Closer? | Reference 20s range |
|---|---:|---:|---:|:---:|---|
| pitch_median_hz | 99.856 | 92.295 | 99.509 | yes | 98.992 to 101.291 |
| pitch_p10_hz | 91.305 | 76.882 | 88.910 | yes | 90.887 to 92.157 |
| pitch_p90_hz | 119.640 | 117.389 | 120.627 | yes | 117.811 to 121.155 |
| pitch_p25_hz | 94.822 | 81.442 | 92.740 | yes | 94.227 to 95.263 |
| pitch_p75_hz | 109.336 | 106.187 | 110.506 | yes | 107.090 to 111.636 |
| pitch_iqr_semitones | 2.466 | 4.593 | 3.034 | yes | 2.152 to 2.812 |
| pitch_range80_semitones | 4.679 | 7.327 | 5.282 | yes | 4.443 to 4.930 |
| pitch_step_p50_semitones | 0.131 | 0.149 | 0.115 | yes | 0.124 to 0.149 |
| pitch_step_p90_semitones | 0.529 | 0.491 | 0.401 | no | 0.471 to 0.601 |
| hnr_median_db | 8.857 | 12.195 | 13.496 | no | 8.572 to 9.225 |
| hnr_iqr_db | 11.129 | 7.061 | 7.712 | yes | 10.282 to 11.838 |
| centroid_median_hz | 238.787 | 233.946 | 229.383 | no | 229.024 to 249.132 |
| rolloff85_median_hz | 304.688 | 351.562 | 328.125 | yes | 281.250 to 304.688 |
| sibilance_p90_db | -2.289 | 0.175 | -1.015 | yes | -4.618 to 2.162 |
| sibilance_p50_db | -25.722 | -28.665 | -24.916 | yes | -26.822 to -25.071 |
| flatness_median | 0.111 | 0.061 | 0.256 | no | 0.109 to 0.117 |
| integrated_lufs | -24.952 | -24.707 | -24.952 | yes | -25.474 to -24.550 |
| rms_dbfs | -24.440 | -24.470 | -24.129 | no | -25.094 to -23.801 |
| sample_peak_dbfs | -8.562 | -5.184 | -8.508 | yes | -8.756 to -8.562 |
| crest_db | 15.878 | 19.286 | 15.622 | yes | 15.118 to 16.338 |
| active_level_range80_db | 16.545 | 16.992 | 16.960 | yes | 16.414 to 17.057 |
| active_level_iqr_db | 9.728 | 9.491 | 9.968 | no | 9.554 to 10.162 |
| pause_fraction_internal | 0.119 | 0.238 | 0.109 | yes | 0.085 to 0.140 |
| pause_median_seconds | 0.320 | 0.736 | 0.256 | yes | 0.256 to 0.512 |
| pause_p90_seconds | 0.954 | 1.024 | 0.730 | no | 0.531 to 0.954 |
| pauses_per_minute | 15.032 | 19.100 | 15.944 | yes | 12.077 to 15.219 |
| speech_run_median_seconds | 2.992 | 2.144 | 2.656 | yes | 2.288 to 3.552 |
| envelope_modulation_peak_hz | 0.549 | 0.549 | 0.549 | no | 0.549 to 0.549 |
| band_100_250_db | -1.524 | -1.918 | -1.540 | yes | -1.736 to -1.337 |
| band_250_500_db | -6.797 | -6.180 | -6.783 | yes | -7.528 to -5.958 |
| band_500_1000_db | -13.464 | -12.261 | -13.411 | yes | -14.763 to -12.702 |
| band_1000_2000_db | -20.331 | -15.106 | -19.897 | yes | -20.670 to -19.615 |
| band_2000_4000_db | -17.636 | -19.502 | -17.162 | yes | -19.704 to -16.228 |
| band_4000_8000_db | -20.756 | -19.031 | -20.412 | yes | -21.337 to -20.097 |
| band_8000_11000_db | -21.601 | -26.931 | -23.388 | yes | -22.122 to -21.016 |

HNR is a harmonic/noise proxy, not a direct breathiness measurement. The reference contains background audio, affecting noise, spectral and loudness measurements. Pause counts, rhythm and consonant statistics also depend on the words. Remaining differences were retained rather than forcing arbitrary pitch wobble, cutting consonants, or copying the background music. Both final WAVs pass finite-sample, decoding, duration and peak checks. Accent and listening quality still require an audition.

Repeat with the same local reference/source: run `scripts/match_sleep_voice.py`, then `scripts/refine_sleep_voice.py` in the main `.venv`. The Qwen GPU is not used by these refinement scripts. Install `requirements-voice-analysis.txt` in addition to the existing project requirements; Silero model download is at `media/voice-analysis/silero_vad.onnx`.