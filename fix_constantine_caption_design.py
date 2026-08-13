"""Three-tier caption design for the Constantine V5 CapCut project.

Tiers, per the brief:
  대사      MOVIE_DIALOGUE   -- refined sans, legibility first, must recede
  나레이션   REVIEW_NARRATION -- our own narration, editorial serif so it reads as a
                               different voice from the film
  인물      character names inside the narration, coloured to mark importance:
                               yellow for the cast, red for the antagonist Mammon

Two defects are repaired at the same time:
  * REVIEW_NARRATION claimed font_name "Cormorant Garamond" while font_path,
    font_resource_id and the inline style.font all pointed at CapCut's cached
    Rubik-Bold.ttf, so Rubik is what actually rendered.
  * REVIEW_NARRATION had background_alpha 1.0, a solid black box the design never
    called for.

Names are a curated list, not pattern-matched: the source subtitles carry no speaker
data, and Hell / Heaven / Los Angeles / GPS would otherwise be highlighted as people.
Timeranges, positions, text strings and animation refs are left untouched and verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "Constantine" / "story_review_v5"
BACKUP_ROOT = REVIEW / "backups" / "capcut_caption_design"
QA_PATH = REVIEW / "output" / "CAPCUT_CAPTION_DESIGN_QA.json"

DEFAULT_PROJECT = (
    Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects"
    / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"
)
MIRROR_NAMES = {"draft_content.json", "template-2.tmp"}
SERIF_PATH = (
    Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    / "CormorantGaramond-Medium.ttf"
)

CAST_COLOR = "#FFD24D"        # yellow: the people the story follows
ANTAGONIST_COLOR = "#FF5555"  # red: the threat
CAST = ["John Constantine", "Constantine", "Angela", "Isabel",
        "Beeman", "Midnite", "Manuel", "Chas"]
ANTAGONISTS = ["Mammon"]

NARRATION_STYLE = {
    "font_name": "Cormorant Garamond",
    "font_resource_id": "",
    "font_source_platform": 0,
    # Cormorant Garamond's x-height is 0.386 em against Pretendard's 0.530, so at the
    # same nominal size the narration reads far smaller. 7 * 0.530/0.386 = 9.62 makes the
    # lowercase match the dialogue, which is what the eye actually compares.
    "font_size": 9.62,
    "text_color": "#F6EBD2",
    "letter_spacing": 0.030,
    "border_width": 0.032,
    "border_alpha": 1.0,
    "shadow_alpha": 0.62,
    "shadow_smoothing": 0.68,
    "shadow_distance": 1.5,
    "background_alpha": 0.0,
    "italic_degree": 10,
}
DIALOGUE_STYLE = {
    "font_size": 7.0,
    "text_color": "#FFFFFF",
    "letter_spacing": -0.005,
    "border_width": 0.055,
    "border_alpha": 1.0,
    "shadow_alpha": 0.55,
    "shadow_smoothing": 0.70,
    "shadow_distance": 1.6,
    "background_alpha": 0.0,
}
EXPECTED = {"REVIEW_NARRATION": 29, "MOVIE_DIALOGUE": 287}


def hex_to_rgb(value: str) -> list[float]:
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def capcut_running() -> int:
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"],
                             check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return 0
    return sum(1 for line in out.splitlines() if line.lower().startswith("capcut"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mirrors(project: Path) -> list[Path]:
    found = [p for p in project.rglob("*") if p.is_file() and p.name in MIRROR_NAMES]
    if not found:
        raise RuntimeError(f"No project documents under {project}")
    return sorted(found)


def track_material_ids(doc: dict) -> dict[str, list[str]]:
    return {
        str(t.get("name")): [s.get("material_id") for s in t["segments"]]
        for t in doc.get("tracks", []) if t.get("type") == "text"
    }


def fingerprint(doc: dict) -> dict:
    texts = {t["id"]: t for t in doc.get("materials", {}).get("texts", [])}
    segments = []
    for track in doc.get("tracks", []):
        if track.get("type") != "text":
            continue
        for seg in track["segments"]:
            segments.append({
                "target": seg["target_timerange"],
                "material_id": seg.get("material_id"),
                "clip": seg.get("clip"),
                "refs": seg.get("extra_material_refs"),
            })
    return {
        "duration": doc.get("duration"),
        "text_count": len(texts),
        "strings": sorted(json.loads(t["content"]).get("text", "") for t in texts.values()),
        "segments": segments,
        "track_names": [t.get("name") for t in doc.get("tracks", [])],
        "audio_paths": sorted(a.get("path", "")
                              for a in doc.get("materials", {}).get("audios", [])),
        "video_paths": sorted(v.get("path", "")
                              for v in doc.get("materials", {}).get("videos", [])),
    }


def name_spans(text: str) -> list[tuple[int, int, str]]:
    """Character ranges for cast and antagonist mentions, longest name first.

    'John Constantine' has to win over 'Constantine' so the first name is coloured too,
    and a trailing possessive is included so "Beeman's" does not end mid-word.
    """
    spans: list[tuple[int, int, str]] = []
    taken: set[int] = set()
    ordered = ([(n, ANTAGONIST_COLOR) for n in ANTAGONISTS]
               + [(n, CAST_COLOR) for n in CAST])
    for name, colour in sorted(ordered, key=lambda item: -len(item[0])):
        for match in re.finditer(rf"\b{re.escape(name)}(?:'s)?\b", text):
            start, end = match.span()
            if any(i in taken for i in range(start, end)):
                continue
            taken.update(range(start, end))
            spans.append((start, end, colour))
    return sorted(spans)


def restyle(path: Path, font_uri: str) -> tuple[dict, dict, dict[str, int], int]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    before = fingerprint(doc)
    texts = {t["id"]: t for t in doc.get("materials", {}).get("texts", [])}
    ids = track_material_ids(doc)
    counts = {"REVIEW_NARRATION": 0, "MOVIE_DIALOGUE": 0}
    highlights = 0

    for material_id in ids.get("REVIEW_NARRATION", []):
        text = texts.get(material_id)
        if text is None:
            continue
        text.update(NARRATION_STYLE)
        text["font_path"] = font_uri
        inner = json.loads(text["content"])
        body = inner.get("text", "")
        base = dict(inner["styles"][0])
        base["range"] = [0, len(body)]
        if "font" in base:
            base["font"] = {**base["font"], "path": font_uri, "id": ""}
        base["fill"] = {"alpha": 1.0, "content": {"render_type": "solid",
                        "solid": {"alpha": 1.0, "color": hex_to_rgb(NARRATION_STYLE["text_color"])}}}
        base["size"] = NARRATION_STYLE["font_size"]
        styles = [base]
        for start, end, colour in name_spans(body):
            accent = dict(base)
            accent["range"] = [start, end]
            accent["fill"] = {"alpha": 1.0, "content": {"render_type": "solid",
                              "solid": {"alpha": 1.0, "color": hex_to_rgb(colour)}}}
            styles.append(accent)
            highlights += 1
        inner["styles"] = styles
        text["content"] = json.dumps(inner, ensure_ascii=False)
        counts["REVIEW_NARRATION"] += 1

    for material_id in ids.get("MOVIE_DIALOGUE", []):
        text = texts.get(material_id)
        if text is None:
            continue
        text.update(DIALOGUE_STYLE)
        inner = json.loads(text["content"])
        for style in inner.get("styles", []):
            style["size"] = DIALOGUE_STYLE["font_size"]
            style["fill"] = {"alpha": 1.0, "content": {"render_type": "solid",
                             "solid": {"alpha": 1.0,
                                       "color": hex_to_rgb(DIALOGUE_STYLE["text_color"])}}}
        text["content"] = json.dumps(inner, ensure_ascii=False)
        counts["MOVIE_DIALOGUE"] += 1

    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    return before, fingerprint(doc), counts, highlights


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    args = parser.parse_args()

    if not SERIF_PATH.is_file():
        raise FileNotFoundError(f"Cormorant Garamond not installed at {SERIF_PATH}")
    font_uri = str(SERIF_PATH).replace("\\", "/")

    project = args.project
    if not project.is_dir():
        raise FileNotFoundError(f"CapCut project not found: {project}")

    temp_dir: Path | None = None
    if args.dry_run:
        temp_dir = Path(tempfile.mkdtemp(prefix="capcut_caption_dryrun_"))
        project = temp_dir / project.name
        shutil.copytree(args.project, project, ignore=shutil.ignore_patterns("assets"))
        print(f"dry run against a copy: {project}")
    elif capcut_running():
        print("CapCut is running. Close it completely and re-run.", file=sys.stderr)
        return 2

    backup: Path | None = None
    if not args.dry_run:
        backup = BACKUP_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(project, backup, ignore=shutil.ignore_patterns("assets"))
        print(f"backup: {backup}")

    reports = []
    for mirror in mirrors(project):
        before, after, counts, highlights = restyle(mirror, font_uri)
        preserved = {k: before[k] == after[k] for k in before}
        if not all(preserved.values()):
            broken = [k for k, ok in preserved.items() if not ok]
            raise RuntimeError(f"{mirror} changed more than caption styling: {broken}")
        if counts != EXPECTED:
            raise RuntimeError(f"{mirror}: restyled {counts}, expected {EXPECTED}")
        reports.append({"file": str(mirror), "restyled": counts,
                        "name_highlights": highlights, "sha256": sha256(mirror)})

    hashes = {r["sha256"] for r in reports}
    if len(hashes) != 1:
        raise RuntimeError("Mirror documents diverged")

    doc = json.loads(mirrors(project)[0].read_text(encoding="utf-8"))
    texts = {t["id"]: t for t in doc["materials"]["texts"]}
    highlighted: dict[str, int] = {}
    for material_id in track_material_ids(doc)["REVIEW_NARRATION"]:
        text = texts[material_id]
        blob = text["content"] + str(text.get("font_path")) + str(text.get("font_resource_id"))
        if "Rubik" in blob or "7148699606082130433" in blob:
            raise RuntimeError(f"a Rubik reference survived on {material_id}")
        if text.get("background_alpha") != 0.0:
            raise RuntimeError(f"background box still set on {material_id}")
        body = json.loads(text["content"])["text"]
        for _, _, colour in name_spans(body):
            highlighted[colour] = highlighted.get(colour, 0) + 1

    qa = {
        "status": "pass",
        "dry_run": args.dry_run,
        "project": str(args.project),
        "backup": str(backup) if backup else None,
        "tiers": {
            "dialogue": {"track": "MOVIE_DIALOGUE", "font": "Pretendard Medium",
                         **DIALOGUE_STYLE},
            "narration": {"track": "REVIEW_NARRATION", "font_file": str(SERIF_PATH),
                          **NARRATION_STYLE},
            "characters": {"cast_colour": CAST_COLOR, "cast": CAST,
                           "antagonist_colour": ANTAGONIST_COLOR,
                           "antagonists": ANTAGONISTS,
                           "highlights_applied": highlighted,
                           "excluded_proper_nouns": ["Hell", "Heaven", "Los Angeles",
                                                     "Mexico", "GPS"]},
        },
        "defects_fixed": [
            "narration font references resolved to cached Rubik-Bold.ttf despite "
            "font_name saying Cormorant Garamond",
            "narration background_alpha was 1.0, a solid black box",
        ],
        "restyled": reports[0]["restyled"],
        "mirror_files_updated": len(reports),
        "mirror_hashes_match": len(hashes) == 1,
        "preserved": "timeranges, positions, text strings, animation refs, media paths",
    }
    if not args.dry_run:
        QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": qa["status"], "dry_run": args.dry_run,
                      "restyled": qa["restyled"],
                      "highlights": highlighted,
                      "mirror_hashes_match": qa["mirror_hashes_match"]},
                     ensure_ascii=False, indent=2))
    if temp_dir is not None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("dry-run copy discarded; the live project was not touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
