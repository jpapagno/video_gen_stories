"""Short viewer-facing description format, separate from production metadata."""
import math

INTRO_NOTE = "A short settling-in introduction opens the video, followed by a quiet pause before the first story."


def duration_label(seconds):
    if seconds >= 10800:
        hours = math.floor(seconds / 3600)
        return f"{hours} hours"
    minutes = max(1, math.floor(seconds / 60))
    return f"{minutes} minutes"


def render_description(*, opening, seconds, experience, synopsis, intro=False,
                       channel="SleepyStorykeeper", hashtags=()):
    paragraphs = [f"{opening.strip()} Enjoy {duration_label(seconds)} of {experience.strip()}"]
    if intro:
        paragraphs.append(INTRO_NOTE)
    paragraphs += [synopsis.strip(),
                   f"Subscribe to {channel} for gentle stories, quiet adventures and restful nights."]
    if hashtags:
        paragraphs.append(" ".join(hashtags))
    return "\n\n".join(paragraphs) + "\n"
