# Music video measurement pipeline

Analyze an audio file, measure a reference video, and transfer reference shot lengths in musical beats onto another recording.

## Run (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts/analyze.py media/reference.mp4 --video --out outputs/reference.json
.venv\Scripts\python scripts/analyze.py media/st-louis-blues.mp3 --reference outputs/reference.json --out outputs/target.json
```

Outputs include beat and onset timestamps, quarter-second RMS energy and spectral brightness, detected cuts, shot lengths in seconds/beats, distance of cuts from beats, and sampled visual brightness/saturation/optical flow. The target output adds a proposed edit timeline for Three.js. Scene labels are creative placeholders, not inferred reference content.

Librosa replaces the initially proposed Essentia extractor for this Windows implementation. Neither lyrics nor semantic song sections are automatically measured in this first version. Beats, cuts, and transferred edits are explicitly marked unreviewed. Optical flow combines subject and camera movement and is resolution-dependent; it does not establish camera speed. Cuts can be confused with flashes or fast motion. Beat tracking can choose half/double tempo and needs listening checks, especially for vintage blues. Beat alignment statistics are descriptive, not evidence of intentional synchronization; a chance baseline and more references are needed for inference.

Transfer preserves the ordered sequence of measured shot lengths in beats and repeats it as needed for the target length. It does not yet match musical sections, learn energy-to-cut relationships, or render a finished video.

## Sources

- Reference: Amy Winehouse, Back to Black, https://www.youtube.com/watch?v=TJAfLE39ZZ8 . Reference footage/audio is for analysis and is not included in generated work.
- Target: Bessie Smith / Louis Armstrong, St. Louis Blues (1925), https://commons.wikimedia.org/wiki/File:Bessie_Smith_and_Louis_Armstrong_-_The_St._Louis_Blues_(1925).mp3 . Commons identifies the recording as public domain in the US; uploader provenance is only 'Mp3 I found', so verify the transfer before publication. UCSB's recording entry was unavailable during acquisition.
- Public-domain corroboration: https://cspd.law.duke.edu/publicdomainday/2026/ . Other jurisdictions differ.

Local media and intermediate WAVs are excluded from version control.

## Preview

Run `npm run dev` and open the displayed local URL. Press play in the audio player. The Three.js city study uses `outputs/target.json` for cuts; it is an early camera/edit prototype, not a finished music video. For a fresh clone, copy the target recording into `public/media/st-louis-blues.mp3`. `npm run build` bundles the timeline and copies that public audio into the local build.
