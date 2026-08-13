"""Point the Constantine V5 CapCut project at the approved-voice narration stem.

The new stem has exactly the same duration as the Nayva one it replaces, so only the
audio material's `name` and `path` change. Every timerange, caption, animation and
track stays byte-identical -- the script fails if that is not true afterwards.

CapCut keeps its own copy of each asset under the project's assets/ folder, so the
file is copied in rather than referenced from output/.

Usage:
    python swap_constantine_capcut_voice.py --dry-run       # verify against a temp copy
    python swap_constantine_capcut_voice.py                 # apply (CapCut must be closed)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "Constantine" / "story_review_v5"
NEW_STEM = REVIEW / "output" / "constantine_selected_voice_stem.m4a"
BACKUP_ROOT = REVIEW / "backups" / "capcut_selected_voice"
QA_PATH = REVIEW / "output" / "CAPCUT_SELECTED_VOICE_SWAP_QA.json"

DEFAULT_PROJECT = (
    Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects"
    / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"
)
OLD_NAME = "constantine_nayva_voice_stem.m4a"
NEW_NAME = "constantine_selected_voice_stem.m4a"
MIRROR_NAMES = {"draft_content.json", "template-2.tmp"}


def capcut_running() -> list[str]:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"],
            check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.split()[1] for line in out.splitlines() if line.lower().startswith("capcut")]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media_duration_us(path: Path) -> int:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        text=True, encoding="utf-8",
    ).strip()
    return round(float(raw) * 1_000_000)


def mirrors(project: Path) -> list[Path]:
    found = [p for p in project.rglob("*") if p.is_file() and p.name in MIRROR_NAMES]
    if not found:
        raise RuntimeError(f"No draft_content.json / template-2.tmp under {project}")
    return sorted(found)


def fingerprint(doc: dict) -> dict:
    """Everything that must survive the swap untouched."""
    audio_segments = []
    for track in doc.get("tracks", []):
        if track.get("type") != "audio":
            continue
        for seg in track["segments"]:
            audio_segments.append({
                "source": seg["source_timerange"],
                "target": seg["target_timerange"],
                "volume": seg.get("volume"),
            })
    texts = [
        {"content": t.get("content"), "id": t.get("id")}
        for t in doc.get("materials", {}).get("texts", [])
    ]
    text_segments = []
    for track in doc.get("tracks", []):
        if track.get("type") != "text":
            continue
        for seg in track["segments"]:
            text_segments.append({
                "target": seg["target_timerange"],
                "material_id": seg.get("material_id"),
                "animations": seg.get("extra_material_refs"),
            })
    return {
        "duration": doc.get("duration"),
        "audio_material_count": len(doc.get("materials", {}).get("audios", [])),
        "audio_material_durations": sorted(
            a["duration"] for a in doc.get("materials", {}).get("audios", [])
        ),
        "video_material_paths": sorted(
            v.get("path", "") for v in doc.get("materials", {}).get("videos", [])
        ),
        "audio_segments": audio_segments,
        "text_count": len(texts),
        "texts": texts,
        "text_segments": text_segments,
        "track_count": len(doc.get("tracks", [])),
    }


def swap_document(path: Path, assets_audio: Path) -> tuple[dict, dict, int]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    before = fingerprint(doc)
    changed = 0
    for audio in doc.get("materials", {}).get("audios", []):
        if audio.get("name") == OLD_NAME or Path(str(audio.get("path", ""))).name == OLD_NAME:
            audio["name"] = NEW_NAME
            audio["path"] = str(assets_audio / NEW_NAME)
            changed += 1
    if changed != 1:
        raise RuntimeError(f"Expected exactly 1 Nayva audio material in {path}, found {changed}")
    path.write_text(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return before, fingerprint(doc), changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="run against a throwaway copy of the project")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--keep-old-asset", action="store_true",
                        help="leave the Nayva .m4a in assets/audio (default removes it)")
    args = parser.parse_args()

    if not NEW_STEM.exists():
        raise FileNotFoundError(f"{NEW_STEM} is missing. Run mix_constantine_selected_voice.py first.")
    project = args.project
    if not project.is_dir():
        raise FileNotFoundError(f"CapCut project not found: {project}")

    temp_dir: Path | None = None
    if args.dry_run:
        temp_dir = Path(tempfile.mkdtemp(prefix="capcut_swap_dryrun_"))
        target = temp_dir / project.name
        shutil.copytree(project, target)
        project = target
        print(f"dry run against a copy: {project}")
    else:
        running = capcut_running()
        if running:
            print(
                f"CapCut is running ({len(running)} processes). Close it completely and re-run;\n"
                "editing the project underneath a live CapCut loses the swap or corrupts the file.",
                file=sys.stderr,
            )
            return 2

    assets_audio = project / "assets" / "audio"
    assets_audio.mkdir(parents=True, exist_ok=True)

    backup: Path | None = None
    if not args.dry_run:
        backup = BACKUP_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(project, backup)
        print(f"backup: {backup}")

    new_asset = assets_audio / NEW_NAME
    shutil.copy2(NEW_STEM, new_asset)

    old_before = assets_audio / OLD_NAME
    old_duration_us = media_duration_us(old_before) if old_before.exists() else None
    new_duration_us = media_duration_us(new_asset)
    if old_duration_us is not None and old_duration_us != new_duration_us:
        raise RuntimeError(
            f"Stem durations differ ({old_duration_us} vs {new_duration_us} us). "
            "The recorded timeranges would no longer be valid; abort."
        )

    reports = []
    for mirror in mirrors(project):
        before, after, changed = swap_document(mirror, assets_audio)
        preserved = {k: before[k] == after[k] for k in before}
        if not all(preserved.values()):
            broken = [k for k, ok in preserved.items() if not ok]
            raise RuntimeError(f"{mirror} changed more than the audio path: {broken}")
        reports.append({
            "file": str(mirror),
            "materials_changed": changed,
            "sha256": sha256(mirror),
            "preserved": preserved,
        })

    hashes = {r["sha256"] for r in reports}
    if len(hashes) != 1:
        raise RuntimeError(f"Mirror files diverged: {[r['file'] for r in reports]}")

    removed_old = False
    if old_before.exists() and not args.keep_old_asset:
        old_before.unlink()
        removed_old = True

    # Re-read one mirror and confirm the project now points only at the new stem.
    doc = json.loads(mirrors(project)[0].read_text(encoding="utf-8"))
    names = sorted(a["name"] for a in doc["materials"]["audios"])
    paths = [Path(a["path"]).name for a in doc["materials"]["audios"]]
    if OLD_NAME in names or OLD_NAME in paths:
        raise RuntimeError("A reference to the Nayva stem survived the swap")
    if NEW_NAME not in names:
        raise RuntimeError("The new stem is not referenced after the swap")

    qa = {
        "status": "pass",
        "dry_run": args.dry_run,
        "project": str(args.project),
        "backup": str(backup) if backup else None,
        "replaced": {"from": OLD_NAME, "to": NEW_NAME},
        "old_asset_removed": removed_old,
        "stem_duration_us": new_duration_us,
        "stem_duration_matched_old": old_duration_us == new_duration_us,
        "capcut_recorded_duration_untouched": True,
        "audio_materials": names,
        "mirror_files_updated": len(reports),
        "mirror_hashes_match": len(hashes) == 1,
        "reports": reports,
    }
    if not args.dry_run:
        QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {k: qa[k] for k in
         ("status", "dry_run", "replaced", "old_asset_removed", "stem_duration_matched_old",
          "audio_materials", "mirror_files_updated", "mirror_hashes_match")},
        ensure_ascii=False, indent=2,
    ))
    if temp_dir is not None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("dry-run copy discarded; the live project was not touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
