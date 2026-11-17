# Singer cutout rig v1

Open http://127.0.0.1:5173/rig.html and press Play 12-second test. The full song can also be scrubbed with the audio player. Controls adjust gesture strength, framing, and show the sprite atlas or joint guides.

Assets generated with the built-in image tool:

- public/art/singer-rig-atlas-v1.png: alpha-transparent six-cell atlas, torso, two replacement heads, two whole-arm pieces, microphone. Verified RGBA with about 72% fully transparent pixels.
- public/art/blues-empty-club-v1.png: empty background plate.
- Prompts: outputs/rig-generation-prompts.json.

src/rig.js trims each atlas cell to alpha bounds at load time and draws its source rectangle. Pivots define waist, neck and shoulder joints. These parameters can be reused at any time without regenerating art. The head uses two replacement drawings: open eyes/neutral mouth and closed eyes/open mouth. They are coupled; independent blink and mouth controls need additional facial assets. Whole-arm rotation supports a limited gesture, not elbow articulation or arbitrary poses. No head turn is implied by rotating a single view.

Song RMS samples from outputs/song.json scale the gesture amplitude. A scripted gesture envelope and head/torso oscillations supply acting. Camera changes at 4 and 8 seconds into the test are authored cues, not learned musical boundaries. Mouth changes use energy plus an oscillator; they are not vocal isolation, phoneme recognition, or lip sync.

This small renderer uses browser Canvas 2D rather than adding PixiJS overhead. The rig hierarchy and atlas are portable to PixiJS if mesh deformation or larger scenes become useful. Export uses deterministic frame capture with Playwright and FFmpeg; no AI video service or per-frame image generation.

Validation: assembled medium and close-up frames inspected, shoulder anchors and cropping adjusted; playback/control smoke check had no browser errors and audio played; Vite build passed. Export frames use the same browser drawing code. Final generated video remains an animation prototype.

Reproduce capture: node scripts/render_rig.cjs. Preview-only: append --preview. Browser executable is currently configured for this Windows Chrome installation. Vite must be running first; RIG_URL can override the preview URL. The script pauses automatic browser animation and explicitly supplies the render time for reproducible output.
