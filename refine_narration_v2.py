from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "output" / "edit_plan.json"

SHORT_NARRATION = {
    2: "이곳에 모인 사람들은 곧 끔찍한 실험에 갇힙니다.",
    3: "그리고 이 기술은 인간까지 하나로 연결할 수 있었죠.",
    5: "평범했던 인연은 곧 살아남아야 할 이유가 됩니다.",
    6: "하지만 테러는 이미 시작된 뒤였습니다.",
    7: "그의 복수는 모두의 개별성을 지우려는 실험이었죠.",
    9: "잠시 뒤, 신인류라는 말이 현실이 됩니다.",
    10: "사람들은 출구가 아닌 감염 구역으로 몰려듭니다.",
    11: "혼자가 되는 순간, 표적이 됩니다.",
    12: "그리고 놈들은 고통도 두려움도 느끼지 않았죠.",
    14: "그때 규성은 학생들을 구할 유인책을 자처합니다.",
    15: "단 한 명만 늦어도 모두가 죽는 작전.",
    16: "결국 규성은 돌아오지 못합니다.",
    17: "설상가상, 정부는 건물 전체를 봉쇄합니다.",
    18: "유일한 희망은 테러범 서영철의 몸속에 있었습니다.",
    21: "세정은 놈들의 집단 지성을 역이용합니다.",
    22: "속임수가 통하는 동안 층을 가로질러야 합니다.",
    23: "마침내 찾은 서영철. 하지만 그는 구조를 원하지 않았죠.",
    24: "이제 그를 옥상까지 직접 데려가야 합니다.",
    25: "그런데 서영철이 도망칩니다.",
    27: "놈들은 이제 인간의 움직임까지 흉내 냅니다.",
    28: "한편 조사팀은 감염망의 중심이 따로 있음을 알아냅니다.",
    29: "CCTV 속 움직임에는 이상한 규칙이 있었습니다.",
    31: "보고 있는 쪽은 오히려 서영철이었습니다.",
    32: "그리고 그는 최초 감염자 강우철에게 향합니다.",
    33: "물린 뒤, 서영철에게 더 이상한 변화가 시작됩니다.",
    34: "순간 흩어진 감염자들이 하나처럼 움직입니다.",
    36: "말하는 순간 계획이 들킵니다. 남은 방법은 문자뿐.",
    38: "현석은 누나와 모두의 생존 사이에서 선택해야 합니다.",
    40: "밖에서는 구조가 아닌 진압을 준비합니다.",
    42: "하지만 그 가설을 시험할 기회는 단 한 번뿐.",
    44: "옥상 구조와 강우철 사살이 동시에 시작됩니다.",
    45: "모두가 이 한 발이면 끝난다고 믿었습니다.",
    47: "하지만 놈들은 멈추지 않았습니다.",
    48: "마침내 세정과 서영철이 마주합니다.",
    49: "그가 원하는 건 복수가 아닌 강제된 하나의 의식.",
    52: "그는 백신이 아니라 감염망의 중심이었습니다.",
    54: "그러나 정부는 결정을 미룹니다.",
    55: "결국 세정은 명령 없이 직접 나섭니다.",
    57: "서영철이 사라지자 놈들의 움직임이 달라집니다.",
}


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    changed = 0
    for segment in plan["segments"]:
        order = int(segment["order"])
        if order in SHORT_NARRATION:
            segment["narration"] = SHORT_NARRATION[order]
            segment["narration_style"] = "short_hype_bridge"
            changed += 1
    missing = sorted(set(SHORT_NARRATION) - {int(x["order"]) for x in plan["segments"]})
    if missing:
        raise RuntimeError(f"편집표에 없는 세그먼트: {missing}")
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"짧은 나레이션 {changed}개 적용")


if __name__ == "__main__":
    main()
