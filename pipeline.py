from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CODE_ROOT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("MOVIE_REVIEW_ROOT", CODE_ROOT)).resolve()
WORK = ROOT / "work"
ANALYSIS = WORK / "analysis"
SHEETS = WORK / "contact_sheets"
RENDER = WORK / "render"
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"
_SFX_RELATIVE = Path("assets") / "sfx" / "narration_preroll" / "manifest.json"
# The preroll library is shared. A project only carries its own copy if it needs different
# assets; otherwise it uses the one beside the code, same as the learning registry does.
SFX_MANIFEST = ROOT / _SFX_RELATIVE if (ROOT / _SFX_RELATIVE).exists() else CODE_ROOT / _SFX_RELATIVE


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str


def load_config() -> dict[str, Any]:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def run(cmd: list[str], *, capture: bool = False, input_text: str | None = None) -> str:
    printable = subprocess.list2cmdline(cmd)
    print(f"> {printable}", flush=True)
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout if capture else ""


def validate_story_map_gate(
    config: dict[str, Any], *, require_render_ready: bool, project_root: Path | None = None
) -> None:
    """Validate the causal story map before plan/render stages when enabled."""
    story_value = config.get("story_map")
    required = bool(config.get("require_story_map", False))
    if not story_value:
        if required:
            raise FileNotFoundError("require_story_map=true 이지만 config.json에 story_map이 없습니다.")
        return
    base_root = project_root or ROOT
    story_map = Path(str(story_value))
    if not story_map.is_absolute():
        story_map = base_root / story_map
    if not story_map.exists():
        raise FileNotFoundError(f"스토리맵을 찾을 수 없습니다: {story_map}")

    default_validator = Path.home() / ".codex" / "skills" / "edit-movie-review" / "scripts" / "validate_story_map.py"
    validator = Path(str(config.get("story_validator") or os.environ.get("MOVIE_REVIEW_STORY_VALIDATOR") or default_validator))
    if not validator.exists():
        raise FileNotFoundError(f"스토리맵 검사기를 찾을 수 없습니다: {validator}")
    command = [sys.executable, str(validator), str(story_map)]
    if require_render_ready:
        command.append("--require-render-ready")
    print(f"> {subprocess.list2cmdline(command)}", flush=True)
    result = subprocess.run(
        command, cwd=base_root, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
        raise ValueError("STORY_MAP_GATE_BLOCKED:\n" + detail)
    if result.stdout.strip():
        print(result.stdout.strip(), flush=True)


def story_map_path(config: dict[str, Any]) -> Path | None:
    value = config.get("story_map")
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def validate_reference_learning_gate(config: dict[str, Any]) -> dict[str, Any] | None:
    value = config.get("reference_learning_registry")
    required = bool(config.get("require_reference_learning_approval", False))
    if not value:
        if required:
            raise FileNotFoundError("require_reference_learning_approval=true 이지만 레지스트리 경로가 없습니다.")
        return None
    registry = Path(str(value))
    if not registry.is_absolute():
        project_registry = ROOT / registry
        shared_registry = CODE_ROOT / registry
        registry = project_registry if project_registry.exists() else shared_registry
    if not registry.exists():
        raise FileNotFoundError(f"승인된 참고 영상 학습 레지스트리가 없습니다: {registry}")
    validator = CODE_ROOT / "scripts" / "validate_reference_learning.py"
    metrics_root = CODE_ROOT if registry.is_relative_to(CODE_ROOT) else ROOT
    result = subprocess.run(
        [sys.executable, str(validator), str(registry), "--project-root", str(metrics_root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
        raise ValueError("REFERENCE_LEARNING_GATE_BLOCKED:\n" + detail)
    return json.loads(result.stdout)


def validate_voice_profile_gate(config: dict[str, Any]) -> dict[str, Any] | None:
    value = config.get("elevenlabs_voice_profile")
    if not value:
        return None
    profile_path = Path(str(value))
    if not profile_path.is_absolute():
        # The approved profile is shared across projects - it was locked once and every
        # review since has used it - so a project only holds its own copy if it deliberately
        # differs. Same fallback as the learning registry and the preroll library.
        project_copy = ROOT / profile_path
        profile_path = project_copy if project_copy.exists() else CODE_ROOT / profile_path
    if not profile_path.exists():
        raise FileNotFoundError(f"승인 보이스 프로필이 없습니다: {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    expected_voice = str(config.get("elevenlabs_voice_id", ""))
    expected_model = str(config.get("elevenlabs_model", ""))
    if expected_voice and str(profile.get("voice_id")) != expected_voice:
        raise ValueError("VOICE_PROFILE_GATE_BLOCKED: config와 프로필의 Voice ID가 다릅니다.")
    if expected_model and str(profile.get("model_id")) != expected_model:
        raise ValueError("VOICE_PROFILE_GATE_BLOCKED: config와 프로필의 모델이 다릅니다.")
    if profile.get("voice_settings") is not None:
        raise ValueError("VOICE_PROFILE_GATE_BLOCKED: 승인 하우스 보이스는 provider defaults여야 합니다.")
    post = profile.get("postprocess", {})
    for key in ("ffmpeg_filter", "sample_rate", "channels", "codec", "bitrate"):
        if key not in post:
            raise ValueError(f"VOICE_PROFILE_GATE_BLOCKED: postprocess.{key}가 없습니다.")
    return {
        "profile": str(profile_path.relative_to(ROOT)).replace("\\", "/") if profile_path.is_relative_to(ROOT) else str(profile_path),
        "profile_id": profile.get("profile_id"),
        "voice_id": profile.get("voice_id"),
        "model_id": profile.get("model_id"),
    }


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    video = ROOT / str(config["video"])
    subtitle = ROOT / str(config["subtitle"])
    if not video.exists():
        raise FileNotFoundError(f"영화 원본이 없습니다: {video}")
    if not subtitle.exists():
        raise FileNotFoundError(f"제공 SRT가 없습니다: {subtitle}")
    validate_story_map_gate(config, require_render_ready=True)
    reference_qa = validate_reference_learning_gate(config)
    voice_qa = validate_voice_profile_gate(config)
    probe = ffprobe(video)
    source_duration = float(probe["format"]["duration"])
    plan_path = OUTPUT / "edit_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"승인 편집표가 없습니다: {plan_path}")
    plan = validate_plan(plan_path, source_duration, float(config.get("target_duration_sec", 1320)))
    result = {
        "status": "pass",
        "video": str(video),
        "subtitle": str(subtitle),
        "source_duration_seconds": source_duration,
        "segment_count": len(plan.get("segments", [])),
        "reference_learning": reference_qa,
        "voice_profile": voice_qa,
        "story_map_required": bool(config.get("require_story_map", False)),
        "narration_rhythm_gate": bool(config.get("enforce_narration_rhythm_gate", True)),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "WORKFLOW_PREFLIGHT_QA.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"사전 검증 통과: {len(plan.get('segments', []))}개 세그먼트", flush=True)
    return result


def ffprobe(video: Path) -> dict[str, Any]:
    raw = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(video),
    ], capture=True)
    return json.loads(raw)


def parse_time(value: str) -> float:
    h, m, rest = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def format_srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    h, rem = divmod(millis, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(path: Path) -> list[Cue]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    blocks = re.split(r"\n{2,}", text.strip())
    cues: list[Cue] = []
    timing = re.compile(r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})")
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        match_pos = next((i for i, line in enumerate(lines) if timing.search(line)), None)
        if match_pos is None:
            continue
        match = timing.search(lines[match_pos])
        assert match
        idx = int(lines[0]) if lines[0].isdigit() else len(cues) + 1
        cues.append(Cue(idx, parse_time(match.group(1)), parse_time(match.group(2)), " ".join(lines[match_pos + 1 :])))
    return cues


HOOK_WORDS = (
    "테러", "죽", "살려", "위험", "비밀", "실험", "경찰", "도망", "폭발", "총",
    "정체", "거짓말", "왜", "안 돼", "멈춰", "사라", "범인", "괴물", "충격", "마지막",
)


def build_analysis(config: dict[str, Any]) -> None:
    video = ROOT / config["video"]
    subtitle = ROOT / config["subtitle"]
    if not video.exists() or not subtitle.exists():
        raise FileNotFoundError("config.json의 video/subtitle 파일을 찾을 수 없습니다.")
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)

    info = ffprobe(video)
    (ANALYSIS / "video_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    duration = float(info["format"]["duration"])
    cues = parse_srt(subtitle)

    packet_size = 180.0
    packets: list[dict[str, Any]] = []
    for packet_index, start in enumerate(range(0, math.ceil(duration), int(packet_size)), 1):
        end = min(duration, start + packet_size)
        selected = [c for c in cues if c.start < end and c.end > start]
        joined = " ".join(c.text for c in selected)
        hook_hits = sum(joined.count(word) for word in HOOK_WORDS)
        speaking = sum(max(0.0, min(c.end, end) - max(c.start, start)) for c in selected)
        packets.append({
            "packet": packet_index,
            "start": start,
            "end": round(end, 3),
            "subtitle_count": len(selected),
            "dialogue_seconds": round(speaking, 2),
            "dialogue_density": round(speaking / max(1.0, end - start), 3),
            "hook_score": hook_hits,
            "dialogue": [{"start": c.start, "end": c.end, "text": c.text} for c in selected],
        })
    (ANALYSIS / "story_packets.json").write_text(json.dumps(packets, ensure_ascii=False, indent=2), encoding="utf-8")
    digest_lines = []
    for packet in packets:
        start = format_srt_time(float(packet["start"]))[:8]
        end = format_srt_time(float(packet["end"]))[:8]
        dialogue = " / ".join(item["text"] for item in packet["dialogue"])
        digest_lines.append(
            f"[{packet['packet']:02d}] {start}-{end} | 후킹어 {packet['hook_score']} | "
            f"대사밀도 {packet['dialogue_density']}\n{dialogue}"
        )
    (ANALYSIS / "story_digest.txt").write_text("\n\n".join(digest_lines), encoding="utf-8")

    gaps: list[dict[str, Any]] = []
    previous_end = 0.0
    for cue in cues:
        gap = cue.start - previous_end
        if gap >= 2.0:
            gaps.append({"start": round(previous_end, 3), "end": round(cue.start, 3), "duration": round(gap, 3)})
        previous_end = max(previous_end, cue.end)
    if duration - previous_end >= 2.0:
        gaps.append({"start": round(previous_end, 3), "end": round(duration, 3), "duration": round(duration - previous_end, 3)})
    (ANALYSIS / "narration_gaps.json").write_text(json.dumps(gaps, ensure_ascii=False, indent=2), encoding="utf-8")

    sheet_pattern = SHEETS / "sheet_%03d.jpg"
    interval = int(config.get("contact_sheet_interval_sec", 30))
    cols = int(config.get("contact_sheet_columns", 5))
    rows = int(config.get("contact_sheet_rows", 4))
    expected_sheets = math.ceil(duration / interval / (cols * rows))
    if len(list(SHEETS.glob("sheet_*.jpg"))) < expected_sheets:
        # drawtext is deliberately omitted: some Windows FFmpeg builds crash when
        # Fontconfig has no configuration. Sheet/frame positions map to a timestamp
        # deterministically via interval, columns, and rows in manifest.json.
        vf = f"fps=1/{interval},scale=320:-2,tile={cols}x{rows}"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-i", str(video), "-vf", vf, "-q:v", "3", "-y", str(sheet_pattern)])

    manifest = {
        "video": str(video.name),
        "subtitle": str(subtitle.name),
        "duration": duration,
        "cue_count": len(cues),
        "story_packet_count": len(packets),
        "narration_gap_count": len(gaps),
        "contact_sheet_interval_sec": interval,
        "contact_sheet_grid": {"columns": cols, "rows": rows},
        "contact_sheets": [p.name for p in sorted(SHEETS.glob("sheet_*.jpg"))],
    }
    (ANALYSIS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def codex_exec(codex: str, schema: Path, output: Path, prompt: str) -> None:
    print(f"Codex 생성 시작: {output.relative_to(ROOT)}", flush=True)
    run([
        codex, "exec", "--ephemeral", "--cd", str(ROOT), "--skip-git-repo-check", "--sandbox", "read-only",
        "--output-schema", str(schema), "--output-last-message", str(output), "-",
    ], input_text=prompt)
    print(f"Codex 생성 완료: {output.relative_to(ROOT)}", flush=True)


def build_plan(config: dict[str, Any]) -> None:
    validate_story_map_gate(config, require_render_ready=True)
    if not (ANALYSIS / "manifest.json").exists():
        build_analysis(config)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    codex = shutil.which("codex.cmd") or shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI를 찾을 수 없습니다.")
    outline = ANALYSIS / "story_outline.json"
    if not outline.exists():
        digest_chunks = (ANALYSIS / "story_digest.txt").read_text(encoding="utf-8").split("\n\n")
        chunk_size = math.ceil(len(digest_chunks) / 3)
        chunk_outputs: list[Path] = []
        for i in range(3):
            selected = digest_chunks[i * chunk_size : (i + 1) * chunk_size]
            if not selected:
                continue
            chunk_output = ANALYSIS / f"outline_chunk_{i + 1}.json"
            chunk_outputs.append(chunk_output)
            if chunk_output.exists():
                continue
            prompt = (
                "You are a story editor for a Korean-language YouTube movie review. "
                "Analyze only the supplied three-minute subtitle packets. Identify characters, events, "
                "conflict changes, reversals, and causal links. Use exact source seconds for event start/end, "
                "and quote only dialogue present in the packets. Return only JSON matching the schema.\n\n"
                + "\n\n".join(selected)
            )
            codex_exec(codex, CODE_ROOT / "schemas" / "chunk_outline.schema.json", chunk_output, prompt)
        merged_chunks = "\n\n".join(path.read_text(encoding="utf-8") for path in chunk_outputs)
        merge_prompt = (
            "Merge the supplied chronological analyses into one accurate story outline for a Korean YouTube "
            "movie review. Produce 8-20 beats covering setup, inciting incident, escalation, midpoint reversal, "
            "rising danger, climax, and resolution. Preserve exact source seconds and quote only supplied dialogue. "
            "For sheet_numbers, sheet 1 covers 0-599 seconds, sheet 2 covers 600-1199 seconds, and so on. "
            "Return only JSON matching the schema.\n\n" + merged_chunks
        )
        codex_exec(codex, CODE_ROOT / "schemas" / "story_outline.schema.json", outline, merge_prompt)
    plan_prompt_template = (CODE_ROOT / "prompts" / "edit_plan.md").read_text(encoding="utf-8")
    story_path = story_map_path(config)
    story_context = story_path.read_text(encoding="utf-8") if story_path and story_path.exists() else "{}"
    plan_prompt = (
        plan_prompt_template
        + "\n\nUse only the supplied config and story outline. Allocate non-overlapping source clips within each beat. "
        f"Target {max(1140, int(float(config.get('target_duration_sec', 1320)) - 60))}-"
        f"{min(1500, int(float(config.get('target_duration_sec', 1320)) + 60))} seconds total, "
        "use natural scene blocks whose lengths follow dramatic function, and keep source order unless the story map explicitly uses audience-reveal order. "
        "Preserve strong dialogue, discoveries, grief, comedy, and action payoffs. Use sparse 2-5 second narration only for orientation, "
        "causal bridges, demonstrated rules, supported character subtext, or established stakes. Never narrate a result before it appears. "
        "End before the decisive solution, final reveal, survivor outcome, and aftermath. Return only schema-valid JSON.\n\n"
        "CONFIG:\n" + json.dumps(config, ensure_ascii=False, indent=2)
        + "\n\nSTORY_OUTLINE:\n" + outline.read_text(encoding="utf-8")
        + "\n\nCAUSAL_STORY_MAP:\n" + story_context
    )
    codex_exec(
        codex, CODE_ROOT / "schemas" / "edit_plan.schema.json", OUTPUT / "edit_plan.json",
        plan_prompt,
    )
    validate_plan(
        OUTPUT / "edit_plan.json",
        float(ffprobe(ROOT / config["video"])["format"]["duration"]),
        float(config.get("target_duration_sec", 1320)),
    )


def validate_story_coverage(plan: dict[str, Any], config: dict[str, Any]) -> None:
    path = story_map_path(config)
    if not path or not path.exists():
        return
    story = json.loads(path.read_text(encoding="utf-8"))
    sections = story.get("sections", [])
    if not sections or any(section.get("status") != "approved" for section in sections):
        return
    segments = plan.get("segments", [])
    threshold = float(config.get("must_show_min_coverage_ratio", 0.85))
    omissions: list[str] = []
    for section in sections:
        for event in section.get("events", []):
            if not event.get("must_show"):
                continue
            for interval in event.get("selected_intervals", []):
                required_start, required_end = map(float, interval)
                required_duration = required_end - required_start
                covered = sum(
                    max(0.0, min(float(seg["source_end"]), required_end) - max(float(seg["source_start"]), required_start))
                    for seg in segments
                )
                ratio = covered / max(required_duration, 0.001)
                if ratio + 1e-9 < threshold:
                    omissions.append(f"{event['id']} {required_start:.2f}-{required_end:.2f} ({ratio:.0%})")
    if omissions:
        raise ValueError("STORY_EVENT_OMITTED: " + "; ".join(omissions))


def validate_plan(path: Path, source_duration: float, target_duration: float = 1320) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    segments = plan.get("segments", [])
    validator_config = load_config() if (ROOT / "config.json").exists() else {}
    min_segments = int(validator_config.get("plan_min_segments", 45))
    max_segments = int(validator_config.get("plan_max_segments", 140))
    max_clip_seconds = float(validator_config.get("plan_max_clip_seconds", 30))
    if not min_segments <= len(segments) <= max_segments:
        raise ValueError(f"편집표 segments 수가 {min_segments}~{max_segments} 범위가 아닙니다.")
    expected = 1
    total = 0.0
    consecutive_narration = 0
    used: list[tuple[float, float]] = []
    for seg in segments:
        if seg["order"] != expected:
            raise ValueError("segment order는 1부터 연속이어야 합니다.")
        start, end = float(seg["source_start"]), float(seg["source_end"])
        if not (0 <= start < end <= source_duration + 0.1):
            raise ValueError(f"잘못된 소스 구간: {start}~{end}")
        if end - start > max_clip_seconds:
            raise ValueError(f"{max_clip_seconds:g}초를 넘는 클립: {start}~{end}")
        if any(max(start, a) < min(end, b) - 0.5 for a, b in used):
            raise ValueError(f"중복된 소스 구간: {start}~{end}")
        used.append((start, end))
        total += end - start
        if str(seg.get("narration", "")).strip():
            consecutive_narration += 1
            if bool(validator_config.get("enforce_narration_rhythm_gate", True)) and consecutive_narration > 2:
                raise ValueError(
                    f"order {seg['order']}: 나레이션 블록이 3개 이상 연속됩니다. 의미 있는 영화 원음으로 반환해야 합니다."
                )
        else:
            consecutive_narration = 0
        expected += 1
    # The 1140 floor came from the 19-25 minute policy. A project may set its own band via
    # min_duration_sec / max_duration_sec, which the config template already exposes; a
    # same-film reference measured at 18.1 minutes is a reason to go under 19, and it should
    # not need a code change. Defaults keep the old behaviour for projects that set neither.
    floor = validator_config.get("min_duration_sec")
    ceiling = validator_config.get("max_duration_sec")
    minimum = float(floor) if floor else max(1140.0, target_duration - 180.0)
    maximum = float(ceiling) if ceiling else min(1500.0, target_duration + 180.0)
    if not minimum <= total <= maximum:
        raise ValueError(f"실제 클립 합계 {total:.1f}초가 허용 범위({minimum:.0f}~{maximum:.0f}초)를 벗어났습니다.")
    validate_story_coverage(plan, validator_config)
    validate_sfx_plan(plan, validator_config)
    return plan


def write_srt(entries: list[tuple[float, float, str]], path: Path) -> None:
    entries = sorted(entries, key=lambda item: (item[0], item[1]))
    blocks = []
    for idx, (start, end, text) in enumerate(entries, 1):
        blocks.append(f"{idx}\n{format_srt_time(start)} --> {format_srt_time(end)}\n{text.strip()}")
    path.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")


def media_duration(path: Path) -> float:
    raw = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], capture=True)
    return float(raw.strip())


def audio_peak_dbfs(path: Path) -> float:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", "volumedetect", "-f", "null", os.devnull,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    match = re.search(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", result.stderr)
    if not match or match.group(1) == "-inf":
        raise ValueError(f"오디오 피크를 측정할 수 없습니다: {path}")
    return float(match.group(1))


def narration_duration(text: str, content_duration: float, config: dict[str, Any]) -> float:
    """Return a brisk movie-review narration window instead of filling a whole clip."""
    explicit = config.get("narration_duration_sec")
    if explicit is not None:
        return min(content_duration, float(explicit))
    spoken_chars = len(re.sub(r"[\s,.!?·…'\"“”‘’]", "", text))
    chars_per_sec = float(config.get("narration_chars_per_sec", 5.2))
    estimated = spoken_chars / max(chars_per_sec, 0.1) + 0.8
    minimum = float(config.get("narration_min_sec", 2.6))
    maximum = float(config.get("narration_max_sec", 6.0))
    return min(content_duration, max(minimum, min(maximum, estimated)))


def narration_audio_path(order: int) -> Path:
    return CAPCUT / "narration_audio" / f"clip_{order:03d}.mp3"


def load_sfx_manifest() -> dict[str, Any]:
    if not SFX_MANIFEST.exists():
        raise FileNotFoundError(f"효과음 manifest를 찾을 수 없습니다: {SFX_MANIFEST}")
    return json.loads(SFX_MANIFEST.read_text(encoding="utf-8"))


def segment_sfx_asset(seg: dict[str, Any]) -> tuple[str, Path, dict[str, Any]] | None:
    asset_id = str(seg.get("narration_sfx_preroll", "none")).strip() or "none"
    if asset_id == "none":
        return None
    manifest = load_sfx_manifest()
    spec = manifest.get("assets", {}).get(asset_id)
    if not spec:
        raise ValueError(f"알 수 없는 나레이션 프리롤 효과음입니다: {asset_id}")
    # The asset sits beside whichever manifest was loaded, so a project using the shared
    # library gets the shared wav files rather than being asked for its own copies.
    # processed_path is written relative to the root that contains assets/, three levels
    # above the manifest itself.
    path = SFX_MANIFEST.parents[3] / str(spec["processed_path"])
    if not path.exists():
        path = ROOT / str(spec["processed_path"])
    if not path.exists():
        raise FileNotFoundError(f"프리롤 효과음 파일을 찾을 수 없습니다: {path}")
    expected_hash = str(spec.get("processed_sha256", "")).upper()
    if expected_hash:
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        if actual_hash != expected_hash:
            raise ValueError(f"프리롤 효과음 해시 불일치: {asset_id}")
    return asset_id, path, spec


def validate_sfx_plan(plan: dict[str, Any], config: dict[str, Any] | None = None) -> None:
    segments = plan.get("segments", [])
    if not any(str(seg.get("narration_sfx_preroll", "none")).strip() not in ("", "none") for seg in segments):
        return
    manifest = load_sfx_manifest()
    rules = manifest.get("global_rules", {})
    global_limit = int((config or {}).get("narration_sfx_max_uses", rules.get("max_uses_per_19_25_min_review", 8)))
    minimum_any = float(rules.get("minimum_seconds_between_any_sfx", 25))
    minimum_same = float(rules.get("minimum_seconds_before_reusing_same_sfx", 90))
    tail_min = float((config or {}).get("narration_sfx_tail_min_sec", rules.get("tail_under_narration_min_seconds", 0.10)))
    tail_max = float((config or {}).get("narration_sfx_tail_max_sec", rules.get("tail_under_narration_max_seconds", 0.30)))
    subtitle_cues: list[Cue] = []
    subtitle_value = (config or {}).get("subtitle")
    if subtitle_value:
        subtitle_path = Path(str(subtitle_value))
        if not subtitle_path.is_absolute():
            subtitle_path = ROOT / subtitle_path
        if not subtitle_path.exists():
            raise FileNotFoundError(f"효과음 대사 충돌 검사에 필요한 SRT가 없습니다: {subtitle_path}")
        subtitle_cues = parse_srt(subtitle_path)
    counts: dict[str, int] = {}
    timeline = 0.0
    last_any: float | None = None
    last_by_id: dict[str, float] = {}
    total = 0
    for seg in segments:
        asset = segment_sfx_asset(seg)
        if asset:
            asset_id, _, spec = asset
            if not str(seg.get("narration", "")).strip():
                raise ValueError(f"order {seg.get('order')}: 나레이션 없는 구간에 프리롤 효과음이 있습니다.")
            lead = float(seg.get("narration_sfx_lead_seconds", 0.0) or 0.0)
            if not 0.15 <= lead <= 1.0:
                raise ValueError(f"order {seg.get('order')}: 효과음 lead는 0.15~1.0초여야 합니다.")
            rationale = str(seg.get("narration_sfx_rationale", "")).strip()
            if not rationale:
                raise ValueError(f"order {seg.get('order')}: 효과음 장면 선택 근거가 없습니다.")
            scene_protection = str(seg.get("narration_scene_protection", "unreviewed")).strip() or "unreviewed"
            if scene_protection != "clear":
                raise ValueError(
                    f"order {seg.get('order')}: 보호 장면({scene_protection})에는 프리롤 효과음을 사용할 수 없습니다."
                )
            asset_duration = float(spec.get("duration_seconds", 0.0))
            tail_overlap = asset_duration - lead
            if not tail_min - 1e-9 <= tail_overlap <= tail_max + 1e-9:
                raise ValueError(
                    f"order {seg.get('order')}: {asset_id} 꼬리 겹침이 {tail_overlap:.3f}초입니다. "
                    f"허용 범위는 {tail_min:.2f}~{tail_max:.2f}초입니다."
                )
            source_start = float(seg["source_start"])
            preroll_end = source_start + lead
            dialogue_hits = [
                cue for cue in subtitle_cues
                if cue.start < preroll_end - 1e-9 and cue.end > source_start + 1e-9
            ]
            if dialogue_hits:
                sample = dialogue_hits[0]
                raise ValueError(
                    f"order {seg.get('order')}: 효과음 프리롤이 영화 대사와 겹칩니다 "
                    f"({sample.start:.3f}~{sample.end:.3f}, {sample.text})."
                )
            if last_any is not None and timeline - last_any < minimum_any:
                raise ValueError(
                    f"order {seg.get('order')}: 직전 효과음과 {timeline - last_any:.1f}초 간격입니다. "
                    f"최소 {minimum_any:g}초가 필요합니다."
                )
            if asset_id in last_by_id and timeline - last_by_id[asset_id] < minimum_same:
                raise ValueError(
                    f"order {seg.get('order')}: {asset_id} 재사용 간격이 {timeline - last_by_id[asset_id]:.1f}초입니다. "
                    f"최소 {minimum_same:g}초가 필요합니다."
                )
            counts[asset_id] = counts.get(asset_id, 0) + 1
            maximum = int(spec.get("max_uses_per_review", global_limit))
            if counts[asset_id] > maximum:
                raise ValueError(f"효과음 {asset_id}가 사용 제한 {maximum}회를 넘습니다.")
            total += 1
            if total > global_limit:
                raise ValueError(f"프리롤 효과음이 전체 제한 {global_limit}회를 넘습니다.")
            last_any = timeline
            last_by_id[asset_id] = timeline
        timeline += float(seg["source_end"]) - float(seg["source_start"])


def segment_narration_duration(seg: dict[str, Any], content_duration: float, config: dict[str, Any]) -> float:
    text = str(seg.get("narration", "")).strip()
    if not text:
        return 0.0
    audio = narration_audio_path(int(seg["order"]))
    if audio.exists():
        return min(content_duration, media_duration(audio) + 0.15)
    return narration_duration(text, content_duration, config)


def segment_narration_timing(
    seg: dict[str, Any], content_duration: float, config: dict[str, Any]
) -> tuple[float, float, tuple[str, Path, dict[str, Any]] | None]:
    text = str(seg.get("narration", "")).strip()
    if not text:
        return 0.0, 0.0, None
    sfx_asset = segment_sfx_asset(seg)
    lead = float(seg.get("narration_sfx_lead_seconds", 0.0) or 0.0) if sfx_asset else 0.0
    lead = min(max(0.0, lead), max(0.0, content_duration - 0.2))
    narration_len = segment_narration_duration(seg, max(0.0, content_duration - lead), config)
    return lead, narration_len, sfx_asset


def split_narration_cues(start: float, duration: float, text: str) -> list[tuple[float, float, str]]:
    """Keep a narration block continuous while showing one short sentence at a time."""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    if len(sentences) <= 1:
        return [(start, start + duration, text)]
    weights = [max(1, len(re.sub(r"\s+", "", sentence))) for sentence in sentences]
    total_weight = sum(weights)
    cues: list[tuple[float, float, str]] = []
    cursor = start
    for index, (sentence, weight) in enumerate(zip(sentences, weights)):
        end = start + duration if index == len(sentences) - 1 else cursor + duration * weight / total_weight
        cues.append((cursor, end, sentence))
        cursor = end
    return cues


def build_sfx_handoff(
    config: dict[str, Any], segments: list[dict[str, Any]], sfx_rows: list[dict[str, Any]], timeline_duration: float
) -> None:
    if not sfx_rows:
        return
    package = CAPCUT / "sfx_preroll"
    package.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SFX_MANIFEST, package / "manifest.json")
    manifest = load_sfx_manifest()
    gain = float(config.get("narration_sfx_mix_gain", manifest.get("global_rules", {}).get("default_mix_gain_linear", 0.85)))
    if not 0 < gain <= 1:
        raise ValueError("narration_sfx_mix_gain은 0보다 크고 1 이하여야 합니다.")
    limiter = float(config.get("audio_limiter", 0.891251))
    inputs = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-t", f"{timeline_duration:.6f}", "-i", "anullsrc=r=48000:cl=stereo",
    ]
    filters: list[str] = []
    labels = ["[0:a]"]
    copied: set[Path] = set()
    for input_index, row in enumerate(sfx_rows, 1):
        seg = segments[int(row["order"]) - 1]
        asset = segment_sfx_asset(seg)
        assert asset is not None
        _, asset_path, _ = asset
        inputs.extend(["-i", str(asset_path)])
        delay_ms = int(round(float(row["sfx_start"]) * 1000))
        label = f"sfx{input_index}"
        filters.append(
            f"[{input_index}:a]aresample=48000,volume={gain:.6f},adelay={delay_ms}:all=1[{label}]"
        )
        labels.append(f"[{label}]")
        if asset_path not in copied:
            shutil.copy2(asset_path, package / asset_path.name)
            copied.add(asset_path)
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0,"
        + f"alimiter=limit={limiter:.6f}:level=false,atrim=duration={timeline_duration:.6f}[stem]"
    )
    stem = package / "sfx_preroll_stem.m4a"
    run([
        *inputs, "-filter_complex", ";".join(filters), "-map", "[stem]",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-y", str(stem),
    ])
    measured_duration = media_duration(stem)
    if abs(measured_duration - timeline_duration) > 0.05:
        raise ValueError(
            f"SFX 스템 길이 불일치: expected={timeline_duration:.6f}, actual={measured_duration:.6f}"
        )
    measured_peak = audio_peak_dbfs(stem)
    maximum_peak = float(config.get("narration_sfx_max_peak_dbfs", -14.0))
    if measured_peak > maximum_peak:
        raise ValueError(f"SFX 스템 피크가 너무 큽니다: {measured_peak:.1f} dBFS > {maximum_peak:.1f} dBFS")
    placements = [float(row["sfx_start"]) for row in sfx_rows]
    tails = [float(row["tail_under_narration_seconds"]) for row in sfx_rows]
    qa = {
        "status": "pass",
        "use_count": len(sfx_rows),
        "timeline_duration_seconds": round(timeline_duration, 6),
        "measured_stem_duration_seconds": round(measured_duration, 6),
        "measured_stem_peak_dbfs": measured_peak,
        "maximum_allowed_peak_dbfs": maximum_peak,
        "mix_gain_linear": gain,
        "mix_gain_db": round(20 * math.log10(gain), 2),
        "minimum_spacing_seconds": round(min((b - a for a, b in zip(placements, placements[1:])), default=0.0), 3),
        "movie_dialogue_overlap_count": 0,
        "tail_overlap_min_seconds": round(min(tails), 3),
        "tail_overlap_max_seconds": round(max(tails), 3),
        "stem": str(stem.relative_to(ROOT)).replace("\\", "/"),
        "render_bake_sfx_preroll": bool(config.get("render_bake_sfx_preroll", False)),
    }
    (package / "SFX_PREROLL_QA.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (package / "README.md").write_text(
        "# SFX_PREROLL handoff\n\n"
        "Import `sfx_preroll_stem.m4a` on one separate CapCut audio track at 00:00:00.000. "
        "Keep it at 0 dB because the approved low-level assets and project mix gain are already applied.\n\n"
        "Use `../sfx_timeline.csv` only when individual WAV placement is needed. "
        "Do not import both the stem and individual effects.\n",
        encoding="utf-8",
    )


