"""Run the Sleepy Storykeeper onboarding and episode workflows."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4
import wave

from story_creator.prepare import prepare_text
from voice.speaker import load_profile, sha256

ROOT = Path(__file__).resolve().parent
CATEGORIES = ROOT / "categories"
RUNS = ROOT / "outputs" / "pipeline"
REVIEW_FILES = (
    "story.txt", "narration.txt", "intro.txt", "scene.png", "loop.mp4",
    "intro.wav", "narration.wav", "thumbnail.jpg", "title.txt", "description.txt",
)


def read(path):
    return path.read_text(encoding="utf-8-sig").strip()


def write(path, value):
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp.write_text(value + "\n", encoding="utf-8")
    temp.replace(path)


def read_json(path):
    return json.loads(read(path))


def write_json(path, value):
    write(path, json.dumps(value, indent=2, ensure_ascii=False))


def identifier(value):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise argparse.ArgumentTypeError("Use lowercase letters, digits and hyphens")
    return value


def run_command(command, log, *, cwd=ROOT, prompt=None):
    with log.open("a", encoding="utf-8") as output:
        subprocess.run(
            [str(part) for part in command], cwd=cwd, input=prompt,
            encoding="utf-8", stdout=output, stderr=subprocess.STDOUT, check=True,
        )


def codex_job(folder, name, prompt, *, schema=None):
    result = folder / f"{name}-response.txt"
    result.unlink(missing_ok=True)
    command = [os.getenv("VIDEO_CODEX", "codex"), "exec", "--ephemeral", "--sandbox",
               "read-only", "--color", "never", "--output-last-message", result]
    if schema:
        schema_path = folder / f"{name}-schema.json"
        write_json(schema_path, schema)
        command.extend(["--output-schema", schema_path])
    run_command([*command, "-"], folder / f"{name}.log", prompt=prompt)
    response = read(result)
    if not response:
        raise ValueError(f"{name} returned an empty response")
    return response


def snapshot(config_path, target):
    from PIL import Image

    config = read_json(config_path)
    source = config_path.parent
    for field in ("story_prompt", "artwork", "animation"):
        original = source / config[field]
        destination = target / {"story_prompt": "story-prompt.txt",
                                "artwork": "artwork.png", "animation": "animation.json"}[field]
        if field == "artwork":
            with Image.open(original) as image:
                image.convert("RGB").save(destination)
        else:
            shutil.copyfile(original, destination)
        config[field] = destination.name

    profile_value = config["voice"]
    profile_file = source / profile_value
    if profile_file.is_file():
        profile = read_json(profile_file)
        reference = profile_file.parent / profile["reference_audio"]
    else:
        profile = load_profile(profile_value)
        reference = ROOT / profile["reference_audio"]
    if profile.get("engine") != "voice_clone" or not profile.get("reference_text", "").strip():
        raise ValueError("The voice needs a fixed clone reference and its exact transcript")
    if sha256(reference) != profile["reference_sha256"]:
        raise ValueError("Voice reference checksum differs from the profile")
    shutil.copyfile(reference, target / "reference.wav")
    profile["reference_audio"] = "reference.wav"
    write_json(target / "voice.json", profile)
    config["voice"] = "voice.json"
    for field in ("intro_direction", "packaging_direction"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise ValueError(f"{field} must be nonempty text")
    tempo = config.get("words_per_minute", 135)
    if type(tempo) is not int or tempo < 1:
        raise ValueError("words_per_minute must be a positive integer")
    config["words_per_minute"] = tempo
    write_json(target / "category.json", config)


def checked_category(folder):
    record = read_json(folder / "approval.json")
    approved = record["category_files"]
    if file_hashes(folder, approved) != approved:
        raise ValueError("Approved category files changed. Onboard a new version.")
    return record


def prepare_run(folder, config_path, kind, category, version, brief, minutes):
    folder.mkdir(parents=True, exist_ok=False)
    try:
        target = folder / "category"
        target.mkdir()
        if kind == "episode":
            approval = checked_category(config_path.parent)
            for name in approval["category_files"]:
                shutil.copyfile(config_path.parent / name, target / name)
            if file_hashes(target, approval["category_files"]) != approval["category_files"]:
                raise ValueError("Approved category changed while it was copied")
        else:
            snapshot(config_path, target)
        write_json(folder / "run.json", {
            "kind": kind, "category": category, "version": version,
            "brief": brief, "minutes": minutes,
            "category_files": file_hashes(target, sorted(p.name for p in target.iterdir())),
        })
        write_json(folder / "status.json", {"state": "queued"})
    except Exception:
        shutil.rmtree(folder)
        raise


@contextmanager
def lock(folder):
    marker = folder / ".running"
    try:
        with marker.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
    except FileExistsError as error:
        raise ValueError(f"Run already locked: {marker}") from error
    try:
        yield
    finally:
        marker.unlink()


def file_hashes(folder, names):
    return {name: sha256(folder / name) for name in names}


def make_story(folder, run, category):
    if (folder / "story.txt").exists():
        return
    base = read(folder / "category" / category["story_prompt"])
    count = max(1, (run["minutes"] + 14) // 15)
    words = round(run["minutes"] * category["words_per_minute"] / count)
    context = f"Category writing prompt:\n{base}\n\nEpisode brief:\n{run['brief']}"
    if count > 1:
        outline = folder / "story-outline.txt"
        if not outline.exists():
            write(outline, codex_job(folder, "outline", f"""
