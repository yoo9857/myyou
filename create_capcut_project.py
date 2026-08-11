from __future__ import annotations

import copy
import json
import os
import shutil
import time
import uuid
from pathlib import Path

import pipeline


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
VIDEO = OUTPUT / "rough_cut.mp4"
SUBTITLE = OUTPUT / "captions_combined.srt"
CAPCUT_ROOT = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
TEMPLATE = CAPCUT_ROOT / "0811"
PROJECT_NAME = "COLONY_AUTO_REVIEW"


def uid() -> str:
    return str(uuid.uuid4()).upper()


def unix_us() -> int:
    return time.time_ns() // 1000


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def new_material(template: dict, material_id: str, **updates) -> dict:
    value = copy.deepcopy(template)
    value["id"] = material_id
    value.update(updates)
    return value


def build() -> Path:
    if not VIDEO.exists() or not SUBTITLE.exists():
        raise FileNotFoundError("rough_cut.mp4 또는 captions_combined.srt가 없습니다.")
    if not TEMPLATE.exists():
        raise FileNotFoundError("CapCut 빈 프로젝트 템플릿 0811을 찾을 수 없습니다.")
    if any(CAPCUT_ROOT.glob(f"{PROJECT_NAME}*")):
        raise FileExistsError("COLONY_AUTO_REVIEW 프로젝트가 이미 있습니다. 기존 프로젝트는 덮어쓰지 않습니다.")

    # Read examples only; no existing project is changed.
    blank = load_json(TEMPLATE / "draft_content.json")
    sample = load_json(CAPCUT_ROOT / "0610" / "draft_content.json")
    sample_video_segment = next(t for t in sample["tracks"] if t["type"] == "video" and t["segments"])["segments"][0]
    sample_video_track = next(t for t in sample["tracks"] if t["type"] == "video" and t["segments"])
    sample_text_segment = next(t for t in sample["tracks"] if t["type"] == "text")["segments"][0]
    sample_text_track = next(t for t in sample["tracks"] if t["type"] == "text")
    sample_video = sample["materials"]["videos"][0]
    sample_text = sample["materials"]["texts"][0]

    project_id = uid()
    folder = CAPCUT_ROOT / PROJECT_NAME
    shutil.copytree(TEMPLATE, folder)
    try:
        duration_us = round(pipeline.media_duration(VIDEO) * 1_000_000)
        now = unix_us()
        video_id = uid()
        speed_id, placeholder_id, canvas_id = uid(), uid(), uid()
        animation_id, color_id, sound_id, vocal_id = uid(), uid(), uid(), uid()
        video_path = VIDEO.resolve().as_posix()

        content = copy.deepcopy(blank)
        content.update({
            "id": project_id,
            "name": PROJECT_NAME,
            "duration": duration_us,
            "create_time": now,
            "update_time": now,
            "fps": 30.0,
            "path": folder.as_posix(),
        })

        video_material = copy.deepcopy(sample_video)
        video_material.update({
            "id": video_id,
            "unique_id": "",
            "type": "video",
            "duration": duration_us,
            "path": video_path,
            "media_path": "",
            "has_audio": True,
            "width": 1920,
            "height": 1080,
            "material_name": VIDEO.name,
            "name": VIDEO.stem,
            "category_name": "local",
            "check_flag": 62978047,
        })

        video_segment = copy.deepcopy(sample_video_segment)
        video_segment.update({
            "id": uid(),
            "source_timerange": {"start": 0, "duration": duration_us},
            "target_timerange": {"start": 0, "duration": duration_us},
            "material_id": video_id,
            "extra_material_refs": [speed_id, placeholder_id, canvas_id, animation_id, color_id, sound_id, vocal_id],
            "render_index": 0,
            "track_render_index": 0,
            "volume": 1.0,
            "last_nonzero_volume": 1.0,
        })
        video_track = {k: copy.deepcopy(v) for k, v in sample_video_track.items() if k != "segments"}
        video_track.update({"id": uid(), "type": "video", "flag": 0, "segments": [video_segment]})

        materials = content["materials"]
        for key in materials:
            if isinstance(materials[key], list):
                materials[key] = []
        materials["videos"] = [video_material]
        materials["speeds"] = [new_material(sample["materials"]["speeds"][0], speed_id)]
        materials["placeholder_infos"] = [new_material(sample["materials"]["placeholder_infos"][0], placeholder_id)]
        materials["canvases"] = [new_material(sample["materials"]["canvases"][0], canvas_id)]
        materials["material_animations"] = [new_material(sample["materials"]["material_animations"][0], animation_id)]
        materials["material_colors"] = [new_material(sample["materials"]["material_colors"][0], color_id)]
        materials["sound_channel_mappings"] = [new_material(sample["materials"]["sound_channel_mappings"][0], sound_id)]
        materials["vocal_separations"] = [new_material(sample["materials"]["vocal_separations"][0], vocal_id)]

        text_materials = []
        text_segments = []
        cues = pipeline.parse_srt(SUBTITLE)
        for cue in cues:
            text_id, text_animation_id = uid(), uid()
            text = cue.text.strip()
            text_material = copy.deepcopy(sample_text)
            style_payload = {
                "text": text,
                "styles": [{
                    "fill": {"content": {"render_type": "solid", "solid": {"color": [1, 1, 1]}}},
                    "font": {"path": "C:/Windows/Fonts/malgun.ttf", "id": ""},
                    "size": 5,
                    "useLetterColor": True,
                    "range": [0, len(text)],
                }],
            }
            text_material.update({
                "id": text_id,
                "recognize_task_id": "",
                "recognize_text": text,
                "content": json.dumps(style_payload, ensure_ascii=False, separators=(",", ":")),
                "words": {"start_time": [], "end_time": [], "text": []},
                "current_words": {"start_time": [], "end_time": [], "text": []},
                "font_name": "맑은 고딕",
                "font_title": "맑은 고딕",
                "font_path": "C:/Windows/Fonts/malgun.ttf",
                "font_resource_id": "",
                "fonts": [],
                "text_size": 30,
                "font_size": 5.0,
                "language": "ko-KR",
                "group_id": project_id,
                "line_max_width": 0.82,
                "border_alpha": 1.0,
                "border_color": "#000000",
                "border_width": 0.08,
            })
            text_materials.append(text_material)
            materials["material_animations"].append(
                new_material(sample["materials"]["material_animations"][0], text_animation_id)
            )

            start_us = round(cue.start * 1_000_000)
            cue_duration_us = max(200_000, round((cue.end - cue.start) * 1_000_000))
            text_segment = copy.deepcopy(sample_text_segment)
            text_segment.update({
                "id": uid(),
                "source_timerange": None,
                "target_timerange": {"start": start_us, "duration": cue_duration_us},
                "material_id": text_id,
                "extra_material_refs": [text_animation_id],
                "render_index": 14000,
                "track_render_index": 0,
                "visible": True,
            })
            text_segment["clip"]["transform"] = {"x": 0.0, "y": -0.78}
            text_segments.append(text_segment)

        materials["texts"] = text_materials
        text_track = {k: copy.deepcopy(v) for k, v in sample_text_track.items() if k != "segments"}
        text_track.update({"id": uid(), "type": "text", "flag": 1, "segments": text_segments})
        content["tracks"] = [video_track, text_track]

        meta = load_json(folder / "draft_meta_info.json")
        meta.update({
            "draft_fold_path": folder.as_posix(),
            "draft_id": project_id,
            "draft_name": PROJECT_NAME,
            "draft_root_path": str(CAPCUT_ROOT),
            "draft_need_rename_folder": False,
            "draft_timeline_materials_size_": VIDEO.stat().st_size,
            "tm_draft_create": now,
            "tm_draft_modified": now,
            "tm_duration": duration_us,
        })
        save_json(folder / "draft_content.json", content)
        save_json(folder / "draft_content.json.bak", content)
        save_json(folder / "draft_meta_info.json", meta)
        cover = ROOT / "work" / "qa" / "start.jpg"
        if cover.exists():
            shutil.copy2(cover, folder / "draft_cover.jpg")

        root_meta_path = CAPCUT_ROOT / "root_meta_info.json"
        root_meta = load_json(root_meta_path)
        backup_dir = ROOT / "work" / "capcut_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root_meta_path, backup_dir / f"root_meta_info_{now}.json")
        template_entry = next(item for item in root_meta["all_draft_store"] if item["draft_name"] == "0811")
        entry = copy.deepcopy(template_entry)
        entry.update({
            "draft_cover": (folder / "draft_cover.jpg").as_posix(),
            "draft_fold_path": folder.as_posix(),
            "draft_id": project_id,
            "draft_json_file": (folder / "draft_content.json").as_posix(),
            "draft_name": PROJECT_NAME,
            "draft_root_path": str(CAPCUT_ROOT),
            "draft_timeline_materials_size": VIDEO.stat().st_size,
            "tm_draft_create": now,
            "tm_draft_modified": now,
            "tm_duration": duration_us,
        })
        root_meta["all_draft_store"].insert(0, entry)
        root_meta["draft_ids"] = len(root_meta["all_draft_store"])
        temp_root_meta = root_meta_path.with_suffix(".json.colony_tmp")
        save_json(temp_root_meta, root_meta)
        os.replace(temp_root_meta, root_meta_path)
        return folder
    except Exception:
        # The new, uniquely named folder is safe to remove if registration never completed.
        if folder.exists():
            shutil.rmtree(folder)
        raise


if __name__ == "__main__":
    project = build()
    print(f"CapCut project created: {project}")
