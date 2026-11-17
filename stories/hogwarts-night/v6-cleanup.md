# V6 crackle cleanup

User selection: V6. Original audio is retained. Latest cleanup: `outputs/sleep-story/qwen/metric-match/v6-clean.wav`.

The V6 refinement had added synthetic aspiration at 12% of signal RMS, then processed the result through spectral matching and de-essing. This was the leading noise hypothesis; V6 had no clipped samples. The exact original path was replayed with maximum sample error of 1.2e-7, consistent with its 24-bit PCM quantization. The clean revision reruns the same three selected processing iterations with that artificial aspiration disabled. The voice-design source, pitch mapping, micro-prosody setting and timing input remain the same.

| Check | Original V6 | V6 clean |
| --- | ---: | ---: |
| Duration | 18.9411 s | 18.9411 s |
| Median pitch | 99.509 Hz | 99.566 Hz |
| Pitch range (p10–p90) | 5.2816 semitones | 5.2744 semitones |
| Median spectral flatness | .2556 | .1086 |
| Median HNR | 13.50 dB | 14.33 dB |
| Integrated loudness | -24.9516 LUFS | -24.9516 LUFS |

The clean WAV decodes, contains finite samples, has identical frame count, and peaks below .39 full scale. These checks establish that the added noise was removed without changing duration or materially changing the measured pitch. They do not establish that every audible crackle or resynthesis artifact is gone; that remains a listening check. No high-frequency blanket filter or new model generation was used.

Reproduce with `.venv\Scripts\python scripts/clean_v6_voice.py`. The script fails if its original-V6 replay differs beyond 2e-6 before creating the cleanup.
