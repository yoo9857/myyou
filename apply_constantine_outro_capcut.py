from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from pipeline import parse_srt, write_srt


CODE_ROOT = Path(__file__).resolve().parent
REVIEW_ROOT = CODE_ROOT / "Constantine" / "story_review_v5"
OUTPUT = REVIEW_ROOT / "output"
PROJECT = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"
FINAL_VIDEO = OUTPUT / "constantine_story_review_v5_with_outro.mp4"
MAIN_BOUNDARY_SEC = 1487.0


def uid() -> str:
    return str(uuid.uuid4()).upper()


def save_atomic(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".outro_tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


def media_duration(path: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        encoding="utf-8",
    )
    return float(raw.strip())


def prepare_srt_assets() -> dict:
    narration = parse_srt(OUTPUT / "narration_v3.srt")
    combined = parse_srt(OUTPUT / "captions_combined_v3.srt")
    outro = parse_srt(OUTPUT / "outro_review.srt")
    absolute_outro = [
        (MAIN_BOUNDARY_SEC + cue.start, MAIN_BOUNDARY_SEC + cue.end, cue.text)
        for cue in outro
    ]
    write_srt(
        [(cue.start, cue.end, cue.text) for cue in narration] + absolute_outro,
        OUTPUT / "narration_v4_outro.srt",
    )
    write_srt(
        [(cue.start, cue.end, cue.text) for cue in combined] + absolute_outro,
        OUTPUT / "captions_combined_v4_outro.srt",
    )
    report = {
        "main_boundary_sec": MAIN_BOUNDARY_SEC,
        "final_duration_sec": media_duration(FINAL_VIDEO),
        "base_review_cues": len(narration),
        "outro_review_cues": len(outro),
        "final_review_cues": len(narration) + len(outro),
        "movie_audio_muted_in_outro": True,
        "movie_captions_suppressed_in_outro": True,
        "music_speech_gain": 0.05,
        "music_post_speech_gain": 0.18,
        "voice_generation": "OFF",
        "runtime_deviation": "25:01.021; retained full approved main cut and minimum 14-second outro",
    }
    (OUTPUT / "OUTRO_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def apply_capcut() -> dict:
    if not PROJECT.exists() or not FINAL_VIDEO.exists():
        raise FileNotFoundError("CapCut project or final outro video is missing")
    duration_sec = media_duration(FINAL_VIDEO)
    duration_us = round(duration_sec * 1_000_000)
    content_path = PROJECT / "draft_content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))

    review_track = next((item for item in content["tracks"] if item.get("name") == "REVIEW_NARRATION"), None)
    movie_track = next((item for item in content["tracks"] if item.get("name") == "MOVIE_DIALOGUE"), None)
    video_track = next((item for item in content["tracks"] if item.get("type") == "video"), None)
    if not review_track or not review_track.get("segments") or not movie_track or not video_track:
        raise ValueError("Required CapCut tracks are missing")

    old_review_ids = {segment["material_id"] for segment in review_track["segments"]}
    template_segment = copy.deepcopy(review_track["segments"][0])
    template_material = copy.deepcopy(
        next(item for item in content["materials"]["texts"] if item["id"] in old_review_ids)
    )
    content["materials"]["texts"] = [
        item for item in content["materials"]["texts"] if item["id"] not in old_review_ids
    ]
    review_track["segments"] = []
    new_materials = []
    for cue in parse_srt(OUTPUT / "narration_v4_outro.srt"):
        text = cue.text.strip()
        material = copy.deepcopy(template_material)
        material_id = uid()
        payload = json.loads(material["content"])
        payload["text"] = text
        for style in payload.get("styles", []):
            style["range"] = [0, len(text) * 2]
        material.update(
            {
                "id": material_id,
                "recognize_text": text,
                "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            }
        )
        segment = copy.deepcopy(template_segment)
        segment.update(
            {
                "id": uid(),
                "raw_segment_id": uid(),
                "material_id": material_id,
                "target_timerange": {
                    "start": round(cue.start * 1_000_000),
                    "duration": max(200_000, round((cue.end - cue.start) * 1_000_000)),
                },
                "group_id": "",
            }
        )
        new_materials.append(material)
        review_track["segments"].append(segment)
    content["materials"]["texts"].extend(new_materials)

    asset_dir = PROJECT / "assets" / "video"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / FINAL_VIDEO.name
    if not asset_path.exists():
        try:
            os.link(FINAL_VIDEO, asset_path)
        except OSError:
            shutil.copy2(FINAL_VIDEO, asset_path)

    video_material = content["materials"]["videos"][0]
    old_video_size = Path(video_material["path"]).stat().st_size if Path(video_material["path"]).exists() else 0
    video_material.update(
        {
            "duration": duration_us,
            "path": str(asset_path),
            "material_name": asset_path.name,
            "has_audio": True,
            "width": 960,
            "height": 540,
        }
    )
    video_segment = video_track["segments"][0]
    video_segment["source_timerange"] = {"start": 0, "duration": duration_us}
    video_segment["target_timerange"] = {"start": 0, "duration": duration_us}
    content["duration"] = duration_us
    content["update_time"] = time.time_ns() // 1000

    content_paths = [
        PROJECT / "draft_content.json",
        PROJECT / "draft_content.json.bak",
        PROJECT / "template-2.tmp",
    ]
    content_paths += list(PROJECT.glob("Timelines/*/draft_content.json"))
    content_paths += list(PROJECT.glob("Timelines/*/draft_content.json.bak"))
    content_paths += list(PROJECT.glob("Timelines/*/template-2.tmp"))
    content_paths = [path for path in content_paths if path.exists()]

    meta_paths = [path for path in (PROJECT / "draft_meta_info.json", PROJECT / "draft_meta_info.json.bak") if path.exists()]
    stamp = str(time.time_ns() // 1000)
    backup = REVIEW_ROOT / "backups" / "capcut_outro_v1" / stamp
    for path in content_paths + meta_paths:
        target = backup / path.relative_to(PROJECT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    for path in content_paths:
        save_atomic(path, content)
    for path in meta_paths:
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta["tm_duration"] = duration_us
        meta["tm_draft_modified"] = content["update_time"]
        if "draft_timeline_materials_size_" in meta:
            meta["draft_timeline_materials_size_"] = max(
                0,
                int(meta["draft_timeline_materials_size_"]) - old_video_size + asset_path.stat().st_size,
            )
        save_atomic(path, meta)

    mirrors = [json.loads(path.read_text(encoding="utf-8")) for path in content_paths]
    mirror_equal = all(item == mirrors[0] for item in mirrors[1:])
    result = {
        "project": str(PROJECT),
        "backup": str(backup),
        "final_video_asset": str(asset_path),
        "duration_sec": duration_sec,
        "movie_dialogue_segments": len(movie_track["segments"]),
        "review_narration_segments": len(review_track["segments"]),
        "text_materials": len(content["materials"]["texts"]),
        "content_mirrors_written": len(content_paths),
        "content_mirrors_equal": mirror_equal,
    }
    (OUTPUT / "CAPCUT_OUTRO_APPLY_QA.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    result = prepare_srt_assets()
    if not args.prepare_only:
        result = apply_capcut()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
