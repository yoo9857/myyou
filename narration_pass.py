from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from pipeline import CODE_ROOT, ROOT, OUTPUT, ANALYSIS, codex_exec, load_config, parse_srt, story_map_path, validate_sfx_plan, validate_story_map_gate


DEFAULT_SOURCE = OUTPUT / "edit_plan_v4_curiosity_hook.json"
SCRIPT_JSON = OUTPUT / "narration_script_v5.json"
SCRIPT_MD = OUTPUT / "narration_script_v5.md"
TARGET_PLAN = OUTPUT / "edit_plan_v5_narration.json"
_SFX_RELATIVE = Path("assets") / "sfx" / "narration_preroll" / "manifest.json"
# The preroll library is shared. A project only carries its own copy if it needs different
# assets; otherwise it uses the one beside the code, same as the learning registry does.
SFX_MANIFEST = ROOT / _SFX_RELATIVE if (ROOT / _SFX_RELATIVE).exists() else CODE_ROOT / _SFX_RELATIVE


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
        if not draft and int(segment["order"]) != 1:
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


def _sfx_durations() -> dict[str, float]:
    manifest = json.loads(SFX_MANIFEST.read_text(encoding="utf-8"))
    return {
        asset_id: float(spec.get("duration_seconds", 0.0))
        for asset_id, spec in manifest.get("assets", {}).items()
    }


def normalize_script(script: dict[str, Any], config: dict[str, Any] | None = None) -> None:
    """Keep user-approved anchor copy stable across model regenerations."""
    for item in script.get("items", []):
        item["caption_ko"] = str(item.get("caption_ko", "")).strip()
        item["tts_en"] = str(item.get("tts_en", "")).strip()
        item["sfx_preroll"] = str(item.get("sfx_preroll", "none")).strip() or "none"
        item["sfx_lead_seconds"] = float(item.get("sfx_lead_seconds", 0.0) or 0.0)
        # The lead is arithmetic, not judgement: the effect has to finish so that only its
        # quiet tail runs under the first fifth of a second of speech, which fixes the lead
        # at the asset's own length minus that overlap. Left to the model it comes back
        # wrong - a 0.7 s asset was given a 0.9 s lead, putting the effect after the words.
        if item["sfx_preroll"] != "none":
            duration = _sfx_durations().get(item["sfx_preroll"])
            if duration:
                item["sfx_lead_seconds"] = round(min(max(duration - 0.20, 0.15), 1.0), 3)
        item["sfx_rationale"] = str(item.get("sfx_rationale", "")).strip()
        item["scene_protection"] = str(item.get("scene_protection", "unreviewed")).strip() or "unreviewed"
        if config and int(item.get("order", 0)) == 1 and config.get("hook_caption_ko"):
            item["use_narration"] = True
            item["role"] = "hook"
            item["caption_ko"] = str(config["hook_caption_ko"]).strip()
            item["tts_en"] = str(config["hook_tts_en"]).strip()
            item["delivery"] = "urgent"
            item["handoff"] = "next_dialogue"
            item["spoiler_risk"] = "low"


