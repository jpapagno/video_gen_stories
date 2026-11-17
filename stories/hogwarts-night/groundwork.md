# The Room Where Maps Sleep

An original, unofficial fan story set at Hogwarts, written in an independent narrative voice. No adaptation of a book or film plot. All principal characters and the map-room premise are new.

## Story foundation

You are a visiting adult magical cartographer, invited to restore the castle's small collection of seasonal landscape maps during a quiet autumn holiday. Elian Vale, the elderly map custodian, leaves you a simple task: help each landscape settle into its night-time shape. The maps need patience, warmth, and a little silver ink. Nothing is missing, threatening, or urgent. The reward is a comfortable room and the feeling of having cared for a small corner of the world.

Setting anchors: Hogwarts, moving portraits, enchanted ceilings, the Black Lake, owls, gentle household magic. Keep the established setting recognizable without relying on canon characters, borrowed dialogue, film music, or retelling existing adventures. Invented details are this story's additions, not claims about canon.

Continuity: one rainy autumn evening; adult visitor; brass key; blue wool coat; silver ink; green-shaded lamp; map room facing the lake; Elian departs after tea. No villain, puzzle to solve, danger, school examinations, cliffhanger, loud surprises, or final awakening.

## Narration foundation

Second-person, present tense, warm and unhurried. Plain sensory prose, soft transitions, very little dialogue. Begin with a clear sense of shelter. Gradually reduce new information. Listening must remain comfortable if a chapter is missed. Do not command sleep or make medical promises. Read headings silently: only prose goes to the voice API.

Use a licensed stock voice with a gentle storytelling delivery. Starting model: eleven_multilingual_v2. Starting settings: stability .75, similarity .75, style 0, speaker boost off, speed .85. These are audition settings, not a guarantee of words per minute. Avoid imitating an actor or audiobook performer.

## Full episode foundation

Minimum finished duration: 10,800 seconds. Plan 12 chapters of about 1,750 words each: 21,000 words. At 105-115 measured words/minute, this is about 183-200 minutes before brief transitions. Estimate from the audition, then revise the word budget. Actual encoded duration is the acceptance criterion. Do not meet three hours by looping the prototype or silently padding the ending.

| Chapter | Pivotal change | Scene to hold | Gentle narrative movement |
| --- | --- | --- | --- |
| 1 | Arrival | Rainy castle entrance, amber windows | Enter, dry your coat, accept the key |
| 2 | Welcome | Small fireside tea table | Meet Elian and receive the simple invitation |
| 3 | Enter map room | Lake-facing room, green lamp | Discover the seasonal atlas collection |
| 4 | First map opens | Painted orchard under stars | Brush silver dew onto the orchard paths |
| 5 | Map changes season | Sheltered winter village | Warm the paper windows one by one |
| 6 | Quiet interval | Window seat over the lake | Tea, distant owls, rain on glass |
| 7 | New landscape | Moonlit greenhouse map | Let the enchanted leaves fold for the night |
| 8 | River settles | Bridge and slow silver river | Restore the reflected stars |
| 9 | Archive closes | Shelves of sleeping atlases | Return maps and wrap the brushes |
| 10 | Walk to guest room | Empty portrait corridor | Gentle farewells, warm pools of lamplight |
| 11 | Settle in | Guest room, low fire, rain | Leave coat and key beside the door |
| 12 | Rest | Still window and fading hearth | Fewer details, long calm paragraphs, no wake-up |

## Scene foundation

One main visual per chapter; changes follow actual audio chapter boundaries. Eight-second dissolves in the eventual video, extremely slow camera drift, dim amber and midnight blue palette. No flashing spells, rapid cuts, subtitles that demand attention, or bright title cards. Consistent castle architecture and weather. The prototype contains three scene briefs only; final images and video rendering are later stages.

Ambience later: steady soft rain, very low hearth, no thunder or animal cries. Keep narration intelligible. No background music in the first voice audition so pacing and artifacts are easy to assess. Final mix target starting point: -20 LUFS integrated and <= -3 dBTP, verified after encoding; audition at comfortable playback volume.

## Separate deliverables

1. This story bible and chapter outline.
2. `prototype.json`: narration prose, scene briefs, voice configuration.
3. `prototype-script.md`: human-readable story only, exported by the code.
4. `scripts/sleep_story.py`: validation, word/character estimate, chunked ElevenLabs generation, resumable cache, alignment, measured scene timeline, combined WAV.
5. Generated audio and timing live under `outputs/sleep-story/`; never store the API key there or in the client bundle.

The prototype is deliberately short and exempt from the three-hour final-episode minimum. Its three miniature chapters test narration and scene boundaries. The full 21,000-word story has not yet been written.
