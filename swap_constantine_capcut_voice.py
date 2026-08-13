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
BACKUP_ROOT = REVIEW / "backups" / "capcut_selected_voice"
QA_PATH = REVIEW / "output" / "CAPCUT_SELECTED_VOICE_SWAP_QA.json"

DEFAULT_PROJECT = (
    Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects"
    / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"
)
MIRROR_NAMES = {"draft_content.json", "template-2.tmp"}
# CapCut names audio materials with `name` and video materials with `material_name`.
# Writing `name` onto a video looked fine until CapCut re-saved the project and dropped
# the key it does not recognise, leaving the old name beside a new path.
NAME_FIELD = {"audios": "name", "videos": "material_name"}

# Both assets are replaced by same-duration equivalents, so only name/path move.
# The bed carries the movie audio ducked against the narration: keeping the Nayva
# bed would hold the movie down past the end of the shorter approved-voice lines.
SWAPS = [
    {
        "kind": "audios",
        "asset_dir": ("assets", "audio"),
        "old": "constantine_nayva_voice_stem.m4a",
        "new": "constantine_selected_voice_stem.m4a",
        "source": REVIEW / "output" / "constantine_selected_voice_stem.m4a",
    },
    {
        "kind": "videos",
        "asset_dir": ("assets", "video"),
        "old": "constantine_story_review_v5_ducked_bed_v2.mp4",
        "new": "constantine_story_review_v5_selected_voice_bed.mp4",
        "source": REVIEW / "output" / "constantine_story_review_v5_selected_voice_bed.mp4",
    },
]


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


def video_size(path: Path) -> tuple[int, int] | None:
    """Pixel dimensions, or None when the file carries no video stream."""
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        text=True, encoding="utf-8",
    ).strip()
    if not raw or "x" not in raw:
        return None
    width, height = raw.split("x")[:2]
    return int(width), int(height)


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
    video_segments = []
    for track in doc.get("tracks", []):
        if track.get("type") != "video":
            continue
        for seg in track["segments"]:
            video_segments.append({
                "source": seg["source_timerange"],
                "target": seg["target_timerange"],
            })
    return {
        "duration": doc.get("duration"),
        "audio_material_count": len(doc.get("materials", {}).get("audios", [])),
        "audio_material_durations": sorted(
            a["duration"] for a in doc.get("materials", {}).get("audios", [])
        ),
        "video_material_count": len(doc.get("materials", {}).get("videos", [])),
        # Durations must hold; width/height are deliberately excluded because swapping in
        # the 1080p bed changes them, and the swap rewrites them from the new file.
        "video_material_durations": sorted(
            v.get("duration") for v in doc.get("materials", {}).get("videos", [])
        ),
        "video_segments": video_segments,
        "audio_segments": audio_segments,
        "text_count": len(texts),
        "texts": texts,
        "text_segments": text_segments,
        "track_count": len(doc.get("tracks", [])),
    }


