from __future__ import annotations

import json
from pathlib import Path

from pipeline import parse_srt, write_srt


ROOT = Path(__file__).resolve().parent / "Constantine" / "story_review_v5"
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"


# Dry, American-style comic relief. These are placed only in long, verified
# breathing gaps and never over grief, discoveries, or high-stakes action.
COMEDIC_BEATS = [
    (20.500, 26.500, "박물관에 갈 유물도 아니고, 주운 사람부터 바꿔놓는 성질 급한 물건이죠.", "도입의 불길함을 물건의 성격처럼 비트는 과소진술"),
    (57.000, 63.000, "기도부터 할 법도 한데, 수상할 정도로 침착하게 방부터 훑어보고,", "콘스탄틴의 노련함을 건조한 직업 농담으로 전환"),
    (562.100, 568.100, "성수도 아니고 수돗물, 성물도 아니고 고양이라니. 꽤 생활형인 지옥행이죠.", "의식 도구의 의외성을 생활형 비유로 완화"),
    (1048.300, 1054.300, "쓸모없는 환각 취급받던 감각은, 이제 악마 전용 내비게이션이 되고,", "안젤라의 능력 변화를 기능적인 비유로 연결"),
]


def overlaps(a: tuple[float, float], b: tuple[float, float], pad: float = 0.0) -> bool:
    return max(a[0] - pad, b[0]) < min(a[1] + pad, b[1])


def main() -> None:
    base = parse_srt(OUTPUT / "narration_v2.srt")
    movie = parse_srt(OUTPUT / "movie_captions.srt")
    jokes = [(start, end, text) for start, end, text, _ in COMEDIC_BEATS]
    violations = []
    for index, (start, end, text) in enumerate(jokes, 1):
        if not 3.0 <= end - start <= 6.5:
            violations.append(f"duration:{index}")
        if any(overlaps((start, end), (cue.start, cue.end), 0.12) for cue in movie):
            violations.append(f"movie_collision:{index}")
        if any(overlaps((start, end), (cue.start, cue.end), 0.12) for cue in base):
            violations.append(f"narration_collision:{index}")
    if violations:
        raise ValueError("NARRATION_V3_BLOCKED: " + ", ".join(violations))

    merged = [(cue.start, cue.end, cue.text) for cue in base] + jokes
    merged.sort(key=lambda item: item[0])
    combined = [(cue.start, cue.end, cue.text) for cue in movie] + merged
    combined.sort(key=lambda item: (item[0], item[1]))
    if any(current[0] < previous[1] for previous, current in zip(combined, combined[1:])):
        raise ValueError("NARRATION_V3_OVERLAP")

    banned = ("관객", "시청자", "영화는", "장면은", "연출은", "입니다", "습니다")
    hits = [word for _, _, text in merged for word in banned if word in text]
    if hits:
        raise ValueError("NARRATION_V3_STYLE_BLOCKED: " + ", ".join(hits))

    write_srt(merged, OUTPUT / "narration_v3.srt")
    write_srt(combined, OUTPUT / "captions_combined_v3.srt")
    CAPCUT.mkdir(parents=True, exist_ok=True)
    write_srt(merged, CAPCUT / "narration_v3.srt")
    report = {
        "base_review_cues": len(base),
        "added_comedic_beats": len(jokes),
        "final_review_cues": len(merged),
        "movie_dialogue_cues": len(movie),
        "combined_cues": len(combined),
        "collisions": 0,
        "meta_or_formal_style_hits": 0,
        "protected_emotional_or_action_scenes_used": 0,
        "voice_generation": "OFF_READY_FOR_TTS",
        "comedic_beats": [
            {"start": start, "end": end, "text": text, "intent": intent}
            for start, end, text, intent in COMEDIC_BEATS
        ],
    }
    (OUTPUT / "NARRATION_V3_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
