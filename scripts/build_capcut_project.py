"""Build a CapCut draft for a finished review instead of leaving the editor to assemble it.

Importing an mp4 and two SRTs by hand is fine until the captions need the channel's styling,
at which point every cue has to be restyled inside CapCut. This writes the draft directly:
the master on the video track, the two caption tracks as native CapCut text carrying the
styling the previous review used, and the channel's watermark and name kept as they were.

The structure is not invented. It is cloned from an existing draft that CapCut itself wrote
and has opened since, and only the parts that must differ are replaced - the schema has
dozens of fields whose defaults are undocumented, and a draft CapCut refuses to open is
worth less than no draft at all.

    python scripts/build_capcut_project.py devil/config.json --name THE_DEVIL_ALL_THE_TIME

CapCut must be closed. It holds the draft in memory and rewrites it on exit, dropping keys
it did not put there.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

DRAFTS = Path.home() / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft"
MIRRORS = {"draft_content.json", "template-2.tmp"}
MICRO = 1_000_000


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def micros(seconds: float) -> int:
    return int(round(seconds * MICRO))


def probe(path: Path, entries: str) -> list[str]:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", entries,
         "-of", "default=nw=1:nk=1", str(path)], text=True)
    return out.strip().splitlines()


def text_material(template: dict, cue_text: str) -> dict:
    """Clone a caption's material, keeping its styling and replacing only the words."""
    material = json.loads(json.dumps(template))
    material["id"] = new_id()
    content = json.loads(material["content"])
    content["text"] = cue_text
    # Style ranges are character offsets into the old text; the first one is the caption's
    # own styling, and it has to cover the new string or CapCut renders the tail unstyled.
    styles = content.get("styles") or []
    if styles:
        styles[0]["range"] = [0, len(cue_text)]
        content["styles"] = styles[:1]
    material["content"] = json.dumps(content, ensure_ascii=False)
    material["recognize_text"] = cue_text
    return material


def text_segment(template: dict, material_id: str, start: float, end: float) -> dict:
    segment = json.loads(json.dumps(template))
    segment["id"] = new_id()
    segment["raw_segment_id"] = new_id()
    segment["material_id"] = material_id
    segment["target_timerange"] = {"start": micros(start), "duration": micros(end - start)}
    return segment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--name", default=None, help="Draft folder name shown in CapCut.")
    parser.add_argument("--template", default="CONSTANTINE_STORY_REVIEW_V5")
    args = parser.parse_args()

    import pipeline

    if subprocess.run(["powershell", "-NoProfile", "-Command",
                       "if (Get-Process CapCut -ErrorAction SilentlyContinue) { exit 1 }"],
                      capture_output=True).returncode == 1:
        raise SystemExit("CapCut이 실행 중입니다. 닫고 다시 실행하십시오.")

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    package = root / "output" / "capcut_import"
    master = root / "output" / str(config.get("output_video", "rough_cut.mp4"))
    if not master.exists():
        raise SystemExit(f"최종본이 없습니다: {master}")

    template_dir = DRAFTS / args.template
    if not template_dir.exists():
        raise SystemExit(f"기준 프로젝트가 없습니다: {template_dir}")
    name = args.name or re.sub(r"[^A-Za-z0-9_]+", "_",
                               str(config.get("project_title", "REVIEW"))).strip("_").upper()
    target = DRAFTS / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(template_dir, target,
                    ignore=shutil.ignore_patterns(".capcut-cli-history", "*.bak"))

    # CapCut keeps private copies of every asset inside the draft, so the review is copied in
    # rather than referenced where it sits.
    video_assets = target / "assets" / "video"
    for stale in video_assets.glob("*"):
        if stale.name != "Vera_Lindqvist_icon_05.png":
            stale.unlink()
    shutil.rmtree(target / "assets" / "audio", ignore_errors=True)
    asset = video_assets / master.name
    shutil.copy2(master, asset)

    duration = float(probe(master, "format=duration")[0])
    total = micros(duration)
    width, height = (int(v) for v in probe(master, "stream=width,height")[:2])

    source = json.loads((target / "draft_content.json").read_text(encoding="utf-8"))
    materials = source["materials"]

    video_material = materials["videos"][0]
    video_material.update({
        "path": str(asset), "material_name": asset.name, "duration": total,
        "width": width, "height": height,
    })
    # The stems belong to the previous review, and this master already carries its narration
    # and its effects. Leaving them in would play someone else's voice over this film.
    materials["audios"] = []
    source["tracks"] = [t for t in source["tracks"] if t["type"] != "audio"]

    for track in source["tracks"]:
        for segment in track["segments"]:
            if track["type"] == "video":
                segment["target_timerange"] = {"start": 0, "duration": total}
                if segment["material_id"] == video_material["id"]:
                    segment["source_timerange"] = {"start": 0, "duration": total}

    caption_tracks = {"MOVIE_DIALOGUE": package / "movie_captions.srt",
                      "REVIEW_NARRATION": package / "narration.srt"}
    keep_texts = []
    for track in source["tracks"]:
        if track["type"] != "text" or track.get("name") not in caption_tracks:
            keep_texts += [s["material_id"] for s in track["segments"]]
    written = {}
    for track in source["tracks"]:
        if track["type"] != "text" or track.get("name") not in caption_tracks:
            continue
        template_segment = track["segments"][0]
        template_id = template_segment["material_id"]
        template_material = next(m for m in materials["texts"] if m["id"] == template_id)
        cues = pipeline.parse_srt(caption_tracks[track["name"]])
        segments, made = [], []
        for cue in cues:
            material = text_material(template_material, cue.text.strip())
            made.append(material)
            segments.append(text_segment(template_segment, material["id"], cue.start, cue.end))
        track["segments"] = segments
        written[track["name"]] = (made, len(cues))

    materials["texts"] = [m for m in materials["texts"] if m["id"] in keep_texts]
    for made, _ in written.values():
        materials["texts"].extend(made)

    source["duration"] = total
    source["canvas_config"].update({"width": width, "height": height})
    source["id"] = new_id()

    payload = json.dumps(source, ensure_ascii=False)
    mirrors = [p for p in target.rglob("*") if p.is_file() and p.name in MIRRORS]
    for mirror in mirrors:
        mirror.write_text(payload, encoding="utf-8")

    meta_path = target / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["draft_name"] = name
    meta["draft_id"] = new_id()
    meta["tm_duration"] = total
    meta["draft_fold_path"] = str(target)
    meta["draft_removable_storage_device"] = str(target.drive)
    for item in meta.get("draft_materials", []):
        for entry in item.get("value", []):
            if str(entry.get("metetype")) == "video" or entry.get("file_Path", "").endswith(".mp4"):
                entry["file_Path"] = str(asset)
                entry["extra_info"] = asset.name
                entry["duration"] = total
                entry["width"], entry["height"] = width, height
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    for extra in target.rglob("draft_meta_info.json"):
        if extra != meta_path:
            extra.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    print(f"  프로젝트: {name}")
    print(f"  영상 {asset.name}  {width}x{height}  {duration/60:.2f}분")
    for label, (_, count) in written.items():
        print(f"  {label:16} 자막 {count}개")
    print(f"  미러 파일 {len(mirrors)}개 동일 기록")
    print(f"  위치: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
