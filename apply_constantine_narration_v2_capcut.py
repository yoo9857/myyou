from __future__ import annotations

import copy
import json
import os
import shutil
import time
import uuid
from pathlib import Path

from pipeline import parse_srt


REVIEW_ROOT = Path(__file__).resolve().parent / "Constantine" / "story_review_v5"
PROJECT = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"
SRT = REVIEW_ROOT / "output" / os.environ.get("CAPCUT_NARRATION_SRT", "narration_v2.srt")


def uid() -> str:
    return str(uuid.uuid4()).upper()


def save_atomic(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".v2_tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


def main() -> None:
    if not PROJECT.exists() or not SRT.exists():
        raise FileNotFoundError("CapCut V5 프로젝트 또는 narration_v2.srt가 없습니다.")
    content_path = PROJECT / "draft_content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    track = next((item for item in content["tracks"] if item.get("name") == "REVIEW_NARRATION"), None)
    if track is None or not track.get("segments"):
        raise ValueError("REVIEW_NARRATION 템플릿 트랙을 찾지 못했습니다.")

    old_ids = {segment["material_id"] for segment in track["segments"]}
    template_segment = copy.deepcopy(track["segments"][0])
    template_material = copy.deepcopy(next(item for item in content["materials"]["texts"] if item["id"] in old_ids))
    content["materials"]["texts"] = [item for item in content["materials"]["texts"] if item["id"] not in old_ids]
    track["segments"] = []

    new_materials = []
    for cue in parse_srt(SRT):
        text = cue.text.strip()
        material = copy.deepcopy(template_material)
        material_id = uid()
        payload = json.loads(material["content"])
        payload["text"] = text
        for style in payload.get("styles", []):
            style["range"] = [0, len(text) * 2]
        material.update({
            "id": material_id,
            "recognize_text": text,
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        })
        segment = copy.deepcopy(template_segment)
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
        new_materials.append(material)
        track["segments"].append(segment)
    content["materials"]["texts"].extend(new_materials)
    content["update_time"] = time.time_ns() // 1000

    content_paths = [PROJECT / "draft_content.json", PROJECT / "draft_content.json.bak"]
    content_paths += list(PROJECT.glob("Timelines/*/draft_content.json"))
    content_paths += list(PROJECT.glob("Timelines/*/draft_content.json.bak"))
    stamp = str(time.time_ns() // 1000)
    backup = REVIEW_ROOT / "backups" / "capcut_narration_v2" / stamp
    backup.mkdir(parents=True, exist_ok=True)
    for path in content_paths:
        if path.exists():
            relative = path.relative_to(PROJECT)
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            save_atomic(path, content)

    movie_track = next(item for item in content["tracks"] if item.get("name") == "MOVIE_DIALOGUE")
    result = {
        "project": str(PROJECT),
        "backup": str(backup),
        "movie_segments": len(movie_track["segments"]),
        "review_narration_segments": len(track["segments"]),
        "text_materials": len(content["materials"]["texts"]),
        "mirrors_written": len(content_paths),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
