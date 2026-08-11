from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from pipeline import media_duration, parse_srt

WORKSPACE = Path(r"C:\cineyoutube")
REVIEW_ROOT = Path(os.environ.get("CAPCUT_REVIEW_ROOT", WORKSPACE / "Constantine" / "pro_review"))
OUTPUT = REVIEW_ROOT / "output"
VIDEO = OUTPUT / os.environ.get("CAPCUT_VIDEO_NAME", "constantine_flow_review_v2.mp4")
MOVIE_SRT = OUTPUT / "movie_captions.srt"
NARRATION_SRT = OUTPUT / "narration.srt"
CAPCUT_ROOT = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
SOURCE_NAME = "CONSTANTINE_YOUTUBE_READY"
PROJECT_NAME = os.environ.get("CAPCUT_PROJECT_NAME", "CONSTANTINE_FLOW_REVIEW_V2")


def uid() -> str:
    return str(uuid.uuid4()).upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def validate_story_gate() -> None:
    config_path = REVIEW_ROOT / "config.json"
    if not config_path.exists():
        return
    config = load(config_path)
    if not config.get("require_story_map", False):
        return
    story_map = REVIEW_ROOT / str(config.get("story_map", ""))
    if not config.get("story_map") or not story_map.exists():
        raise FileNotFoundError(f"CapCut 생성 전 스토리맵을 찾을 수 없습니다: {story_map}")
    validator = Path.home() / ".codex" / "skills" / "edit-movie-review" / "scripts" / "validate_story_map.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(story_map), "--require-render-ready"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("CapCut 생성 차단: " + (result.stderr.strip() or result.stdout.strip()))


def clone_text_track(content: dict, track_index: int, cues, project_id: str, *, name: str) -> tuple[dict, list[dict]]:
    source_track = content["tracks"][track_index]
    source_segment = source_track["segments"][0]
    source_material_id = source_segment["material_id"]
    source_material = next(item for item in content["materials"]["texts"] if item["id"] == source_material_id)
    track = copy.deepcopy(source_track)
    track["id"] = uid()
    track["name"] = name
    track["segments"] = []
    materials = []
    for cue in cues:
        material = copy.deepcopy(source_material)
        material_id = uid()
        text = cue.text.strip()
        payload = json.loads(material["content"])
        payload["text"] = text
        for style in payload.get("styles", []):
            style["range"] = [0, len(text) * 2]
        material.update({
            "id": material_id,
            "recognize_text": text,
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            "group_id": project_id,
        })
        materials.append(material)

        segment = copy.deepcopy(source_segment)
        segment.update({
            "id": uid(),
            "raw_segment_id": uid(),
            "material_id": material_id,
            "target_timerange": {
                "start": round(cue.start * 1_000_000),
                "duration": max(200_000, round((cue.end - cue.start) * 1_000_000)),
            },
            "group_id": "",
        })
        track["segments"].append(segment)
    return track, materials


def rewrite_content(source_content: dict, project_id: str, folder: Path, asset: Path, duration_us: int) -> dict:
    content = copy.deepcopy(source_content)
    now = time.time_ns() // 1000
    content.update({
        "id": project_id,
        "duration": duration_us,
        "create_time": now,
        "update_time": now,
        "fps": 24.0,
        "path": folder.as_posix(),
    })
    video_track = copy.deepcopy(source_content["tracks"][0])
    video_track["id"] = uid()
    video_segment = video_track["segments"][0]
    video_segment["id"] = uid()
    video_segment["raw_segment_id"] = uid()
    video_segment["source_timerange"] = {"start": 0, "duration": duration_us}
    video_segment["target_timerange"] = {"start": 0, "duration": duration_us}

    video_material = copy.deepcopy(source_content["materials"]["videos"][0])
    video_material.update({
        "path": str(asset),
        "media_path": "",
        "duration": duration_us,
        "width": 960,
        "height": 540,
        "material_name": VIDEO.name,
        "name": VIDEO.stem,
    })
    movie_track, movie_materials = clone_text_track(source_content, 1, parse_srt(MOVIE_SRT), project_id, name="MOVIE_DIALOGUE")
    narration_track, narration_materials = clone_text_track(source_content, 2, parse_srt(NARRATION_SRT), project_id, name="REVIEW_NARRATION")
    content["tracks"] = [video_track, movie_track, narration_track]
    content["materials"]["videos"] = [video_material]
    content["materials"]["texts"] = movie_materials + narration_materials
    return content


