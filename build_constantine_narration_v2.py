from __future__ import annotations

import json
from pathlib import Path

from pipeline import parse_srt, write_srt


ROOT = Path(__file__).resolve().parent / "Constantine" / "story_review_v5"
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"


# Timeline times in the rendered V5 proxy.  Every cue sits in a verified gap in
# both the movie-dialogue and first-pass narration tracks.
ADDITIONS = [
    (14.800, 20.200, "그 순간부터, 평범했던 인간의 시간이 조용히 뒤틀리기 시작하죠.", "reflection", "창의 영향이 화면에 나타난 뒤 분위기를 확장"),
    (50.600, 56.400, "기도부터 할 거란 예상과 달리, 그는 방에 남은 징후부터 읽어가고,", "character_subtext", "퇴마사의 관찰 방식을 현재 행동으로 해설"),
    (233.000, 238.500, "이사벨은 분명 몸을 던졌지만, 안젤라는 그 선택부터 받아들이지 못하죠.", "character_subtext", "이미 본 추락과 이미 드러난 안젤라의 부정을 연결"),
    (274.100, 278.800, "그가 궁금한 건 악령의 이름보다, 대체 왜 규칙이 깨졌느냐는 것.", "causal_bridge", "첫 퇴마의 이상과 비먼 방문의 목적을 정리"),
    (394.300, 400.300, "이곳은 천국과 지옥이 잠시 싸움을 멈추는, 유일한 중립지대였죠.", "rule_clarify", "미드나이트의 공간과 현재 분위기를 설명"),
    (556.000, 561.800, "이제 수사는 증거를 찾는 단계를 넘어, 죽은 자의 행선지를 향하고,", "stakes", "지옥 확인 의식으로 바뀐 수사의 성격을 정리"),
    (601.000, 606.000, "그렇게 건너간 지옥은, 현실 위에 겹쳐진 폐허에 가까웠죠.", "reflection", "이미 보이는 지옥의 시각적 성격을 해설"),
    (930.300, 936.200, "안젤라가 원한 건 능력이 아니었죠. 늦게라도 동생에게 닿고 싶었던 건데요.", "character_subtext", "죄책감 고백 뒤 선택의 감정적 목적을 해설"),
    (986.000, 991.500, "하지만 진실을 보는 순간, 그 진실도 안젤라를 바라보게 되고,", "stakes", "앞서 설명된 영적 감각의 대가를 환기"),
    (1042.000, 1048.000, "이제 그녀는 보호받는 의뢰인이 아니라, 악마를 찾아내는 눈이 된 거죠.", "character_subtext", "각성 뒤 역할 변화를 현재 추적 행동과 연결"),
    (1196.000, 1202.500, "문제는 되찾은 감각이, 안젤라를 단서이자 표적으로 만들었다는 것.", "stakes", "발사자르가 표적을 밝힌 뒤 의미를 정리"),
    (1257.000, 1262.500, "처음엔 원칙이던 중립도, 이 순간엔 움직이지 않을 변명처럼 들리죠.", "reflection", "미드나이트의 거절과 콘스탄틴의 호소가 드러난 뒤 해석"),
    (1414.000, 1420.000, "적의 숫자는 줄었지만, 강림을 막을 시간도 함께 사라져 가고,", "stakes", "혼혈종 전투 뒤 이미 확립된 시간 압박을 강화"),
    (1470.000, 1476.000, "결국 마몬의 강림은, 예언이 아닌 눈앞의 현실이 돼버렸죠.", "stakes", "안젤라가 꺼내달라고 한 뒤 현재 위기를 정리"),
]


