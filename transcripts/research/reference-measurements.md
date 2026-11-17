# Reference transcript measurements

Three quiet-story uploads from one creator, The Sleepy Shack. This is a provisional house-style profile, not a universal sleep-story standard. Full reference prose is not reproduced here.

Automatic caption punctuation supplies estimated sentences; caption line breaks do not supply paragraphs. The first 120 and last 30 captioned seconds are excluded provisionally, not through semantic intro detection.

| Reference | Story-window words | Sentence median / p90 | Median estimated WPM | Last caption | Video duration |
|---|---:|---:|---:|---:|---:|
| [A Day at Hogwarts: Gryffindor Students' Adventures](https://www.youtube.com/watch?v=DqE40ZHyF7E) | 22468 | 13.0 / 27.0 | 132 | 172.8 min | 281.8 min |
| [The Midnight Library Sessions: Books & Quiet Magic](https://www.youtube.com/watch?v=l9K6lfAX8v0) | 22223 | 14.0 / 28.0 | 149 | 151.9 min | 275.3 min |
| [The Kitchen's Secret Hours: Midnight Comfort & Magic](https://www.youtube.com/watch?v=r5K09zDkTMs) | 18248 | 12.0 / 25.0 | 151 | 122.6 min | 282.6 min |

## Approximately 1,000-word windows

62 windows. These are descriptive ranges to guide a test, not pass/fail evidence of good prose.

| Metric | 10th percentile | Median | 90th percentile |
|---|---:|---:|---:|
| sentence_words_p10 | 4.000 | 6.000 | 8.990 |
| sentence_words_median | 10.000 | 14.000 | 19.000 |
| sentence_words_p90 | 21.000 | 26.000 | 33.000 |
| sentence_words_p95 | 24.155 | 29.000 | 36.800 |
| sentences_over_40_fraction | 0.000 | 0.000 | 0.021 |
| sentences_under_8_fraction | 0.074 | 0.181 | 0.353 |
| question_sentence_fraction | 0.000 | 0.021 | 0.086 |
| sentence_opening_top_bigram_fraction | 0.025 | 0.036 | 0.061 |
| mattr_100 | 0.767 | 0.790 | 0.815 |
| repeated_8gram_token_fraction | 0.000 | 0.000 | 0.000 |
| scenic_cues_per_1000 | 7.064 | 15.855 | 28.707 |
| dialogue_tag_cues_per_1000 | 0.990 | 4.948 | 10.985 |
| past_auxiliary_cues_per_1000 | 0.987 | 3.982 | 19.954 |
| present_auxiliary_cues_per_1000 | 4.056 | 11.952 | 21.642 |
| first_person_pronouns_per_1000 | 0.990 | 6.483 | 20.562 |
| second_person_pronouns_per_1000 | 0.000 | 3.982 | 10.719 |
| third_person_pronouns_per_1000 | 37.724 | 49.505 | 65.868 |
| sight_cues_per_1000 | 1.945 | 7.474 | 19.809 |
| sound_cues_per_1000 | 1.980 | 5.955 | 11.899 |
| touch_cues_per_1000 | 1.979 | 5.430 | 11.877 |
| smell_cues_per_1000 | 0.000 | 0.000 | 0.999 |
| taste_cues_per_1000 | 0.000 | 0.989 | 5.983 |

Lexicon cue counts depend on a small explicit dictionary in `text_metrics.py`; they cannot establish sensory depth, dialogue share, emotional arousal or plot quality. No paragraph, new-character or scene-change counts are claimed. First-occurrence vocabulary decline is not treated as proof of declining novelty.

Long runtimes can contain uncaptained sections. The sparse late-audio probe results for the user's reference are stored in ignored `media/transcript-research/reference-metadata.json`; do not generalize three probes to the entire tail.