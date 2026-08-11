from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output" / "edit_plan_v3_spoiler_safe.json"
TARGET = ROOT / "output" / "edit_plan.json"


def main() -> None:
    plan = json.loads(SOURCE.read_text(encoding="utf-8"))
    first = plan["segments"][0]
    first["kind"] = "hook_teaser"
    first["narration"] = "모두를 살릴 유일한 남자. 그런데 왜 감염자들은 그를 공격하지 않았을까요?"
    first["keep_original_audio"] = False
    first["audio_level"] = 0.16
    first["purpose"] = "감염자들이 백신을 자처한 남자를 공격하지 않는 이유를 질문해 핵심 미스터리를 연다."
    first["narration_style"] = "curiosity_question"

    last = plan["segments"][-1]
    last["narration"] = "과연 그들이 구해낸 것은, 정말 백신이었을까요?"
    last["purpose"] = "오프닝의 질문을 회수하되 정답은 숨긴 채 영화 시청 욕구를 남긴다."
    last["narration_style"] = "open_loop_callback"

    plan["project_title"] = "COLONY (2026) — 공격받지 않는 백신"
    plan["style_notes"] = [
        "0초에 감염자들이 백신을 공격하지 않는 이유를 질문해 즉시 미스터리를 만든다.",
        "오프닝 질문 뒤 영화의 유일한 백신 원음 대사를 붙여 질문과 장면을 연결한다.",
        "최종 정체와 결말은 공개하지 않고 마지막에 백신이 맞는지 다시 질문한다.",
    ]
    TARGET.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("V4 궁금증 유발 오프닝/엔딩 적용")


if __name__ == "__main__":
    main()