def swap_document(path: Path, project: Path) -> tuple[dict, dict, dict[str, int]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    before = fingerprint(doc)
    changed: dict[str, int] = {}
    for swap in SWAPS:
        target_dir = project.joinpath(*swap["asset_dir"])
        items = doc.get("materials", {}).get(swap["kind"], [])
        size = video_size(swap["source"]) if swap["kind"] == "videos" else None
        field = NAME_FIELD[swap["kind"]]

        def labels(item: dict) -> set[str]:
            return {
                str(item.get(field, "")),
                Path(str(item.get("path", ""))).name,
            }

        hits = 0
        for item in items:
            if swap["old"] in labels(item) or swap["new"] in labels(item):
                item[field] = swap["new"]
                item["path"] = str(target_dir / swap["new"])
                if size is not None:
                    # The 1080p bed replaces a 540p one; CapCut mis-scales if these
                    # stay at the old dimensions.
                    item["width"], item["height"] = size
                hits += 1
        if hits != 1:
            raise RuntimeError(
                f"{path}: expected exactly 1 {swap['kind']} material matching "
                f"'{swap['old']}' or '{swap['new']}', found {hits}"
            )
        elif hits != 1:
            raise RuntimeError(
                f"Expected exactly 1 '{swap['old']}' in {swap['kind']} of {path}, found {hits}"
            )
        changed[swap["old"]] = hits
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

    absent = [str(s["source"]) for s in SWAPS if not s["source"].exists()]
    if absent:
        raise FileNotFoundError(
            "Run mix_constantine_selected_voice.py first; missing: " + ", ".join(absent)
        )
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

    backup: Path | None = None
    if not args.dry_run:
        backup = BACKUP_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Skip assets/: they are hundreds of MB and every one of them is a copy of a
        # file in output/. Only the project documents are needed to roll the swap back.
        shutil.copytree(project, backup, ignore=shutil.ignore_patterns("assets"))
        size_mb = sum(f.stat().st_size for f in backup.rglob("*") if f.is_file()) / 1048576
        print(f"backup: {backup} ({size_mb:.1f} MB, assets excluded)")

    assets: list[dict] = []
    removed_old: list[str] = []
    for swap in SWAPS:
        target_dir = project.joinpath(*swap["asset_dir"])
        target_dir.mkdir(parents=True, exist_ok=True)
        new_asset = target_dir / swap["new"]
        shutil.copy2(swap["source"], new_asset)
        old_asset = target_dir / swap["old"]
        old_us = media_duration_us(old_asset) if old_asset.exists() else None
        new_us = media_duration_us(new_asset)
        if old_us is not None and old_us != new_us:
            raise RuntimeError(
                f"{swap['new']} runs {new_us} us but {swap['old']} runs {old_us} us. "
                "The recorded timeranges would no longer be valid; abort."
            )
        size = video_size(new_asset) if swap["kind"] == "videos" else None
        assets.append({
            "kind": swap["kind"],
            "from": swap["old"],
            "to": swap["new"],
            "resolution": f"{size[0]}x{size[1]}" if size else None,
            "duration_us": new_us,
            "old_asset_present": old_us is not None,
            # None means the old asset was already gone from a previous run, so
            # there was nothing left to compare against here.
            "duration_matched_old": None if old_us is None else old_us == new_us,
        })
        if old_asset.exists() and not args.keep_old_asset:
            old_asset.unlink()
            removed_old.append(swap["old"])

    reports = []
    for mirror in mirrors(project):
        before, after, changed = swap_document(mirror, project)
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

    # Re-read one mirror and confirm every reference now resolves to a file on disk.
    doc = json.loads(mirrors(project)[0].read_text(encoding="utf-8"))
    referenced: list[str] = []
    for kind in ("audios", "videos"):
        for item in doc["materials"].get(kind, []):
            path = str(item.get("path", ""))
            if not path:
                continue
            referenced.append(Path(path).name)
            if not Path(path).exists():
                raise RuntimeError(f"Project references a missing file: {path}")
    for swap in SWAPS:
        if swap["old"] in referenced:
            raise RuntimeError(f"A reference to {swap['old']} survived the swap")
        if swap["new"] not in referenced:
            raise RuntimeError(f"{swap['new']} is not referenced after the swap")
        # The display name has to agree with the path, in the field CapCut actually reads.
        field = NAME_FIELD[swap["kind"]]
        names = [str(item.get(field, "")) for item in doc["materials"].get(swap["kind"], [])]
        if swap["old"] in names:
            raise RuntimeError(f"{field} still reads {swap['old']}")
        if swap["new"] not in names:
            raise RuntimeError(f"{field} was not set to {swap['new']}; got {names}")

    qa = {
        "status": "pass",
        "dry_run": args.dry_run,
        "project": str(args.project),
        "backup": str(backup) if backup else None,
        "assets_replaced": assets,
        "old_assets_removed": removed_old,
        "capcut_recorded_durations_untouched": True,
        "referenced_assets": sorted(referenced),
        "mirror_files_updated": len(reports),
        "mirror_hashes_match": len(hashes) == 1,
        "reports": reports,
    }
    if not args.dry_run:
        QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {k: qa[k] for k in
         ("status", "dry_run", "assets_replaced", "old_assets_removed",
          "referenced_assets", "mirror_files_updated", "mirror_hashes_match")},
        ensure_ascii=False, indent=2,
    ))
    if temp_dir is not None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("dry-run copy discarded; the live project was not touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