def validate_script(script: dict[str, Any], candidate_orders: set[int], config: dict[str, Any]) -> None:
    items = script.get("items", [])
    orders = [int(item["order"]) for item in items]
    if len(orders) != len(set(orders)):
        raise ValueError("나레이션 결과에 중복 order가 있습니다.")
    if set(orders) != candidate_orders:
        missing = sorted(candidate_orders - set(orders))
        extra = sorted(set(orders) - candidate_orders)
        raise ValueError(f"나레이션 후보 불일치: missing={missing}, extra={extra}")

    # 32 characters is a Korean caption's readable width. The same count in English is
    # about four words, so a review narrated in English is measured in words instead - the
    # caption carries the same sentence as the voice line and reads at the same rate.
    english_caption = str(config.get("review_language", "ko")).lower().startswith("en")
    max_ko = int(config.get("narration_max_chars_ko", 32))
    max_en = int(config.get("narration_max_words_en", 14))
    question_limit = int(config.get("narration_question_limit", 2))
    manifest = json.loads(SFX_MANIFEST.read_text(encoding="utf-8"))
    sfx_assets = manifest.get("assets", {})
    global_sfx_limit = int(config.get("narration_sfx_max_uses", manifest.get("global_rules", {}).get("max_uses_per_19_25_min_review", 8)))
    sfx_counts = {asset_id: 0 for asset_id in sfx_assets}
    scene_protections = {
        "unreviewed", "clear", "strong_dialogue", "death_grief", "confession",
        "discovery_payoff", "reversal_reveal", "horror_payoff", "active_combat",
    }
    total_sfx = 0
    questions = 0
    for item in items:
        use = bool(item["use_narration"])
        ko = str(item["caption_ko"]).strip()
        en = str(item["tts_en"]).strip()
        sfx_id = str(item.get("sfx_preroll", "none"))
        sfx_lead = float(item.get("sfx_lead_seconds", 0.0))
        sfx_reason = str(item.get("sfx_rationale", "")).strip()
        scene_protection = str(item.get("scene_protection", "unreviewed")).strip() or "unreviewed"
        if scene_protection not in scene_protections:
            raise ValueError(f"order {item['order']}: 알 수 없는 보호 상태입니다: {scene_protection}")
        if not use:
            if ko or en:
                raise ValueError(f"order {item['order']}: 제거 문장은 caption_ko/tts_en이 비어야 합니다.")
            if sfx_id != "none" or sfx_lead != 0 or sfx_reason:
                raise ValueError(f"order {item['order']}: 제거 문장에는 프리롤 효과음을 사용할 수 없습니다.")
            continue
        if not ko or not en:
            raise ValueError(f"order {item['order']}: 사용할 문장의 한/영 텍스트가 비었습니다.")
        if "\n" in ko or "\n" in en:
            raise ValueError(f"order {item['order']}: 한 문장만 허용됩니다.")
        if english_caption:
            caption_words = len(re.findall(r"[A-Za-z0-9']+", ko))
            if caption_words > max_en:
                raise ValueError(f"order {item['order']}: 자막 문장이 {max_en}단어를 넘습니다: {ko}")
            if re.search(r"[가-힣]", ko + en):
                raise ValueError(f"order {item['order']}: 영어 리뷰인데 한글이 섞였습니다: {ko}")
        elif visible_korean_chars(ko) > max_ko:
            raise ValueError(f"order {item['order']}: 한국어 문장이 {max_ko}자를 넘습니다: {ko}")
        if len(re.findall(r"[A-Za-z0-9']+", en)) > max_en:
            raise ValueError(f"order {item['order']}: 영어 문장이 {max_en}단어를 넘습니다: {en}")
        if sfx_id == "none":
            if sfx_lead != 0 or sfx_reason:
                raise ValueError(f"order {item['order']}: sfx_preroll=none이면 lead와 rationale이 비어야 합니다.")
        else:
            if sfx_id not in sfx_assets:
                raise ValueError(f"order {item['order']}: 알 수 없는 효과음 ID입니다: {sfx_id}")
            if not 0.15 <= sfx_lead <= 1.0:
                raise ValueError(f"order {item['order']}: 효과음 lead는 0.15~1.0초여야 합니다.")
            if not sfx_reason:
                raise ValueError(f"order {item['order']}: 효과음 선택 근거가 비었습니다.")
            if item.get("delivery") == "somber" or item.get("role") == "reflection":
                raise ValueError(f"order {item['order']}: 감정/성찰 나레이션에는 효과음을 사용할 수 없습니다.")
            if scene_protection != "clear":
                raise ValueError(
                    f"order {item['order']}: 보호 장면({scene_protection})에는 프리롤 효과음을 사용할 수 없습니다."
                )
            sfx_counts[sfx_id] += 1
            total_sfx += 1
        questions += ko.count("?") + en.count("?")
    if questions > question_limit * 2:
        raise ValueError(f"질문형 문장이 제한을 넘습니다: 한/영 물음표 {questions}개")
    if total_sfx > global_sfx_limit:
        raise ValueError(f"프리롤 효과음이 전체 제한 {global_sfx_limit}개를 넘습니다: {total_sfx}")
    for asset_id, count in sfx_counts.items():
        maximum = int(sfx_assets[asset_id].get("max_uses_per_review", global_sfx_limit))
        if count > maximum:
            raise ValueError(f"효과음 {asset_id} 사용 {count}회가 제한 {maximum}회를 넘습니다.")


