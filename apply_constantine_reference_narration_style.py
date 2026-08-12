from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = (
    Path(os.environ["LOCALAPPDATA"])
    / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    / "CONSTANTINE_STORY_REVIEW_V5"
)
REFERENCE_TEXT = "From then on, an ordinary life quietly twists."
TRACK_NAME = "REVIEW_NARRATION"
QA_PATH = ROOT / "Constantine" / "story_review_v5" / "output" / "CAPCUT_NARRATION_STYLE_USER_REFERENCE_QA.json"
BACKUP_ROOT = ROOT / "Constantine" / "story_review_v5" / "backups" / "capcut_narration_user_reference"

TEXT_IDENTITY_KEYS = {
    "id", "name", "recognize_text", "content", "base_content", "words",
    "current_words", "ssml_content", "translate_original_text",
}


def normalized(value: str) -> str:
    return " ".join(value.replace("ˇ", " ").replace("…", "...").split()).rstrip(".")


def capcut_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return "CapCut.exe" in result.stdout


def project_files() -> list[Path]:
    candidates = [PROJECT / "draft_content.json", PROJECT / "template-2.tmp"]
    timeline_root = PROJECT / "Timelines"
    for timeline in timeline_root.iterdir():
        if timeline.is_dir():
            candidates.extend([timeline / "draft_content.json", timeline / "template-2.tmp"])
    return [path for path in candidates if path.exists()]


def apply_style(document: dict[str, object]) -> dict[str, object]:
    tracks = document.get("tracks", [])
    track = next(
        item for item in tracks
        if item.get("type") == "text" and item.get("name") == TRACK_NAME
    )
    texts = {item["id"]: item for item in document["materials"]["texts"]}
    reference_segment = None
    reference_material = None
    for segment in track["segments"]:
        material = texts[segment["material_id"]]
        if normalized(str(material.get("recognize_text", ""))) == normalized(REFERENCE_TEXT):
            reference_segment = segment
            reference_material = material
            break
    if reference_segment is None or reference_material is None:
        raise RuntimeError("The user reference narration line was not found.")

    reference_content = json.loads(reference_material["content"])
    reference_y = float(reference_segment["clip"]["transform"]["y"])
    changed = 0
    for segment in track["segments"]:
        material = texts[segment["material_id"]]
        original_content = json.loads(material["content"])
        text = str(original_content.get("text", material.get("recognize_text", "")))
        for key, value in reference_material.items():
            if key not in TEXT_IDENTITY_KEYS:
                material[key] = copy.deepcopy(value)
        styles = copy.deepcopy(reference_content["styles"])
        for style in styles:
            style["range"] = [0, len(text)]
        material["content"] = json.dumps(
            {"text": text, "styles": styles},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        current_y = float(segment["clip"]["transform"]["y"])
        delta = reference_y - current_y
        segment["clip"]["transform"]["x"] = float(reference_segment["clip"]["transform"]["x"])
        segment["clip"]["transform"]["y"] = reference_y
        for keyframe in segment.get("common_keyframes", []):
            if keyframe.get("property_type") == "KFTypePositionY":
                for point in keyframe.get("keyframe_list", []):
                    values = point.get("values", [])
                    if values:
                        values[0] = round(float(values[0]) + delta, 6)
        changed += 1

    return {
        "track": TRACK_NAME,
        "segment_count": len(track["segments"]),
        "changed_count": changed,
        "reference_text": REFERENCE_TEXT,
        "style_name": reference_material.get("style_name"),
        "font_name": reference_material.get("font_name"),
        "font_resource_id": reference_material.get("font_resource_id"),
        "font_size": reference_material.get("font_size"),
        "text_color": reference_material.get("text_color"),
        "border_width": reference_material.get("border_width"),
        "position_y": reference_y,
    }


def main() -> int:
    if capcut_running():
        raise RuntimeError("CapCut is running. Save and close it before applying the style.")
    files = project_files()
    if not files:
        raise FileNotFoundError(PROJECT)

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_ROOT / stamp
    shutil.copytree(
        PROJECT,
        backup,
        ignore=shutil.ignore_patterns("assets", ".capcut-cli-history"),
    )

    reports = []
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        report = apply_style(document)
        path.write_text(
            json.dumps(document, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        report["file"] = str(path)
        report["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        reports.append(report)

    hashes = {report["sha256"] for report in reports}
    qa = {
        "status": "pass" if len(hashes) == 1 else "fail",
        "project": str(PROJECT),
        "backup": str(backup),
        "files_updated": len(files),
        "mirror_hashes_match": len(hashes) == 1,
        "reports": reports,
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