def build_caption_tracks(config: dict[str, Any], plan: dict[str, Any]) -> None:
    """Remap the existing movie SRT onto the rendered cut timeline.

    This is not transcription. Original cues are clipped and shifted for segments
    whose movie audio is preserved. A narration only occupies its short calculated
    window; the movie dialogue captions resume immediately after that window.
    Actual encoded clip durations are used for cumulative timeline offsets so AAC
    padding does not create progressive drift in CapCut.
    """
    CAPCUT.mkdir(parents=True, exist_ok=True)
    clips_dir = CAPCUT / str(config.get("clips_dir", "clips"))
    source_cues = parse_srt(ROOT / config["subtitle"])
    movie_entries: list[tuple[float, float, str]] = []
    narration_entries: list[tuple[float, float, str]] = []
    combined_entries: list[tuple[float, float, str]] = []
    csv_rows: list[dict[str, Any]] = []
    timeline = 0.0

    segments = plan["segments"]
    for seg_index, seg in enumerate(segments):
        order = int(seg["order"])
        clip = clips_dir / f"clip_{order:03d}_{seg['kind']}.mp4"
        if not clip.exists():
            raise FileNotFoundError(f"편집표의 정확한 클립을 찾을 수 없습니다: {clip.name}")
        encoded_duration = media_duration(clip)
        content_duration = min(encoded_duration, float(seg["source_end"]) - float(seg["source_start"]))
        timeline_end = timeline + encoded_duration
        text = str(seg.get("narration", "")).strip()

        source_start = float(seg["source_start"])
        source_end = float(seg["source_end"])
        narration_end_source = source_start
        if text:
            narration_lead, narration_len, sfx_asset = segment_narration_timing(seg, content_duration, config)
            entries = split_narration_cues(timeline + narration_lead, narration_len, text)
            narration_entries.extend(entries)
            combined_entries.extend(entries)
            narration_end_source = source_start + narration_lead + narration_len + float(config.get("caption_resume_gap_sec", 0.12))
        else:
            narration_lead, narration_len, sfx_asset = 0.0, 0.0, None

        # A narration-pass candidate keeps the movie bed even when its review
        # narration is later removed. In that case movie captions must return
        # instead of disappearing with the rejected narration.
        if bool(seg.get("keep_original_audio")) or text or "narration_original" in seg:
            for cue in source_cues:
                if cue.start >= source_end:
                    break
                if cue.end <= narration_end_source:
                    continue
                mapped_start = timeline + max(cue.start, narration_end_source) - source_start
                mapped_end = timeline + min(cue.end, source_end) - source_start
                if mapped_end - mapped_start >= 0.2 and cue.text.strip():
                    entry = (mapped_start, mapped_end, cue.text.strip())
                    movie_entries.append(entry)
                    combined_entries.append(entry)

        previous_caption_end = max(
            (cue.end for cue in source_cues if cue.end <= source_start + 1e-9), default=0.0
        )
        sfx_duration = float(sfx_asset[2].get("duration_seconds", 0.0)) if sfx_asset else 0.0
        tail_overlap = max(0.0, sfx_duration - narration_lead) if sfx_asset else 0.0
        csv_rows.append({
            "order": order,
            "timeline_start": round(timeline, 3),
            "timeline_end": round(timeline_end, 3),
            "source_start": seg["source_start"],
            "source_end": seg["source_end"],
            "kind": seg["kind"],
            "story_beat": seg["story_beat"],
            "audio_level": seg["audio_level"],
            "narration": text,
            "narration_start": round(timeline + narration_lead, 3) if text else "",
            "sfx_preroll": sfx_asset[0] if sfx_asset else "none",
            "sfx_start": round(timeline, 3) if sfx_asset else "",
            "sfx_lead_seconds": round(narration_lead, 3) if sfx_asset else 0,
            "sfx_duration_seconds": round(sfx_duration, 3) if sfx_asset else 0,
            "tail_under_narration_seconds": round(tail_overlap, 3) if sfx_asset else 0,
            "dialogue_clearance_seconds": round(source_start - previous_caption_end, 3) if sfx_asset else "",
            "scene_protection": seg.get("narration_scene_protection", "unreviewed"),
            "sfx_rationale": seg.get("narration_sfx_rationale", ""),
            "mix_gain_linear": float(config.get("narration_sfx_mix_gain", 0.85)) if sfx_asset else "",
            "purpose": seg["purpose"],
            "clip": str(clip.relative_to(CAPCUT)),
        })
        timeline = timeline_end

    write_srt(narration_entries, OUTPUT / "narration.srt")
    write_srt(movie_entries, OUTPUT / "movie_captions.srt")
    write_srt(combined_entries, OUTPUT / "captions_combined.srt")
    (OUTPUT / "narration.txt").write_text(
        "\n\n".join(f"[{format_srt_time(start)}] {text}" for start, _, text in narration_entries) + "\n",
        encoding="utf-8",
    )
    for name in ("narration.srt", "movie_captions.srt", "captions_combined.srt"):
        shutil.copy2(OUTPUT / name, CAPCUT / name)
    with (CAPCUT / "timeline.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    sfx_rows = [row for row in csv_rows if row["sfx_preroll"] != "none"]
    with (CAPCUT / "sfx_timeline.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "order", "sfx_preroll", "sfx_start", "narration_start", "sfx_lead_seconds",
            "sfx_duration_seconds", "tail_under_narration_seconds", "dialogue_clearance_seconds",
            "scene_protection", "sfx_rationale", "mix_gain_linear", "purpose",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sfx_rows)
    build_sfx_handoff(config, segments, sfx_rows, timeline)
    print(
        f"자막 완료: 영화 대사 {len(movie_entries)}개, 나레이션 {len(narration_entries)}개, "
        f"통합 {len(combined_entries)}개",
        flush=True,
    )


def master_audio(config: dict[str, Any], video: Path) -> None:
    """Bring the concatenated master to a delivery loudness without touching the picture.

    Per-clip mixing sets the balance between narration and film, and it holds: measured on
    The Devil All The Time, narration blocks sat 7.1 dB above film blocks, which is the
    target. What per-clip mixing cannot set is the loudness of the whole, and the first
    master came out at -20.37 LUFS - below the delivery floor of -20 with 3.3 dB of peak
    headroom going unused.

    Two passes, and `linear=true` so the correction is one static gain across the programme.
    Dynamic normalisation would re-balance quiet passages against loud ones and undo the
    ducking. `lra` is set above the measured range for the same reason: loudnorm silently
    drops out of linear mode when the programme is wider than the target.
    """
    target = config.get("master_loudness_lufs")
    if target is None:
        return
    target = float(target)
    peak_ceiling = float(config.get("master_true_peak_dbtp", -1.5))
    measured = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
         "-af", f"loudnorm=I={target}:TP={peak_ceiling}:LRA=25:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    stats = json.loads(measured[measured.rindex("{"):measured.rindex("}") + 1])
    second_pass = (
        f"loudnorm=I={target}:TP={peak_ceiling}:LRA=25:linear=true"
        f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
        f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
    )
    mastered = video.with_name(video.stem + ".mastered.mp4")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
         "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", second_pass,
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", "-y", str(mastered)])
    mastered.replace(video)
    print(f"마스터링: {stats['input_i']} -> {target} LUFS, 트루피크 한계 {peak_ceiling} dBTP",
          flush=True)


def render(config: dict[str, Any]) -> None:
    preflight(config)
    video = ROOT / config["video"]
    source_duration = float(ffprobe(video)["format"]["duration"])
    plan = validate_plan(OUTPUT / "edit_plan.json", source_duration, float(config.get("target_duration_sec", 1320)))
    RENDER.mkdir(parents=True, exist_ok=True)
    CAPCUT.mkdir(parents=True, exist_ok=True)
    clips_dir = CAPCUT / str(config.get("clips_dir", "clips"))
    clips_dir.mkdir(parents=True, exist_ok=True)

    width = int(config.get("render_width", 1920))
    height = int(config.get("render_height", 1080))
    fps = int(config.get("render_fps", 30))
    video_preset = str(config.get("render_preset", "veryfast"))
    video_crf = str(config.get("render_crf", 20))
    video_codec = str(config.get("render_video_codec", "libx264"))
    input_options = ["-hwaccel", str(config["render_hwaccel"])] if config.get("render_hwaccel") else []
    if video_codec == "h264_nvenc":
        video_encode_options = ["-c:v", video_codec, "-preset", video_preset, "-cq", video_crf, "-b:v", "0"]
    else:
        video_encode_options = ["-c:v", video_codec, "-preset", video_preset, "-crf", video_crf]
    concat_lines: list[str] = []
    narration: list[tuple[float, float, str]] = []
    timeline = 0.0
    csv_rows: list[dict[str, Any]] = []

    transition_fade = float(config.get("transition_fade_sec", 0.0))
    transition_gap_threshold = float(config.get("transition_gap_threshold_sec", 120.0))
    segments = plan["segments"]
    for seg_index, seg in enumerate(segments):
        order = int(seg["order"])
        start, end = float(seg["source_start"]), float(seg["source_end"])
        duration = end - start
        clip = clips_dir / f"clip_{order:03d}_{seg['kind']}.mp4"
        previous_gap = start - float(segments[seg_index - 1]["source_end"]) if seg_index else 0.0
        next_gap = float(segments[seg_index + 1]["source_start"]) - end if seg_index + 1 < len(segments) else 0.0
        fade_in = transition_fade > 0 and seg_index > 0 and previous_gap >= transition_gap_threshold
        fade_out = transition_fade > 0 and seg_index + 1 < len(segments) and next_gap >= transition_gap_threshold
        video_filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            f"fps={fps}",
            "format=yuv420p",
        ]
        audio_fades: list[str] = []
        if fade_in:
            video_filters.append(f"fade=t=in:st=0:d={transition_fade:.3f}")
            audio_fades.append(f"afade=t=in:st=0:d={transition_fade:.3f}")
        if fade_out:
            fade_start = max(0.0, duration - transition_fade)
            video_filters.append(f"fade=t=out:st={fade_start:.3f}:d={transition_fade:.3f}")
            audio_fades.append(f"afade=t=out:st={fade_start:.3f}:d={transition_fade:.3f}")
        vf = ",".join(video_filters)
        level = float(seg["audio_level"])
        text = str(seg.get("narration", "")).strip()
        narration_lead, narration_len, sfx_asset = segment_narration_timing(seg, duration, config)
        tts_audio = narration_audio_path(order)
        duck_without_voice = bool(config.get("preview_duck_without_voice", False))
        should_duck = bool(text and (tts_audio.exists() or duck_without_voice))
        if should_duck:
            normal_level = float(config.get("post_narration_audio_level", 0.96))
            voice_start = narration_lead
            voice_end = narration_lead + narration_len
            attack = min(float(config.get("audio_duck_attack_sec", 0.35)), narration_len / 3)
            release = min(float(config.get("audio_duck_release_sec", 0.55)), narration_len / 3)
            release_start = max(voice_start, voice_end - release)
            if voice_start > 0:
                attack_start = max(0.0, voice_start - attack)
                attack_duration = max(0.001, voice_start - attack_start)
                volume_curve = (
                    f"if(lt(t,{attack_start:.3f}),{normal_level:.4f},"
                    f"if(lt(t,{voice_start:.3f}),"
                    f"{normal_level:.4f}+({level:.4f}-{normal_level:.4f})*((t-{attack_start:.3f})/{attack_duration:.3f}),"
                    f"if(lt(t,{release_start:.3f}),{level:.4f},"
                    f"if(lt(t,{voice_end:.3f}),"
                    f"{level:.4f}+({normal_level:.4f}-{level:.4f})*((t-{release_start:.3f})/{release:.3f}),"
                    f"{normal_level:.4f}))))"
                )
            else:
                release_start = max(attack, narration_len - release)
                volume_curve = (
                    f"if(lt(t,{attack:.3f}),"
                    f"{normal_level:.4f}+({level:.4f}-{normal_level:.4f})*(t/{attack:.3f}),"
                    f"if(lt(t,{release_start:.3f}),{level:.4f},"
                    f"if(lt(t,{narration_len:.3f}),"
                    f"{level:.4f}+({normal_level:.4f}-{level:.4f})*((t-{release_start:.3f})/{release:.3f}),"
                    f"{normal_level:.4f})))"
                )
            audio_filter = (
                f"volume='{volume_curve}':eval=frame,"
                "aresample=48000"
            )
        else:
            # A narration block whose line was dropped has nothing to duck under, so it
            # plays at the film's own level. Falling back to the block's ducked level held
            # the film 9.5 dB down for seven seconds with silence over it - 63 seconds of
            # this review, four blocks of it consecutive across the preacher's confession,
            # which is the one stretch the film is supposed to carry alone.
            open_level = float(config.get("post_narration_audio_level", 0.96))
            narration_block = str(seg.get("kind", "")) == "narration"
            unducked_level = open_level if (text or narration_block) else level
            audio_filter = f"volume={unducked_level:.3f},aresample=48000"
        # Optional explicit downmix, applied before anything else touches the bed.
        # ffmpeg's default 5.1 -> stereo drops the centre channel by 3 dB and folds the
        # surrounds in, which costs dialogue exactly where a review needs it: measured on a
        # 5.1 source, the default landed 4.2 dB under a centre-weighted pan. Empty by
        # default so stereo sources and existing projects are untouched.
        downmix = str(config.get("source_audio_downmix", "")).strip()
        if downmix:
            audio_filter = f"{downmix},{audio_filter}"
        audio_fade_filter = ("," + ",".join(audio_fades)) if audio_fades else ""
        mix_gain = float(config.get("narration_sfx_mix_gain", 0.85))
        limiter = float(config.get("audio_limiter", 0.891251))
        mix_tail = f",alimiter=limit={limiter:.6f}:level=false{audio_fade_filter}[a]"
        if text and tts_audio.exists():
            voice_delay_ms = int(round(narration_lead * 1000))
            # The voice went in at unity, which put the narration 5.4 dB above the film's own
            # dialogue and 9.7 dB above the film blocks as a whole - loud enough that every
            # narration block read as a jump in level. The gain is configurable so it can be
            # set against measurement rather than by re-encoding to taste.
            voice_gain = float(config.get("narration_voice_gain", 1.0))
            voice_filter = f"[1:a:0]aresample=48000,volume={voice_gain:.4f}"
            if voice_delay_ms:
                voice_filter += f",adelay={voice_delay_ms}:all=1"
            voice_filter += "[vo];"
            bake_sfx = bool(sfx_asset and config.get("render_bake_sfx_preroll", False))
            sfx_input = ["-i", str(sfx_asset[1])] if bake_sfx else []
            if bake_sfx:
                mix_filter = (
                    f"[0:v:0]{vf}[v];[0:a:0]{audio_filter}[bed];{voice_filter}"
                    f"[2:a:0]aresample=48000,volume={mix_gain:.6f}[fx];"
                    f"[bed][fx][vo]amix=inputs=3:duration=first:dropout_transition=0:normalize=0{mix_tail}"
                )
            else:
                mix_filter = (
                    f"[0:v:0]{vf}[v];[0:a:0]{audio_filter}[bed];{voice_filter}"
                    f"[bed][vo]amix=inputs=2:duration=first:dropout_transition=0:normalize=0{mix_tail}"
                )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", *input_options, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                "-i", str(video), "-i", str(tts_audio), *sfx_input,
                "-filter_complex", mix_filter,
                "-map", "[v]", "-map", "[a]", *video_encode_options,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-y", str(clip),
            ])
        elif sfx_asset and bool(config.get("preview_sfx_without_voice", False)):
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", *input_options, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                "-i", str(video), "-i", str(sfx_asset[1]), "-filter_complex",
                f"[0:v:0]{vf}[v];[0:a:0]{audio_filter}[bed];[1:a:0]aresample=48000,volume={mix_gain:.6f}[fx];"
                f"[bed][fx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0{mix_tail}",
                "-map", "[v]", "-map", "[a]", *video_encode_options,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-y", str(clip),
            ])
        else:
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", *input_options, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                "-i", str(video), "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
                "-af", audio_filter + audio_fade_filter, *video_encode_options,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-y", str(clip),
            ])
        concat_lines.append(f"file '{clip.as_posix()}'")
        if text:
            narration.append((timeline + narration_lead, timeline + narration_lead + narration_len, text))
        csv_rows.append({
            "order": order, "timeline_start": round(timeline, 3), "timeline_end": round(timeline + duration, 3),
            "source_start": start, "source_end": end, "kind": seg["kind"], "story_beat": seg["story_beat"],
            "audio_level": level, "narration": text,
            "narration_start": round(timeline + narration_lead, 3) if text else "",
            "sfx_preroll": sfx_asset[0] if sfx_asset else "none",
            "sfx_start": round(timeline, 3) if sfx_asset else "",
            "sfx_lead_seconds": round(narration_lead, 3) if sfx_asset else 0,
            "purpose": seg["purpose"], "clip": str(clip.relative_to(CAPCUT)),
        })
        timeline += duration

    concat_file = RENDER / "concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    output_video = str(config.get("output_video", "rough_cut.mp4"))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", "-y", str(OUTPUT / output_video)])
    master_audio(config, OUTPUT / output_video)
    shutil.copy2(OUTPUT / "edit_plan.json", CAPCUT / "edit_plan.json")
    build_caption_tracks(config, plan)
    # The instructions have to describe the file that was actually produced. A render that
    # found the voice files baked them into every clip, so telling the editor to lay the same
    # mp3s on a track would play the narration twice - which the old wording did, because it
    # was written when the master came out silent.
    voice_baked = any(
        narration_audio_path(int(s["order"])).exists() and str(s.get("narration", "")).strip()
        for s in plan["segments"]
    )
    sfx_baked = bool(config.get("render_bake_sfx_preroll", False))
    steps = [f"상위 output 폴더의 {output_video}를 CapCut으로 가져옵니다."
             + (" 나레이션 음성이 이미 믹스되어 있습니다." if voice_baked else ""),
             "movie_captions.srt와 narration.srt만 각각 별도 자막 트랙으로 가져옵니다. "
             "captions_combined.srt는 QA용이며 가져오지 않습니다.",
             "captions_styled.ass는 이전 리뷰와 같은 자막 디자인이며, CapCut 대신 이미 "
             "구워진 *_captioned.mp4를 그대로 쓸 때 참고합니다."]
    if voice_baked:
        steps.append("narration_audio의 mp3를 오디오 트랙에 다시 얹지 마십시오. "
                     "러프컷에 이미 들어 있어 나레이션이 두 번 들립니다. "
                     "다시 믹스할 때만 사용합니다.")
    else:
        steps.append("narration_audio 폴더의 승인 음성을 REVIEW_NARRATION 오디오 트랙에 "
                     "배치합니다. CapCut 임의 TTS로 대체하지 않습니다.")
    steps.append("나레이션이 끝나면 같은 클립 안에서 원음과 영화 자막이 자동으로 복귀합니다.")
    if sfx_baked:
        steps.append("프리롤 효과음도 러프컷에 포함되어 있으므로 sfx_preroll 스템을 "
                     "추가하지 않습니다.")
    else:
        steps.append("프리롤 효과음이 선택된 경우 sfx_preroll/sfx_preroll_stem.m4a를 "
                     "타임라인 0초에 SFX_PREROLL 별도 트랙으로 한 번만 가져옵니다.")
    steps.append("개별 WAV를 직접 배치할 때만 sfx_timeline.csv를 사용하며 스템과 동시에 "
                 "쓰지 않습니다.")
    steps.append("필요하면 clips 폴더의 개별 원본 클립과 timeline.csv로 컷을 교체합니다.")
    (CAPCUT / "IMPORT_README.txt").write_text(
        "".join(f"{i}. {step}\n" for i, step in enumerate(steps, start=1)), encoding="utf-8")
    print(f"완료: {OUTPUT / output_video} ({timeline:.1f}초)")


def main() -> int:
    parser = argparse.ArgumentParser(description="영화 리뷰 자동 편집 + CapCut 인계 파이프라인")
    parser.add_argument("stage", choices=("analyze", "plan", "preflight", "render", "captions", "all"), nargs="?", default="all")
    args = parser.parse_args()
    config = load_config()
    if args.stage in ("analyze", "all"):
        build_analysis(config)
    if args.stage in ("plan", "all"):
        build_plan(config)
    if args.stage == "preflight":
        preflight(config)
    if args.stage in ("render", "all"):
        render(config)
    if args.stage == "captions":
        validate_story_map_gate(config, require_render_ready=False)
        source_duration = float(ffprobe(ROOT / config["video"])["format"]["duration"])
        plan = validate_plan(OUTPUT / "edit_plan.json", source_duration, float(config.get("target_duration_sec", 1320)))
        build_caption_tracks(config, plan)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"외부 명령 실패(exit={exc.returncode})", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
