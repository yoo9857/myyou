from __future__ import annotations

import argparse
import csv
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


ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
ANALYSIS = WORK / "analysis"
SHEETS = WORK / "contact_sheets"
RENDER = WORK / "render"
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"


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
                "당신은 한국 영화 리뷰의 스토리 에디터다. 아래는 영화의 한 구간에 포함된 "
                "3분 단위 한국어 대사 전문이다. 파일을 열거나 도구를 사용하지 말고 제공된 대사만 분석하라. "
                "인물, 사건, 갈등 변화, 반전, 다음 구간으로 이어지는 의문을 시간순으로 정리하라. "
                "events의 start/end는 제공된 구간 안의 초 단위 원본 시간이다. key_dialogue는 실제 제공된 대사를 "
                "짧게 옮기고 대략적인 해당 3분 범위 안 시간으로 지정하라. JSON 스키마만 만족하라.\n\n"
                + "\n\n".join(selected)
            )
            codex_exec(codex, ROOT / "schemas" / "chunk_outline.schema.json", chunk_output, prompt)
        merged_chunks = "\n\n".join(path.read_text(encoding="utf-8") for path in chunk_outputs)
        merge_prompt = (
            "당신은 한국 영화 리뷰의 수석 스토리 에디터다. 아래 세 구간 분석을 하나의 정확한 영화 이야기 지도로 "
            "합쳐라. 파일이나 도구는 사용하지 마라. 중복 사건을 합치고 설정, 촉발 사건, 상승, 중반 전환, 반전, "
            "위기, 클라이맥스, 해결이 드러나는 8~20개 비트를 만든다. key_dialogues는 제공된 실제 대사만 사용한다. "
            "sheet_numbers는 시간 0~599초=1, 600~1199초=2처럼 계산한다. JSON만 출력하라.\n\n"
            + merged_chunks
        )
        codex_exec(codex, ROOT / "schemas" / "story_outline.schema.json", outline, merge_prompt)
    plan_prompt_template = (ROOT / "prompts" / "edit_plan.md").read_text(encoding="utf-8")
    plan_prompt = (
        plan_prompt_template
        + "\n\n이번 호출에서는 파일이나 도구를 사용하지 마라. 아래 제공된 config와 story_outline만으로 편집표를 작성하라. "
        "각 비트의 시간 범위 안에서 서로 겹치지 않는 원본 클립을 배분하고, 전체 클립 길이 합계를 1,260~1,380초로 맞춰라. "
        "콜드 오픈 외에는 source_start 오름차순을 지킨다. 실제 대사 후보 주변은 movie_dialogue로, 나머지는 narration으로 구성한다.\n\n"
        "CONFIG:\n" + json.dumps(config, ensure_ascii=False, indent=2)
        + "\n\nSTORY_OUTLINE:\n" + outline.read_text(encoding="utf-8")
    )
    codex_exec(
        codex, ROOT / "schemas" / "edit_plan.schema.json", OUTPUT / "edit_plan.json",
        plan_prompt,
    )
    validate_plan(
        OUTPUT / "edit_plan.json",
        float(ffprobe(ROOT / config["video"])["format"]["duration"]),
        float(config.get("target_duration_sec", 1320)),
    )


def validate_plan(path: Path, source_duration: float, target_duration: float = 1320) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    segments = plan.get("segments", [])
    if not 45 <= len(segments) <= 140:
        raise ValueError("편집표 segments 수가 45~140 범위가 아닙니다.")
    expected = 1
    total = 0.0
    used: list[tuple[float, float]] = []
    for seg in segments:
        if seg["order"] != expected:
            raise ValueError("segment order는 1부터 연속이어야 합니다.")
        start, end = float(seg["source_start"]), float(seg["source_end"])
        if not (0 <= start < end <= source_duration + 0.1):
            raise ValueError(f"잘못된 소스 구간: {start}~{end}")
        if end - start > 30:
            raise ValueError(f"30초를 넘는 클립: {start}~{end}")
        if any(max(start, a) < min(end, b) - 0.5 for a, b in used):
            raise ValueError(f"중복된 소스 구간: {start}~{end}")
        used.append((start, end))
        total += end - start
        expected += 1
    minimum = max(1140.0, target_duration - 180.0)
    maximum = min(1500.0, target_duration + 180.0)
    if not minimum <= total <= maximum:
        raise ValueError(f"실제 클립 합계 {total:.1f}초가 허용 범위({minimum:.0f}~{maximum:.0f}초)를 벗어났습니다.")
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

    for seg in plan["segments"]:
        order = int(seg["order"])
        matches = sorted(clips_dir.glob(f"clip_{order:03d}_*.mp4"))
        if len(matches) != 1:
            raise FileNotFoundError(f"clip_{order:03d} 파일을 하나만 찾을 수 있어야 합니다.")
        clip = matches[0]
        encoded_duration = media_duration(clip)
        content_duration = min(encoded_duration, float(seg["source_end"]) - float(seg["source_start"]))
        timeline_end = timeline + encoded_duration
        text = str(seg.get("narration", "")).strip()

        source_start = float(seg["source_start"])
        source_end = float(seg["source_end"])
        narration_end_source = source_start
        if text:
            narration_len = narration_duration(text, content_duration, config)
            entry = (timeline, timeline + narration_len, text)
            narration_entries.append(entry)
            combined_entries.append(entry)
            narration_end_source = source_start + narration_len + float(config.get("caption_resume_gap_sec", 0.12))

        if bool(seg.get("keep_original_audio")) or text:
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
    print(
        f"자막 완료: 영화 대사 {len(movie_entries)}개, 나레이션 {len(narration_entries)}개, "
        f"통합 {len(combined_entries)}개",
        flush=True,
    )


