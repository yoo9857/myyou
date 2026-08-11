from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from pipeline import parse_srt, validate_story_map_gate

ROOT = Path(r"C:\cineyoutube\Constantine\story_review_v3")
SUBTITLE = (ROOT / ".." / "Constantine.2005.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].ko.srt").resolve()
OUTPUT = ROOT / "output"

# Natural story blocks, not evenly sampled intervals. Narration lines describe
# the visible action at the start of their owning block.
BLOCKS = [
    (98, 150, "setup", "폐허를 뒤지던 남자의 손에, 땅속 깊이 묻혀 있던 낡은 창 하나가 걸립니다.", "While searching the ruins, a man uncovers an ancient spear buried deep underground."),
    (269, 291, "setup", "한편, 퇴마사 콘스탄틴은 악령에게 붙잡힌 소녀의 방으로 들어섭니다.", "Meanwhile, exorcist John Constantine enters the room of a girl trapped by a demon."),
    (368, 403, "setup", "", ""),
    (439, 506, "setup", "", ""),
    (879, 912, "inciting_incident", "이번엔, 콘스탄틴 자신의 검사 결과입니다.", "This time, the test results belong to Constantine himself."),
    (940, 981, "inciting_incident", "", ""),
    (1010, 1037, "inciting_incident", "", ""),
    (1135, 1192, "rising_action", "콘스탄틴이 모아 온 무기와 성물을 관리하는 사람은, 오랜 친구 비먼입니다.", "Constantine's old friend Beeman looks after the weapons and relics he has collected."),
    (1295, 1338, "rising_action", "", ""),
    (1840, 1904, "rising_action", "답을 찾지 못한 콘스탄틴은 천사와 악마가 함께 드나드는 중립지대, 미드나이트의 클럽으로 향합니다.", "With no answers, Constantine heads to Midnite's club, neutral ground shared by angels and demons."),
    (2185, 2216, "rising_action", "", ""),
    (2380, 2432, "rising_action", "날갯소리를 들은 콘스탄틴은, 복도에 있어서는 안 될 무언가가 왔음을 직감합니다.", "Hearing wings, Constantine realizes that something forbidden has entered the corridor."),
    (2480, 2535, "rising_action", "콘스탄틴은 안젤라의 집으로 자리를 옮겨, 이사벨을 찾을 의식을 준비합니다.", "Constantine moves to Angela's home and begins preparing a ritual to find Isabel."),
    (2742, 2779, "rising_action", "의식이 시작되자, 콘스탄틴은 지옥으로 건너갑니다.", "As the ritual begins, Constantine crosses into hell."),
    (3060, 3128, "rising_action", "", ""),
    (3460.38, 3486.7, "reversal", "안젤라는 어린 시절, 자매끼리 메시지를 남기던 방법을 떠올립니다.", "Angela remembers how the sisters used to leave messages for each other as children."),
    (3486.7, 3555, "reversal", "", ""),
    (3640, 3713, "rising_action", "통화가 끊긴 직후, 콘스탄틴과 안젤라는 비먼의 은신처에 도착합니다.", "After the call cuts out, Constantine and Angela arrive at Beeman's hideout."),
    (3910, 3937, "rising_action", "", ""),
    (4190, 4238, "reversal", "안젤라는 비먼이 죽기 전 본 마지막 장면을 천천히 더듬기 시작합니다.", "Angela begins retracing the final images Beeman saw before he died."),
    (4340, 4422, "reversal", "흔적을 따라온 콘스탄틴은, 안젤라를 차에 남깁니다.", "Following the trail, Constantine leaves Angela in the car."),
    (4450, 4510, "reversal", "", ""),
    (4560, 4620, "reversal", "", ""),
    (4690, 4760, "crisis", "안젤라가 사라진 직후, 콘스탄틴은 미드나이트의 클럽으로 달려갑니다.", "As soon as Angela disappears, Constantine rushes to Midnite's club."),
    (4800, 4870, "crisis", "", ""),
    (5080, 5108, "crisis", "안젤라의 위치를 알아낸 콘스탄틴과 채즈는, 곧바로 병원으로 향합니다.", "After locating Angela, Constantine and Chas head straight for the hospital."),
    (5217, 5260, "crisis", "병원에 도착한 두 사람은, 안젤라를 찾아 안으로 들어갑니다.", "At the hospital, the two men head inside to find Angela."),
    (5320, 5351, "crisis", "", ""),
    (5408, 5470, "crisis", "", ""),
    (5520, 5556, "climax", "", ""),
]