BASE_REWRITES = [
    "멕시코의 폐허를 뒤지던 마누엘은, 땅속에서 낡은 창 하나를 발견하는데…",
    "한편 로스앤젤레스에선, 퇴마사 존 콘스탄틴이 악령에 붙잡힌 소녀를 찾아오고,",
    "첫 퇴마에서 이상을 느낀 콘스탄틴은, 오랜 동료 비먼을 찾아가는데…",
    "얼마 뒤 직접 공격까지 받은 그는, 중립을 지키는 미드나이트에게 향하고,",
    "이사벨의 행선지를 확인하려는 콘스탄틴, 그녀의 물건과 고양이를 준비하는데…",
    "그런데 비먼의 목소리가 끊기자, 두 사람은 곧장 달려가고,",
    "마침내 감각을 되찾은 안젤라는, 방 안에 남은 악마의 흔적을 더듬어 가는데…",
    "안젤라가 사라지자, 콘스탄틴은 다시 미드나이트를 찾아가고,",
    "마침내 위치를 알아낸 콘스탄틴과 채즈는, 안젤라가 붙잡힌 병원으로 향하는데…",
]


def overlap(a: tuple[float, float], b: tuple[float, float], pad: float = 0.0) -> bool:
    return max(a[0] - pad, b[0]) < min(a[1] + pad, b[1])


def main() -> None:
    CAPCUT.mkdir(parents=True, exist_ok=True)
    base = parse_srt(OUTPUT / "narration.srt")
    write_srt([(cue.start, cue.end, cue.text) for cue in base], OUTPUT / "narration_v1.srt")
    write_srt([(cue.start, cue.end, cue.text) for cue in base], CAPCUT / "narration_v1.srt")
    if len(base) != len(BASE_REWRITES):
        raise ValueError(f"BASE_NARRATION_COUNT_CHANGED: {len(base)}")
    for cue, text in zip(base, BASE_REWRITES):
        cue.text = text
    movie = parse_srt(OUTPUT / "movie_captions.srt")
    additions = [(start, end, text) for start, end, text, _, _ in ADDITIONS]

    violations = []
    for index, (start, end, text) in enumerate(additions, 1):
        if not 2.5 <= end - start <= 6.5:
            violations.append(f"duration:{index}")
        if any(overlap((start, end), (cue.start, cue.end), 0.12) for cue in movie):
            violations.append(f"movie_collision:{index}")
        if any(overlap((start, end), (cue.start, cue.end), 0.12) for cue in base):
            violations.append(f"base_narration_collision:{index}")
    if violations:
        raise ValueError("NARRATION_V2_BLOCKED: " + ", ".join(violations))

    merged = [(cue.start, cue.end, cue.text) for cue in base] + additions
    merged.sort(key=lambda item: item[0])
    if any(current[0] < previous[1] for previous, current in zip(merged, merged[1:])):
        raise ValueError("NARRATION_V2_OVERLAP")
    meta_words = ("관객", "시청자", "영화는", "장면은", "연출은")
    meta_hits = [word for _, _, text in merged for word in meta_words if word in text]
    if meta_hits:
        raise ValueError("IMMERSION_BREAKING_META_VIEWPOINT: " + ", ".join(meta_hits))

    combined = [(cue.start, cue.end, cue.text) for cue in movie] + merged
    combined.sort(key=lambda item: (item[0], item[1]))
    if any(current[0] < previous[1] for previous, current in zip(combined, combined[1:])):
        raise ValueError("COMBINED_V2_OVERLAP")

    write_srt(merged, OUTPUT / "narration_v2.srt")
    write_srt(combined, OUTPUT / "captions_combined_v2.srt")
    write_srt(merged, CAPCUT / "narration_v2.srt")
    report = {
        "base_narration_cues": len(base),
        "added_review_cues": len(additions),
        "final_narration_cues": len(merged),
        "movie_dialogue_cues": len(movie),
        "combined_cues": len(combined),
        "movie_collisions": 0,
        "narration_overlaps": 0,
        "voice_generation": "OFF_READY_FOR_TTS",
        "formal_hamnida_count": sum(text.count("습니다") + text.count("입니다") for _, _, text in merged),
        "meta_viewpoint_count": 0,
        "additions": [
            {"start": start, "end": end, "text": text, "role": role, "evidence": evidence}
            for start, end, text, role, evidence in ADDITIONS
        ],
    }
    (OUTPUT / "NARRATION_V2_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