def render(config: dict[str, Any]) -> None:
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
    concat_lines: list[str] = []
    narration: list[tuple[float, float, str]] = []
    timeline = 0.0
    csv_rows: list[dict[str, Any]] = []

    for seg in plan["segments"]:
        order = int(seg["order"])
        start, end = float(seg["source_start"]), float(seg["source_end"])
        duration = end - start
        clip = clips_dir / f"clip_{order:03d}_{seg['kind']}.mp4"
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p"
        level = float(seg["audio_level"])
        text = str(seg.get("narration", "")).strip()
        narration_len = narration_duration(text, duration, config) if text else 0.0
        if text:
            normal_level = float(config.get("post_narration_audio_level", 0.96))
            duck_factor = level / max(normal_level, 0.001)
            audio_filter = (
                f"volume={normal_level:.3f},"
                f"volume={duck_factor:.4f}:enable='between(t,0,{narration_len:.3f})',"
                "aresample=48000"
            )
        else:
            audio_filter = f"volume={level:.3f},aresample=48000"
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
            "-i", str(video), "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
            "-af", audio_filter, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-y", str(clip),
        ])
        concat_lines.append(f"file '{clip.as_posix()}'")
        if text:
            narration.append((timeline, timeline + narration_len, text))
        csv_rows.append({
            "order": order, "timeline_start": round(timeline, 3), "timeline_end": round(timeline + duration, 3),
            "source_start": start, "source_end": end, "kind": seg["kind"], "story_beat": seg["story_beat"],
            "audio_level": level, "narration": text, "purpose": seg["purpose"], "clip": str(clip.relative_to(CAPCUT)),
        })
        timeline += duration

    concat_file = RENDER / "concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    output_video = str(config.get("output_video", "rough_cut.mp4"))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", "-y", str(OUTPUT / output_video)])
    shutil.copy2(OUTPUT / "edit_plan.json", CAPCUT / "edit_plan.json")
    build_caption_tracks(config, plan)
    (CAPCUT / "IMPORT_README.txt").write_text(
        f"1. 상위 output 폴더의 {output_video}와 이 폴더의 captions_combined.srt를 CapCut으로 가져옵니다.\n"
        "2. 음성 합성용으로는 narration.srt를 별도 가져와 원하는 한국어 남성 음성으로 텍스트 음성 변환합니다.\n"
        "3. movie_captions.srt는 기존 영화 SRT에서 원음 대사 구간만 새 타임라인으로 재매핑한 자막입니다.\n"
        "4. 나레이션이 끝나면 같은 클립 안에서 원음과 영화 자막이 자동으로 복귀합니다.\n"
        "5. 필요하면 clips 폴더의 개별 원본 클립과 timeline.csv로 컷을 교체합니다.\n",
        encoding="utf-8",
    )
    print(f"완료: {OUTPUT / output_video} ({timeline:.1f}초)")


def main() -> int:
    parser = argparse.ArgumentParser(description="영화 리뷰 자동 편집 + CapCut 인계 파이프라인")
    parser.add_argument("stage", choices=("analyze", "plan", "render", "captions", "all"), nargs="?", default="all")
    args = parser.parse_args()
    config = load_config()
    if args.stage in ("analyze", "all"):
        build_analysis(config)
    if args.stage in ("plan", "all"):
        build_plan(config)
    if args.stage in ("render", "all"):
        render(config)
    if args.stage == "captions":
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