def nearest(value: float, choices: list[float], tolerance: float = 2.0) -> float:
    candidate = min(choices, key=lambda item: abs(item - value))
    return candidate if abs(candidate - value) <= tolerance else value


def protect_dialogue_boundaries(start: float, end: float, cues) -> tuple[float, float]:
    """Never enter or leave while a supplied subtitle cue is still speaking."""
    for cue in cues:
        if cue.start < start < cue.end:
            start = max(0.0, cue.start - 0.12)
        if cue.start < end < cue.end:
            end = cue.end + 0.12
    return start, end


def main() -> None:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    validate_story_map_gate(config, require_render_ready=True, project_root=ROOT)
    cues = parse_srt(SUBTITLE)
    starts = [cue.start for cue in cues]
    ends = [cue.end for cue in cues]
    segments = []
    timeline = 0.0
    for order, (start, end, beat, ko, en) in enumerate(BLOCKS, 1):
        if not ko:
            start = nearest(start, starts)
            end = nearest(end, ends)
        start, end = protect_dialogue_boundaries(start, end, cues)
        duration = end - start
        segments.append({
            "order": order,
            "source_start": round(start, 3),
            "source_end": round(end, 3),
            "kind": "narration" if ko else ("ending" if order == len(BLOCKS) else "movie_dialogue"),
            "story_beat": beat,
            "purpose": ko or "연속된 원대사와 반응으로 사건의 원인과 결과를 보여준다.",
            "narration": ko,
            "narration_tts_en": en,
            "keep_original_audio": not bool(ko),
            "audio_level": 0.18 if ko else 0.96,
            "transition": "cut",
        })
        timeline += duration
    plan = {
        "project_title": "Constantine Story-First Review V3",
        "summary": "엄격한 시간순으로 진행하며 고정 길이 샘플링을 제거하고 화면 행동형 나레이션만 사용한다.",
        "target_duration_sec": round(timeline, 3),
        "style_notes": [
            "no non-chronological cold open",
            "natural scene blocks instead of fixed-duration sampling",
            "narration describes visible action and is clustered at transitions",
            "voice generation remains OFF",
        ],
        "segments": segments,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "edit_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    lengths = [s["source_end"] - s["source_start"] for s in segments]
    gaps = [segments[i + 1]["source_start"] - segments[i]["source_end"] for i in range(len(segments) - 1)]
    boundary_violations = []
    for segment in segments:
        for cue in cues:
            if cue.start < segment["source_start"] < cue.end or cue.start < segment["source_end"] < cue.end:
                boundary_violations.append({"segment": segment["order"], "cue": cue.index})
    milestones = [
        ("숙명의 창 발견", 90, 160),
        ("첫 퇴마와 규칙 이상", 260, 540),
        ("폐암 진단", 780, 900),
        ("이사벨 죽음", 900, 1080),
        ("비먼 조사와 가브리엘의 거절", 1080, 1440),
        ("중립지대와 안젤라의 의뢰", 1800, 2220),
        ("악마의 직접 공격", 2340, 2440),
        ("고양이 의식과 지옥 확인", 2460, 2820),
        ("콘스탄틴의 과거", 2880, 3180),
        ("성경 암호와 마몬", 3240, 3600),
        ("안젤라의 능력 회복", 3600, 4140),
        ("발사자르 심문과 강림 조건", 4140, 4530),
        ("안젤라 납치", 4530, 4680),
        ("미드나잇의 추적 의식", 4680, 5040),
        ("병원 결전과 강림 직전", 5040, 5580),
    ]
    milestone_coverage = {
        label: sum(max(0.0, min(s["source_end"], end) - max(s["source_start"], start)) for s in segments)
        for label, start, end in milestones
    }
    report = {
        "segments": len(segments),
        "narration_blocks": sum(bool(s["narration"]) for s in segments),
        "duration_seconds": round(sum(lengths), 3),
        "clip_min": round(min(lengths), 2),
        "clip_median": round(statistics.median(lengths), 2),
        "clip_max": round(max(lengths), 2),
        "clip_stdev": round(statistics.pstdev(lengths), 2),
        "source_monotonic": all(gap >= 0 for gap in gaps),
        "max_source_end": max(s["source_end"] for s in segments),
        "dialogue_boundary_violations": boundary_violations,
        "milestone_coverage_seconds": {key: round(value, 2) for key, value in milestone_coverage.items()},
    }
    (OUTPUT / "PLAN_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
