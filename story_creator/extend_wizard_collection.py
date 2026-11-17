"""Extend the existing wizard narration using its saved writing workflow."""
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from .prepare import prepare_file

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'story_creator/stories/wizard-three-hours-20261117'
SOURCE = ROOT / 'story_creator/comparisons/20261116-202422'
BRIEFS = [
    ('02-the-window-seat', 'Hermione, visiting Hogwarts as an adult, helps McGonagall make a neglected window seat comfortable for quiet reading. An old fabric sample book helps them choose a cushion and curtain. Resolve who the seat is for through its ordinary use. Hermione ends asleep in her guest room.'),
    ('03-the-evening-post', 'An adult Harry and Ron spend a peaceful evening in Hogsmeade, helping Hagrid find the intended recipient of an unaddressed parcel of repaired gardening gloves. The answer comes through kind, ordinary conversations, without suspense or a grand revelation. Harry ends asleep at his overnight lodging.'),
    ('04-a-shelf-for-small-things', 'Luna visits Neville at Hogwarts as adults. They arrange a small shelf for useful everyday things in the greenhouse potting room, gradually working out what belongs there and making room for a contribution from Hagrid. Avoid a plant-delivery plot. Neville ends asleep in his rooms.'),
    ('05-the-quiet-table', 'Adult Ron and Hermione visit Hogwarts for a small weekend gathering. With McGonagall they work out how to seat a few old friends comfortably at an informal supper, using an awkward little table and its mismatched chairs. Keep the purpose practical and the discoveries modest. Ron ends asleep in the guest room he shares with Hermione.'),
    ('06-the-last-page-of-the-day', 'An adult Harry stays at Hogwarts after visiting Neville. With help from Luna, he finishes a simple handwritten guide to a short, pleasant walk through the grounds for future visitors. They test its directions before dusk, making the guide kinder and clearer. No mysteries, danger, lost objects or extraordinary discoveries. Harry ends asleep in his guest room.'),
]


def words(text):
    return len(text.split())


def generate(item):
    slug, brief = item
    folder = OUT / slug
    folder.mkdir(exist_ok=True)
    receipt_path = folder / 'generation.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('status') == 'complete':
            return receipt
    base = (OUT / 'base-prompt.txt').read_text(encoding='utf-8')
    prompt = base.replace('approximately 4,080 words long, intended for about 30 minutes',
                          'approximately 4,600 words long, intended for about 33 minutes')
    prompt += ('\n\nCollection brief: ' + brief +
               '\nThis is a new standalone story in a six-story bedtime collection. '
               'Do not recap or repeat The Last Pot of Lemon Balm. Give this story its own beginning, '
               'connected middle and complete sleeping ending. Aim for 4,500–4,800 words; '
               'develop the connected events fully without padding. Return the title on its own '
               'first line, followed by narration prose only.\n')
    (folder / 'prompt.txt').write_text(prompt, encoding='utf-8')
    command = [shutil.which('codex'), 'exec', '--ignore-user-config', '--ephemeral',
               '--skip-git-repo-check', '--sandbox', 'read-only', '--color', 'never',
               '--model', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="low"',
               '--json', '--output-last-message', str(folder / 'raw-story.txt'), '-']
    start = time.monotonic()
    print('Writing ' + slug, flush=True)
    with (folder / 'events.jsonl').open('w', encoding='utf-8') as events, (folder / 'stderr.log').open('w', encoding='utf-8') as errors:
        result = subprocess.run(command, input=prompt, text=True, encoding='utf-8',
                                stdout=events, stderr=errors, cwd=folder)
    receipt = dict(slug=slug, model='gpt-6.1-sol', reasoning_effort='low',
                   requested_ui_equivalent='Light', exit_code=result.returncode,
                   elapsed_seconds=round(time.monotonic() - start, 2),
                   status='failed', credit_charge='Not exposed by runner')
    for line in (folder / 'events.jsonl').read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        if event.get('type') == 'turn.completed':
            receipt['usage'] = event.get('usage')
    if result.returncode == 0 and (folder / 'raw-story.txt').exists():
        raw = (folder / 'raw-story.txt').read_text(encoding='utf-8').strip()
        prepare_file(folder / 'raw-story.txt', folder / 'fixed-story.txt')
        receipt.update(status='complete', title=raw.splitlines()[0], words=words(raw))
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)
    return receipt


def main():
    OUT.mkdir(exist_ok=True)
    shutil.copyfile(SOURCE / 'prompt.txt', OUT / 'base-prompt.txt')
    first = OUT / '01-the-last-pot-of-lemon-balm'
    first.mkdir(exist_ok=True)
    for name in ('raw-story.txt', 'fixed-story.txt', 'generation.json', 'prompt.txt'):
        shutil.copyfile(SOURCE / name, first / name)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(generate, BRIEFS))
    if any(row['status'] != 'complete' for row in results):
        raise RuntimeError('Incomplete generation; saved outputs retained')
    parts = [first / 'fixed-story.txt'] + [OUT / slug / 'fixed-story.txt' for slug, _ in BRIEFS]
    original_words = words(parts[0].read_text(encoding='utf-8'))
    measured_seconds = 1636.92
    wpm = original_words / (measured_seconds / 60)
    rows = []
    for path in parts:
        text = path.read_text(encoding='utf-8').strip()
        count = words(text)
        rows.append(dict(title=text.splitlines()[0], file=str(path.relative_to(ROOT)),
                         words=count, estimated_minutes=round(count / wpm, 2),
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    total = sum(row['words'] for row in rows)
    manifest = dict(status='drafts_complete', target_minutes=180,
                    original_audio_seconds=measured_seconds, measured_words_per_minute=wpm,
                    total_words=total, estimated_total_minutes=round(total / wpm, 2),
                    narration_rendered=False, stories=rows)
    (OUT / 'collection.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (OUT / 'combined-transcript.txt').write_text('\n\n\n'.join(p.read_text(encoding='utf-8').strip() for p in parts) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    main()