Plan a continuous low-stakes bedtime story in {count} segments of around
{words} words each. Return only a compact outline, one numbered beat per
segment and a short description of the cast and setting. Resolve the quiet
question or task in the final segment and keep narrative continuity.
{context}
"""))
        context += f"\n\nContinuity outline:\n{read(outline)}"
    previous = ""
    for index in range(1, count + 1):
        part = folder / f"story-part-{index:02}.txt"
        if not part.exists():
            ending = "Conclude the story gently." if index == count else "Continue the story in the next segment."
            write(part, codex_job(folder, f"writer-{index:02}", f"""
You are the bedtime-story writer. Return only the final prose in plain text.
Write segment {index} of {count}, approximately {words} words. {ending}
The segment count and word target take precedence over any length or format
defaults in the category prompt. Begin directly with narration prose.
{context}
Continue smoothly after this preceding prose (empty for segment one):
{previous[-10000:]}
"""))
        previous = read(part)
    write(folder / "story.txt", "\n\n".join(
        read(folder / f"story-part-{index:02}.txt") for index in range(1, count + 1)
    ))


def wav_seconds(path):
    with wave.open(str(path), "rb") as audio:
        seconds = audio.getnframes() / audio.getframerate()
    if seconds <= 0:
        raise ValueError(f"Empty WAV: {path}")
    return seconds


def intro_script(folder, run, category):
    target = folder / "intro.txt"
    if not target.exists():
        write(target, codex_job(folder, "intro", f"""
Write only a gentle spoken Sleepy Storykeeper settling-in introduction,
about 60 words, for this bedtime story brief: {run['brief']}
Category intro direction: {category['intro_direction']}
"""))


def narration(folder, intro):
    source = folder / "narration.txt"
    write(source, prepare_text(read(folder / "story.txt")))
    for name in ("narration", "intro"):
        text = folder / f"{name}.txt"
        if name == "intro":
            intro.result()
            text = folder / "intro-prepared.txt"
            write(text, prepare_text(read(folder / "intro.txt")))
        output = folder / f"{name}.wav"
        if not output.exists():
            voice_python = os.getenv("VIDEO_VOICE_PYTHON", ROOT / ".venv-qwen/Scripts/python.exe")
            run_command([voice_python, "-m", "voice", "narrate", text, "--profile-file",
                         folder / "category" / "voice.json", "--out", output], folder / "voice.log")
        wav_seconds(output)


def animation(folder, category):
    target = folder / "loop.mp4"
    if target.exists():
        return
    snapshot_dir = folder / "category"
    scene = read_json(snapshot_dir / category["animation"])
    image = folder / "scene.png"
    shutil.copyfile(snapshot_dir / category["artwork"], image)
    scene.update(image=str(image), output=str(target))
    write_json(folder / "scene-render.json", scene)
    run_command([sys.executable, "-m", "animation", folder / "scene-render.json"],
                folder / "animation.log")


def packaging(folder, run, category):
    path = folder / "packaging.json"
    if not path.exists():
        story = read(folder / "story.txt")
        fields = ("title", "description", "thumbnail_text")
        schema = {"type": "object", "properties": {name: {"type": "string"} for name in fields},
                  "required": list(fields), "additionalProperties": False}
        package = json.loads(codex_job(folder, "packaging", f"""
