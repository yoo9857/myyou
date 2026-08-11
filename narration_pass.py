from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from pipeline import ROOT, OUTPUT, ANALYSIS, codex_exec, load_config, parse_srt


DEFAULT_SOURCE = OUTPUT / "edit_plan_v4_curiosity_hook.json"
SCRIPT_JSON = OUTPUT / "narration_script_v5.json"
SCRIPT_MD = OUTPUT / "narration_script_v5.md"
TARGET_PLAN = OUTPUT / "edit_plan_v5_narration.json"


def compact_dialogue(cues: list[Any], start: float, end: float, limit: int = 240) -> str:
    parts = [cue.text for cue in cues if cue.start < end and cue.end > start and cue.text.strip()]
    text = " / ".join(parts)
    return text[:limit] + ("…" if len(text) > limit else "")


def build_candidates(plan: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    cues = parse_srt(ROOT / config["subtitle"])
    segments = plan["segments"]
    candidates: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        draft = str(segment.get("narration", "")).strip()
        if not draft:
            continue
        source_start = float(segment["source_start"])
        source_end = float(segment["source_end"])
        previous = segments[index - 1] if index else None
        following = segments[index + 1] if index + 1 < len(segments) else None
        candidates.append({
            "order": int(segment["order"]),
            "story_beat": segment.get("story_beat", ""),
            "purpose": segment.get("purpose", ""),
            "source_start": source_start,
            "source_end": source_end,
            "clip_seconds": round(source_end - source_start, 3),
            "current_draft": draft,
            "dialogue_before": compact_dialogue(cues, max(0.0, source_start - 8.0), source_start),
            "dialogue_inside": compact_dialogue(cues, source_start, source_end),
            "dialogue_after": compact_dialogue(cues, source_end, source_end + 10.0),
            "previous_segment": None if previous is None else {
                "order": previous["order"],
                "kind": previous["kind"],
                "purpose": previous["purpose"],
            },
            "next_segment": None if following is None else {
                "order": following["order"],
                "kind": following["kind"],
                "purpose": following["purpose"],
            },
        })
    return candidates


def visible_korean_chars(text: str) -> int:
    return len(re.sub(r"[\s,.!?·…'\"“”‘’]", "", text))


def normalize_script(script: dict[str, Any]) -> None:
    """Keep user-approved anchor copy stable across model regenerations."""
    for item in script.get("items", []):
        if int(item.get("order", 0)) == 1:
            item["use_narration"] = True
            item["role"] = "hook"
            item["caption_ko"] = "여기, 모두를 살릴 유일한 남자가 있습니다."
            item["tts_en"] = "There is only one man who can save them all."
            item["delivery"] = "intrigued"
            item["handoff"] = "next_dialogue"
            break


def validate_script(script: dict[str, Any], candidate_orders: set[int], config: dict[str, Any]) -> None:
    items = script.get("items", [])
    orders = [int(item["order"]) for item in items]
    if len(orders) != len(set(orders)):
        raise ValueError("나레이션 결과에 중복 order가 있습니다.")
    if set(orders) != candidate_orders:
        missing = sorted(candidate_orders - set(orders))
        extra = sorted(set(orders) - candidate_orders)
        raise ValueError(f"나레이션 후보 불일치: missing={missing}, extra={extra}")

    max_ko = int(config.get("narration_max_chars_ko", 32))
    max_en = int(config.get("narration_max_words_en", 14))
    question_limit = int(config.get("narration_question_limit", 2))
    questions = 0
    for item in items:
        use = bool(item["use_narration"])
        ko = str(item["caption_ko"]).strip()
        en = str(item["tts_en"]).strip()
        if not use:
            if ko or en:
                raise ValueError(f"order {item['order']}: 제거 문장은 caption_ko/tts_en이 비어야 합니다.")
            continue
        if not ko or not en:
            raise ValueError(f"order {item['order']}: 사용할 문장의 한/영 텍스트가 비었습니다.")
        if "\n" in ko or "\n" in en:
            raise ValueError(f"order {item['order']}: 한 문장만 허용됩니다.")
        if visible_korean_chars(ko) > max_ko:
            raise ValueError(f"order {item['order']}: 한국어 문장이 {max_ko}자를 넘습니다: {ko}")
        if len(re.findall(r"[A-Za-z0-9']+", en)) > max_en:
            raise ValueError(f"order {item['order']}: 영어 문장이 {max_en}단어를 넘습니다: {en}")
        questions += ko.count("?") + en.count("?")
    if questions > question_limit * 2:
        raise ValueError(f"질문형 문장이 제한을 넘습니다: 한/영 물음표 {questions}개")


def write_markdown(script: dict[str, Any]) -> None:
    lines = [
        "# COLONY 나레이션 대본 V5",
        "",
        script.get("summary", ""),
        "",
        "| # | 사용 | 역할 | 한국어 자막 | Clara 영어 TTS | 톤 | 인계 |",
        "|---:|:---:|---|---|---|---|---|",
    ]
    for item in script["items"]:
        ko = str(item["caption_ko"]).replace("|", "\\|")
        en = str(item["tts_en"]).replace("|", "\\|")
        lines.append(
            f"| {item['order']} | {'Y' if item['use_narration'] else 'N'} | {item['role']} | "
            f"{ko} | {en} | {item['delivery']} | {item['handoff']} |"
        )
    SCRIPT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(source: Path) -> None:
    config = load_config()
    plan = json.loads(source.read_text(encoding="utf-8"))
    candidates = build_candidates(plan, config)
    if not candidates:
        raise ValueError("나레이션 후보가 없습니다.")
    outline = json.loads((ANALYSIS / "story_outline.json").read_text(encoding="utf-8"))
    prompt = (ROOT / "prompts" / "narration_pass.md").read_text(encoding="utf-8")
    prompt += (
        "\n\n이 프로젝트는 최종 반전 공개 직전까지만 사용한다. "
        "아래 후보의 source_start/source_end와 목적을 벗어나는 미래 사실을 쓰지 마라. "
        "order 1의 caption_ko는 정확히 '여기, 모두를 살릴 유일한 남자가 있습니다.'로 유지하고 "
        "tts_en은 같은 범위의 짧은 자연스러운 영어로 작성하라.\n\n"
        "STORY_CONTEXT:\n" + json.dumps({
            "title": outline.get("title"),
            "premise": outline.get("premise"),
            "spoiler_cutoff_source_sec": config.get("spoiler_cutoff_source_sec", 6113.5),
        }, ensure_ascii=False, indent=2)
        + "\n\nCANDIDATES:\n" + json.dumps(candidates, ensure_ascii=False, indent=2)
    )
    codex = shutil.which("codex.cmd") or shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI를 찾을 수 없습니다.")
    codex_exec(codex, ROOT / "schemas" / "narration_script.schema.json", SCRIPT_JSON, prompt)
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    normalize_script(script)
    validate_script(script, {item["order"] for item in candidates}, config)
    SCRIPT_JSON.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(script)
    print(f"나레이션 V5 생성: {SCRIPT_JSON.relative_to(ROOT)}, 후보 {len(candidates)}개")


def apply(source: Path, make_current: bool) -> None:
    config = load_config()
    plan = json.loads(source.read_text(encoding="utf-8"))
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    normalize_script(script)
    candidate_orders = {int(seg["order"]) for seg in plan["segments"] if str(seg.get("narration", "")).strip()}
    validate_script(script, candidate_orders, config)
    SCRIPT_JSON.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    items = {int(item["order"]): item for item in script["items"]}
    kept = 0
    for segment in plan["segments"]:
        order = int(segment["order"])
        if order not in items:
            continue
        item = items[order]
        segment["narration_original"] = segment.get("narration", "")
        segment["narration"] = item["caption_ko"] if item["use_narration"] else ""
        segment["narration_tts_en"] = item["tts_en"] if item["use_narration"] else ""
        segment["narration_delivery"] = item["delivery"]
        segment["narration_max_seconds"] = item["max_seconds"]
        segment["narration_handoff"] = item["handoff"]
        segment["narration_role"] = item["role"]
        if item["use_narration"]:
            kept += 1
    plan["narration_version"] = 5
    plan["narration_voice"] = {
        "provider": "ElevenLabs",
        "model": "eleven_v3",
        "voice_name": "Clara - Whispery & Intimate",
        "voice_id": "wNvqdMNs9MLd1PG6uWuY",
    }
    TARGET_PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if make_current:
        shutil.copy2(TARGET_PLAN, OUTPUT / "edit_plan.json")
    write_markdown(script)
    print(f"나레이션 적용: {kept}/{len(items)}개 유지 -> {TARGET_PLAN.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="편집표를 바꾸지 않는 V5 나레이션 전용 패스")
    parser.add_argument("action", choices=("generate", "apply"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--make-current", action="store_true")
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source
    if args.action == "generate":
        generate(source)
    else:
        apply(source, args.make_current)


if __name__ == "__main__":
    main()