def write_markdown(script: dict[str, Any]) -> None:
    lines = [
        f"# {load_config().get('project_title', 'Movie Review')} 나레이션 대본",
        "",
        script.get("summary", ""),
        "",
        "| # | 사용 | 역할 | 보호 상태 | 한국어 자막 | 영어 TTS | 톤 | 인계 | 프리롤 효과음 |",
        "|---:|:---:|---|---|---|---|---|---|---|",
    ]
    for item in script["items"]:
        ko = str(item["caption_ko"]).replace("|", "\\|")
        en = str(item["tts_en"]).replace("|", "\\|")
        lines.append(
            f"| {item['order']} | {'Y' if item['use_narration'] else 'N'} | {item['role']} | {item.get('scene_protection', 'unreviewed')} | "
            f"{ko} | {en} | {item['delivery']} | {item['handoff']} | {item.get('sfx_preroll', 'none')} |"
        )
    SCRIPT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_reference_learning_context(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("reference_learning_registry", "work/references/learning_registry.json")
    path = Path(str(value))
    if not path.is_absolute():
        project_path = ROOT / path
        shared_path = CODE_ROOT / path
        path = project_path if project_path.exists() else shared_path
    required = bool(config.get("require_reference_learning_approval", False))
    if not path.exists():
        if required:
            raise FileNotFoundError(f"승인된 참고 영상 학습 레지스트리가 없습니다: {path}")
        return {}
    registry = json.loads(path.read_text(encoding="utf-8"))
    references = registry.get("references", [])
    approved_rules = [rule for rule in registry.get("rules", []) if rule.get("status") == "approved"]
    reference_ids = {str(item.get("video_id")) for item in references}
    for reference in references:
        metrics_path = Path(str(reference.get("metrics_file", "")))
        if not metrics_path.is_absolute():
            metrics_root = CODE_ROOT if path.is_relative_to(CODE_ROOT) else ROOT
            metrics_path = metrics_root / metrics_path
        if not metrics_path.exists():
            raise FileNotFoundError(f"참고 영상 지표 파일이 없습니다: {metrics_path}")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if str(metrics.get("video_id")) != str(reference.get("video_id")):
            raise ValueError(f"참고 영상 ID와 지표 파일이 일치하지 않습니다: {metrics_path}")
        if not str(reference.get("limitations", "")).strip():
            raise ValueError(f"참고 영상 {reference.get('video_id')}의 측정 한계가 비었습니다.")
    for rule in approved_rules:
        evidence = {str(item) for item in rule.get("evidence", [])}
        missing = sorted(evidence - reference_ids)
        if missing:
            raise ValueError(f"참고 영상 학습 규칙 {rule.get('id')}의 근거가 레지스트리에 없습니다: {missing}")
        if not str(rule.get("instruction", "")).strip():
            raise ValueError(f"참고 영상 학습 규칙 {rule.get('id')}의 instruction이 비었습니다.")
    if required and not approved_rules:
        raise ValueError("승인된 참고 영상 학습 규칙이 하나도 없습니다.")
    return {
        "copyright_policy": registry.get("copyright_policy"),
        "references": references,
        "approved_rules": approved_rules,
    }


def generate(source: Path) -> None:
    config = load_config()
    validate_story_map_gate(config, require_render_ready=True)
    plan = json.loads(source.read_text(encoding="utf-8"))
    candidates = build_candidates(plan, config)
    if not candidates:
        raise ValueError("나레이션 후보가 없습니다.")
    prompt = (CODE_ROOT / "prompts" / "narration_pass.md").read_text(encoding="utf-8")
    # The shared prompt was written for a review that prunes narration down to what the
    # film cannot say for itself, and it assumes Korean. A project whose approved rules
    # disagree - a different language, a narration share the edit plan already allocated -
    # states so here rather than by forking the prompt, which every other project reads.
    directives = str(config.get("narration_pass_directives", "")).strip()
    if directives:
        prompt += (
            "\n\n## Project directives\n\n"
            "These come from this project's approved reference learning and override the "
            "general guidance above wherever the two disagree.\n\n" + directives
        )
    reference_learning = load_reference_learning_context(config)
    story_path = story_map_path(config)
    story_map = json.loads(story_path.read_text(encoding="utf-8")) if story_path and story_path.exists() else {}
    # Only the title and premise are wanted here. A project that authored its story map by
    # hand has both already and does not need the codex outline pass, which exists to derive
    # a beat list from the subtitle track - work the story map supersedes.
    outline_path = ANALYSIS / "story_outline.json"
    if outline_path.exists():
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    elif story_map.get("project_title") and story_map.get("premise"):
        outline = {"title": story_map["project_title"], "premise": story_map["premise"]}
    else:
        raise FileNotFoundError(
            f"{outline_path} 가 없고 스토리맵에 project_title/premise도 없습니다.")
    prompt += (
        "\n\nSTORY_CONTEXT:\n" + json.dumps({
            "title": outline.get("title"),
            "premise": outline.get("premise"),
            "spoiler_cutoff_source_sec": config.get("spoiler_cutoff_source_sec"),
            "causal_story_map": story_map,
        }, ensure_ascii=False, indent=2)
        + "\n\nCANDIDATES:\n" + json.dumps(candidates, ensure_ascii=False, indent=2)
        + "\n\nAPPROVED_REFERENCE_LEARNING:\n" + json.dumps(reference_learning, ensure_ascii=False, indent=2)
    )
    codex = shutil.which("codex.cmd") or shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI를 찾을 수 없습니다.")
    codex_exec(codex, CODE_ROOT / "schemas" / "narration_script.schema.json", SCRIPT_JSON, prompt)
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    normalize_script(script, config)
    validate_script(script, {item["order"] for item in candidates}, config)
    SCRIPT_JSON.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(script)
    print(f"나레이션 V5 생성: {SCRIPT_JSON.relative_to(ROOT)}, 후보 {len(candidates)}개")


def apply(source: Path, make_current: bool) -> None:
    config = load_config()
    validate_story_map_gate(config, require_render_ready=True)
    plan = json.loads(source.read_text(encoding="utf-8"))
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    normalize_script(script, config)
    candidate_orders = {
        int(seg["order"])
        for seg in plan["segments"]
        if str(seg.get("narration", "")).strip()
        or str(seg.get("narration_original", "")).strip()
        or int(seg["order"]) == 1
    }
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
        segment["narration_sfx_preroll"] = item.get("sfx_preroll", "none") if item["use_narration"] else "none"
        segment["narration_sfx_lead_seconds"] = item.get("sfx_lead_seconds", 0.0) if item["use_narration"] else 0.0
        segment["narration_sfx_rationale"] = item.get("sfx_rationale", "") if item["use_narration"] else ""
        segment["narration_scene_protection"] = item.get("scene_protection", "unreviewed")
        if item["use_narration"]:
            kept += 1
    plan["narration_version"] = 5
    plan["narration_sfx_library"] = {
        "manifest": str(
            SFX_MANIFEST.relative_to(ROOT) if SFX_MANIFEST.is_relative_to(ROOT)
            else SFX_MANIFEST
        ).replace("\\", "/"),
        "version": 1,
        "placement": "low-level preroll before selected narration cues",
    }
    plan["narration_voice"] = {
        "provider": "ElevenLabs",
        "model": "eleven_v3",
        "voice_name": "User-selected Voice Library voice",
        "voice_id": config.get("elevenlabs_voice_id", "cfc7wVYq4gw4OpcEEAom"),
        "voice_settings": "voice defaults (no request override)",
    }
    validate_sfx_plan(plan, config)
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
    try:
        main()
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
