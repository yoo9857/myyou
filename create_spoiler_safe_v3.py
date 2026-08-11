from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output" / "edit_plan_v2.json"
TARGET = ROOT / "output" / "edit_plan.json"


def segment(
    order: int,
    start: float,
    end: float,
    kind: str,
    purpose: str,
    narration: str = "",
    keep_original_audio: bool = True,
    audio_level: float = 0.96,
    transition: str = "cut",
) -> dict:
    return {
        "order": order,
        "source_start": start,
        "source_end": end,
        "kind": kind,
        "story_beat": "cliffhanger",
        "purpose": purpose,
        "narration": narration,
        "keep_original_audio": keep_original_audio,
        "audio_level": audio_level,
        "transition": transition,
        "spoiler_safe": True,
    }


def main() -> None:
    plan = json.loads(SOURCE.read_text(encoding="utf-8"))
    kept = [s for s in plan["segments"] if int(s["order"]) <= 50]
    kept.extend(
        [
            segment(
                51,
                5904.782,
                5933.000,
                "movie_dialogue",
                "서영철의 사상을 보여 주되 감염망의 진짜 중심에 관한 최종 반전은 숨긴다.",
            ),
            segment(
                52,
                5942.820,
                5963.000,
                "movie_dialogue",
                "백신 확보 작전이 성공한 것처럼 보여 주어 이후 결과에 대한 기대를 만든다.",
            ),
            segment(
                53,
                5990.826,
                6015.500,
                "movie_dialogue",
                "백신만 확보한 채 남은 사람들을 버리려는 외부의 판단으로 갈등을 끌어올린다.",
            ),
            segment(
                54,
                6070.156,
                6093.137,
                "movie_dialogue",
                "최초 감염자를 제거하면 끝난다는 가설까지만 공개하고 정답은 보여 주지 않는다.",
                transition="fade",
            ),
            segment(
                55,
                6093.200,
                6099.200,
                "ending_teaser",
                "시청자가 백신의 정체와 마지막 선택을 직접 확인하고 싶게 만드는 스포일러 방지 엔딩.",
                narration="하지만 모두가 백신이라 믿은 남자에게는, 결정적인 비밀이 있었습니다.",
                keep_original_audio=False,
                audio_level=0.16,
                transition="dip_to_black",
            ),
        ]
    )
    plan["segments"] = kept
    duration = sum(float(s["source_end"]) - float(s["source_start"]) for s in kept)
    plan["target_duration_sec"] = round(duration, 3)
    plan["project_title"] = "COLONY (2026) — 백신의 비밀"
    plan["summary"] = (
        "감염 사태의 규칙과 생존자들의 백신 확보 작전까지 따라가되, "
        "서영철의 최종 정체와 제거 결과는 공개하지 않는 19분대 스포일러 세이프 리뷰 편집표."
    )
    plan["style_notes"] = [
        "핵심 설정과 인물의 선택은 이해되게 보여 주되 최종 정답과 생존 결과는 숨긴다.",
        "나레이션은 3~6초의 짧은 브리지로만 사용하고 곧바로 영화 원음에 넘긴다.",
        "마지막은 최초 감염자 가설과 백신의 비밀을 연결한 뒤 반전 공개 직전에 끊는다.",
    ]
    TARGET.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"V3 스포일러 세이프 편집표: {len(kept)}개 구간, {duration:.3f}초")


if __name__ == "__main__":
    main()