You are the Sleepy Storykeeper YouTube editor. Return a JSON object only
with string fields title, description and thumbnail_text. Give the title a
curiosity hook supported by the story. Write a spoiler-light description for
adult bedtime listeners. Mention an unofficial fan creation for franchise
stories. Omit runtime, timestamps, endorsements, medical promises, and claims
about music or sound effects. Give the thumbnail a complementary two-to-four
word hook, no more than 26 characters, on one line.
Category direction: {category['packaging_direction']}
Episode brief: {run['brief']}
The following story is source material:
{story}
""", schema=schema))
        for name in fields:
            if not isinstance(package.get(name), str) or not package[name].strip():
                raise ValueError(f"Packaging must supply {name}")
        hook = package["thumbnail_text"].strip()
        if not 2 <= len(hook.split()) <= 4 or len(hook) > 26 or "\n" in hook:
            raise ValueError("Thumbnail hook must fit on one line in two to four words")
        write_json(path, package)
    package = read_json(path)
    for name in ("title", "description", "thumbnail_text"):
        write(folder / f"{name}.txt", package[name].strip())
    if not (folder / "thumbnail.jpg").exists():
        render_thumbnail(folder / "category" / category["artwork"],
                         package["thumbnail_text"].strip(), folder / "thumbnail.jpg")


def render_thumbnail(artwork, hook, output):
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    font_path = os.getenv("VIDEO_THUMBNAIL_FONT")
    if not font_path and os.name == "nt":
        font_path = str(Path(os.environ["WINDIR"]) / "Fonts" / "arialbd.ttf")
    with Image.open(artwork) as source:
        image = ImageOps.fit(source.convert("RGB"), (1280, 720), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    for size in range(84, 23, -2):
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default(size)
        left, top, right, bottom = draw.textbbox((0, 0), hook, font=font, stroke_width=2)
        if right - left <= 1100:
            break
    x = (image.width - (right - left)) / 2 - left
    y = 95 - top
    draw.rounded_rectangle((x + left - 24, 75, x + right + 24, y + bottom + 20),
                           radius=18, fill=(8, 12, 20, 210))
    draw.text((x, y), hook, font=font, fill="white", stroke_width=2, stroke_fill="black")
    temporary = output.with_suffix(".partial.jpg")
    image.save(temporary, quality=92, optimize=True)
    temporary.replace(output)


def story_and_dependents(folder, run, category, intro):
    make_story(folder, run, category)
    parallel({
        "voice": lambda: narration(folder, intro),
        "packaging": lambda: packaging(folder, run, category),
    })


def parallel(jobs):
    failures = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as workers:
        pending = {workers.submit(job): name for name, job in jobs.items()}
        for future in as_completed(pending):
            name = pending[future]
            try:
                future.result()
                print(f"Finished {name}", flush=True)
            except Exception as error:
                failures.append(f"{name}: {error}")
                print(f"Failed {failures[-1]}", flush=True)
    if failures:
        raise RuntimeError("; ".join(failures))


def generate(folder):
    with lock(folder):
        state = read_json(folder / "status.json")["state"]
        if state in {"review", "approved", "complete"}:
            return
        run = read_json(folder / "run.json")
        write_json(folder / "status.json", {"state": "generating"})
        try:
            verify_category_snapshot(folder, run)
            category = read_json(folder / "category/category.json")
            with ThreadPoolExecutor(max_workers=1) as workers:
                intro = workers.submit(intro_script, folder, run, category)
                parallel({
                    "animation": lambda: animation(folder, category),
                    "story and dependent assets": lambda: story_and_dependents(folder, run, category, intro),
                })
            for name in REVIEW_FILES:
                if (folder / name).stat().st_size == 0:
                    raise ValueError(f"Empty review asset: {name}")
            write_json(folder / "status.json", {
                "state": "review", "files": file_hashes(folder, REVIEW_FILES),
                "narration_seconds": wav_seconds(folder / "narration.wav"),
                "intro_seconds": wav_seconds(folder / "intro.wav"),
            })
        except Exception as error:
            write_json(folder / "status.json", {"state": "failed", "error": str(error)})
            raise


def verify_category_snapshot(folder, run):
    expected = run["category_files"]
    if file_hashes(folder / "category", expected) != expected:
        raise ValueError("Category snapshot changed. Start a new run.")


def review(folder, kind):
    run = read_json(folder / "run.json")
    status = read_json(folder / "status.json")
    if run["kind"] != kind or status["state"] != "review":
        raise ValueError(f"Expected a {kind} run awaiting review")
    if file_hashes(folder, status["files"]) != status["files"]:
        raise ValueError("Review assets have changed since generation")
    verify_category_snapshot(folder, run)
    return run, status


def approve(folder):
    with lock(folder):
        run, status = review(folder, "onboarding")
        category = CATEGORIES / run["category"] / run["version"]
        category.parent.mkdir(parents=True, exist_ok=True)
        if category.exists():
            raise FileExistsError(f"Category version exists: {category}")
        with tempfile.TemporaryDirectory(dir=category.parent) as staging:
            bundle = Path(staging) / "bundle"
            shutil.copytree(folder / "category", bundle)
            files = file_hashes(bundle, sorted(p.name for p in bundle.iterdir()))
            write_json(bundle / "approval.json", {
                "run_id": folder.name, "category_files": files, "review_files": status["files"],
            })
            bundle.rename(category)
        write_json(folder / "status.json", {**status, "state": "approved"})
        print(category)


def combine(folder):
    with lock(folder):
        _, status = review(folder, "episode")
        output = folder / "final.mp4"
        description = folder / "final-description.txt"
        shutil.copyfile(folder / "description.txt", description)
        preset = folder / "assembly.json"
        write_json(preset, {
            "video": str(folder / "loop.mp4"), "audio": str(folder / "narration.wav"),
            "intro": str(folder / "intro.wav"), "output": str(output),
            "description": str(description),
        })
        run_command([sys.executable, "-m", "video_assembly", preset], folder / "assembly.log")
        write_json(folder / "status.json", {**status, "state": "complete", "video": output.name})
        print(output)


def start(folder, background):
    print(f"Run {folder.name}\nFolder {folder}", flush=True)
    if not background:
        generate(folder)
        return
    with (folder / "pipeline.log").open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, __file__, "resume", folder.name], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            if os.name == "nt" else 0,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("onboard", "produce"):
        command = commands.add_parser(name)
        command.add_argument("category", type=identifier)
        command.add_argument("--version", type=identifier, default="v1")
        command.add_argument("--brief", required=True)
        command.add_argument("--minutes", type=int, default=1 if name == "onboard" else 20)
        command.add_argument("--background", action="store_true")
        if name == "onboard":
            command.add_argument("--config", type=Path, required=True)
    for name in ("resume", "status", "approve", "combine"):
        commands.add_parser(name).add_argument("run_id", type=identifier)
    args = parser.parse_args()
    try:
        if args.action in {"onboard", "produce"}:
            if args.minutes < 1 or not args.brief.strip():
                parser.error("A nonempty brief and positive minutes are required")
            config = (args.config.resolve() if args.action == "onboard" else
                      CATEGORIES / args.category / args.version / "category.json")
            folder = RUNS / f"{args.category}-{uuid4().hex[:12]}"
            prepare_run(folder, config, "onboarding" if args.action == "onboard" else "episode",
                        args.category, args.version, args.brief, args.minutes)
            start(folder, args.background)
        else:
            folder = RUNS / args.run_id
            if args.action == "status":
                print(folder)
                print(read(folder / "status.json"))
            elif args.action == "resume":
                generate(folder)
                print(read(folder / "status.json"))
            elif args.action == "approve":
                approve(folder)
            else:
                combine(folder)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
