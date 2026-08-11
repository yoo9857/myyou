from __future__ import annotations

import copy
import json
import os
import time
import uuid
from pathlib import Path

from pipeline import parse_srt


ROOT = Path(__file__).resolve().parent / "Constantine" / "story_review_v5"
OUTPUT = ROOT / "output"
PROJECT = Path(os.environ["LOCALAPPDATA"]) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" / "CONSTANTINE_STORY_REVIEW_V5"


def uid() -> str:
    return str(uuid.uuid4()).upper()


def save_atomic(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".english_tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


def rebuild_track(content: dict, track: dict, srt: Path) -> int:
    old_ids = {segment["material_id"] for segment in track["segments"]}
    template_segment = copy.deepcopy(track["segments"][0])
    template_material = copy.deepcopy(next(item for item in content["materials"]["texts"] if item["id"] in old_ids))
    content["materials"]["texts"] = [item for item in content["materials"]["texts"] if item["id"] not in old_ids]
    track["segments"] = []
    new_materials = []
    for cue in parse_srt(srt):
        text = cue.text.strip()
        material = copy.deepcopy(template_material)
        material_id = uid()
        payload = json.loads(material["content"])
        payload["text"] = text
        payload["styles"] = [{
            "range": [0, len(text)],
            "size": float(material.get("font_size", 5.0)),
            "bold": False,
            "italic": False,
            "underline": False,
            "fill": {"alpha": 1, "content": {"render_type": "solid", "solid": {"alpha": 1, "color": [1, 1, 1]}}},
        }]
        material.update({
            "id": material_id,
            "recognize_text": text,
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            "is_rich_text": False,
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
            "common_keyframes": [],
        })
        segment["extra_material_refs"] = [
            ref for ref in segment.get("extra_material_refs", [])
            if not any(ref == item.get("id") for item in content["materials"].get("material_animations", []))
        ]
        new_materials.append(material)
        track["segments"].append(segment)
    content["materials"]["texts"].extend(new_materials)
    return len(track["segments"])


def main() -> None:
    if not PROJECT.exists():
        raise FileNotFoundError(PROJECT)
    content = json.loads((PROJECT / "draft_content.json").read_text(encoding="utf-8"))
    movie = next(track for track in content["tracks"] if track.get("name") == "MOVIE_DIALOGUE")
    review = next(track for track in content["tracks"] if track.get("name") == "REVIEW_NARRATION")
    movie_count = rebuild_track(content, movie, OUTPUT / "movie_captions_en.srt")
    review_count = rebuild_track(content, review, OUTPUT / "narration_v4_outro_en.srt")

    old_anim_ids = {item.get("id") for item in content["materials"].get("material_animations", [])}
    for track in content["tracks"]:
        for segment in track.get("segments", []):
            segment["extra_material_refs"] = [ref for ref in segment.get("extra_material_refs", []) if ref not in old_anim_ids]
            if track.get("type") == "text":
                segment["common_keyframes"] = []
    content["materials"]["material_animations"] = []
    content["update_time"] = time.time_ns() // 1000

    mirrors = [PROJECT / "draft_content.json", PROJECT / "template-2.tmp"]
    mirrors += list(PROJECT.glob("Timelines/*/draft_content.json"))
    mirrors += list(PROJECT.glob("Timelines/*/template-2.tmp"))
    mirrors = [path for path in mirrors if path.exists()]
    for path in mirrors:
        save_atomic(path, content)
    result = {
        "language": "en",
        "movie_dialogue_segments": movie_count,
        "review_narration_segments": review_count,
        "text_materials": len(content["materials"]["texts"]),
        "animation_materials_before_restyle": len(content["materials"]["material_animations"]),
        "mirrors_written": len(mirrors),
    }
    (OUTPUT / "CAPCUT_ENGLISH_APPLY_QA.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