def build() -> Path:
    validate_story_gate()
    if not all(path.exists() for path in (VIDEO, MOVIE_SRT, NARRATION_SRT)):
        raise FileNotFoundError("검토 영상 또는 자막 파일이 없습니다.")
    source = CAPCUT_ROOT / SOURCE_NAME
    target = CAPCUT_ROOT / PROJECT_NAME
    if target.exists():
        raise FileExistsError(f"이미 존재합니다: {target}")
    source_content = load(source / "draft_content.json")
    old_id = source_content["id"]
    project_id = uid()

    shutil.copytree(source, target, ignore=shutil.ignore_patterns("assets"))
    old_timeline = target / "Timelines" / old_id
    new_timeline = target / "Timelines" / project_id
    if old_timeline.exists():
        old_timeline.rename(new_timeline)
    asset_dir = target / "assets" / "video"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset = asset_dir / VIDEO.name
    try:
        os.link(VIDEO, asset)
    except OSError:
        shutil.copy2(VIDEO, asset)
    duration_us = round(media_duration(VIDEO) * 1_000_000)

    # Replace identity/path references throughout small JSON mirror files.
    old_folder = str(source)
    for path in target.rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        raw = raw.replace(old_id, project_id).replace(old_id.upper(), project_id)
        raw = raw.replace(old_folder, str(target)).replace(SOURCE_NAME, PROJECT_NAME)
        path.write_text(raw, encoding="utf-8")

    content = rewrite_content(source_content, project_id, target, asset, duration_us)
    track_counts = {track.get("name", ""): len(track.get("segments", [])) for track in content["tracks"]}
    expected_movie = len(parse_srt(MOVIE_SRT))
    expected_narration = len(parse_srt(NARRATION_SRT))
    if track_counts.get("MOVIE_DIALOGUE") != expected_movie or track_counts.get("REVIEW_NARRATION") != expected_narration:
        raise ValueError(
            "CapCut 자막 트랙 수 불일치: "
            f"movie={track_counts.get('MOVIE_DIALOGUE')}/{expected_movie}, "
            f"narration={track_counts.get('REVIEW_NARRATION')}/{expected_narration}"
        )
    content_paths = [target / "draft_content.json", target / "draft_content.json.bak"]
    if new_timeline.exists():
        content_paths += [new_timeline / "draft_content.json", new_timeline / "draft_content.json.bak"]
    for path in content_paths:
        save(path, content)

    now = time.time_ns() // 1000
    meta_path = target / "draft_meta_info.json"
    meta = load(meta_path)
    meta.update({
        "draft_fold_path": target.as_posix(),
        "draft_id": project_id,
        "draft_name": PROJECT_NAME,
        "draft_root_path": str(CAPCUT_ROOT),
        "draft_need_rename_folder": False,
        "draft_timeline_materials_size_": VIDEO.stat().st_size,
        "tm_draft_create": now,
        "tm_draft_modified": now,
        "tm_duration": duration_us,
    })
    save(meta_path, meta)
    if (target / "draft_meta_info.json.bak").exists():
        save(target / "draft_meta_info.json.bak", meta)

    root_meta_path = CAPCUT_ROOT / "root_meta_info.json"
    root_meta = load(root_meta_path)
    backup_dir = REVIEW_ROOT / "backups" / "capcut"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root_meta_path, backup_dir / f"root_meta_info-before-flow-{now}.json")
    template_entry = next(item for item in root_meta["all_draft_store"] if item["draft_name"] == SOURCE_NAME)
    entry = copy.deepcopy(template_entry)
    entry.update({
        "draft_cover": (target / "draft_cover.jpg").as_posix(),
        "draft_fold_path": target.as_posix(),
        "draft_id": project_id,
        "draft_json_file": (target / "draft_content.json").as_posix(),
        "draft_name": PROJECT_NAME,
        "draft_root_path": str(CAPCUT_ROOT),
        "draft_timeline_materials_size": VIDEO.stat().st_size,
        "tm_draft_create": now,
        "tm_draft_modified": now,
        "tm_duration": duration_us,
    })
    root_meta["all_draft_store"].insert(0, entry)
    root_meta["draft_ids"] = len(root_meta["all_draft_store"])
    temp = root_meta_path.with_suffix(".json.flow_tmp")
    save(temp, root_meta)
    os.replace(temp, root_meta_path)
    return target


if __name__ == "__main__":
    try:
        print(build())
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
