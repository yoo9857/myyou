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


def fit_font_size(materials: list[dict], frame: tuple[int, int], max_lines: int = 2) -> float | None:
    """Find the largest size at which no caption on this track needs a third line.

    The sizes carried over were set against Korean, which is compact; the same numbers on
    English put 25 of 49 narration captions onto three lines. Rather than pick a new number
    by eye, each caption's width is measured against the font CapCut will actually render it
    with, and the size is the largest one that keeps every line within the box.

    CapCut states font_size as a percentage of frame height, and line_max_width as a
    fraction of frame width, so both resolve to pixels here.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    first = materials[0]
    style = (json.loads(first["content"]).get("styles") or [{}])[0]
    font_path = Path(str(style.get("font", {}).get("path") or first.get("font_path", "")))
    if not font_path.exists():
        return None
    font = TTFont(str(font_path), fontNumber=0)
    units = font["head"].unitsPerEm
    cmap, metrics = font.getBestCmap(), font["hmtx"]

    def em_width(text: str) -> float:
        return sum(metrics[cmap[ord(c)]][0] if ord(c) in cmap else units / 2
                   for c in text) / units

    width, height = frame
    box = width * float(first.get("line_max_width", 0.78))
    widths = [em_width(json.loads(m["content"])["text"]) for m in materials]
    current = float(first.get("font_size", 7.0))
    size = current
    while size > 3.0:
        em = size / 100 * height
        if all(-(-w * em // box) <= max_lines for w in widths):
            return round(size, 2)
        size -= 0.1
    return None


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
    # The .bak files come along: CapCut reads them when the primary document fails to parse,
    # and a draft carrying a backup of somebody else's project is a trap either way, so they
    # are overwritten with this project's content below along with everything else.
    shutil.copytree(template_dir, target,
                    ignore=shutil.ignore_patterns(".capcut-cli-history"))

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
    fitted = {}
    for label, (made, _) in written.items():
        size = fit_font_size(made, (width, height))
        if size is not None and size < float(made[0].get("font_size", 7.0)):
            for material in made:
                material["font_size"] = size
                content = json.loads(material["content"])
                for style in content.get("styles", []):
                    style["size"] = size
                material["content"] = json.dumps(content, ensure_ascii=False)
            fitted[label] = size
        materials["texts"].extend(made)

    source["duration"] = total
    source["canvas_config"].update({"width": width, "height": height})
    # The document's id is the timeline's id: it names the Timelines/<id>/ folder the mirror
    # copies live in. Issuing a fresh one left the folder pointing at a timeline that no
    # longer existed, and CapCut listed the project but would not open it.

    payload = json.dumps(source, ensure_ascii=False)
    mirrors = [p for p in target.rglob("*")
               if p.is_file() and (p.name in MIRRORS
                                   or p.name in {f"{m}.bak" for m in MIRRORS})]
    for mirror in mirrors:
        mirror.write_text(payload, encoding="utf-8")

    meta_path = target / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    draft_id = new_id()
    meta["draft_name"] = name
    meta["draft_id"] = draft_id
    meta["tm_duration"] = total
    # CapCut writes these with forward slashes and leaves the storage-device field empty on a
    # local draft. Backslashes and a drive letter are what it does for removable media, and a
    # draft that claims to live on one it cannot find does not open.
    meta["draft_fold_path"] = target.as_posix()
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

    # CapCut lists projects from this index, not from what is on disk, so a draft that is not
    # registered here simply does not appear - the folder existing is not enough.
    index_path = DRAFTS / "root_meta_info.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = [e for e in index.get("all_draft_store", [])
               if e.get("draft_name") != name and e.get("draft_fold_path") != target.as_posix()]
    donor = next((e for e in index["all_draft_store"]
                  if e.get("draft_name") == args.template), index["all_draft_store"][0])
    entry = json.loads(json.dumps(donor))
    entry.update({
        "draft_name": name,
        "draft_id": draft_id,
        "draft_fold_path": target.as_posix(),
        "draft_json_file": f"{target.as_posix()}\\draft_content.json",
        "draft_cover": f"{target.as_posix()}\\draft_cover.jpg",
        "tm_duration": total,
        "tm_draft_modified": meta.get("tm_draft_modified", 0),
        "tm_draft_create": meta.get("tm_draft_create", 0),
    })
    # Only all_draft_store is ours to touch. draft_ids is an integer CapCut keeps for its own
    # bookkeeping - writing a list of ids there, which is what the name suggests, is how the
    # index stopped parsing and the project stopped appearing.
    index["all_draft_store"] = [entry] + entries
    index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    print(f"  프로젝트: {name}")
    print(f"  목록 등록: {len(index['all_draft_store'])}개 중 첫 번째")
    print(f"  영상 {asset.name}  {width}x{height}  {duration/60:.2f}분")
    for label, (_, count) in written.items():
        note = f", 글자 크기 {fitted[label]}로 축소 (3줄 방지)" if label in fitted else ""
        print(f"  {label:16} 자막 {count}개{note}")
    print(f"  미러 파일 {len(mirrors)}개 동일 기록")
    print(f"  위치: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
