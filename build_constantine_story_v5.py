from __future__ import annotations

import json
import statistics
from pathlib import Path

from pipeline import parse_srt


REPO = Path(__file__).resolve().parent
ROOT = REPO / "Constantine" / "story_review_v5"
OUTPUT = ROOT / "output"
SOURCE = REPO / "Constantine" / "Constantine.2005.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mkv"
SUBTITLE = SOURCE.with_suffix(".ko.srt")


# Every interval is chosen for a dramatic function.  They deliberately vary in
# length; this is not fixed-window sampling.  Narration remains text-only.
CLIPS = [
    ("spear_found", 108.000, 138.306, "narration", "멕시코의 폐허에서, 마누엘은 땅속에 묻힌 낡은 창을 발견합니다.", "불길한 원인을 현재 화면의 발견 행동으로만 제시한다."),
    ("first_exorcism", 255.005, 291.000, "narration", "그 시각 로스앤젤레스, 퇴마사 존 콘스탄틴이 한 소녀의 방으로 들어섭니다.", "주인공과 현재 장소를 소개한 뒤 원대사로 넘긴다."),
    ("first_exorcism", 387.639, 402.000, "movie_dialogue", "", "거울을 요구하며 퇴마 방식이 구체화된다."),
    ("first_exorcism", 475.810, 505.298, "movie_dialogue", "", "거울 속 악령과 마지막 대사를 온전히 보여준다."),
    ("angela_confession", 734.000, 773.566, "movie_dialogue", "", "안젤라가 자신의 비정상적으로 정확한 감각을 두려워한다."),
    ("isabel_fall", 800.000, 840.000, "movie_dialogue", "", "이사벨의 망설임과 추락을 설명 없이 체험시킨다."),
    ("constantine_diagnosis", 889.891, 921.339, "movie_dialogue", "", "폐암과 남은 시간이 의사의 대사로 공개된다."),
    ("angela_denial", 991.284, 1024.025, "movie_dialogue", "", "안젤라는 이사벨의 자살을 완강하게 부정한다."),
    ("beeman_rule_break", 1080.000, 1103.354, "narration", "첫 퇴마의 이상을 확인하려, 콘스탄틴은 오랜 동료 비먼을 찾아갑니다.", "완료된 퇴마와 현재 방문의 인과를 연결한다."),
    ("beeman_rule_break", 1167.252, 1190.400, "movie_dialogue", "", "악령이 인간을 통로로 삼은 전례가 없다는 규칙을 보존한다."),
    ("gabriel_refusal", 1357.233, 1404.781, "movie_dialogue", "", "가브리엘은 그의 퇴마가 자기 구원을 위한 거래였다고 지적한다."),
    ("street_attack", 1686.855, 1725.101, "movie_dialogue", "", "거리의 악마가 직접 공격하며 경고가 현실이 된다."),
    ("midnite_warning", 1849.934, 1863.406, "narration", "직접 공격까지 받은 콘스탄틴은, 중립을 지키는 미드나이트에게 경고하러 갑니다.", "완료된 공격과 현재 목적지를 잇는다."),
    ("midnite_warning", 1926.010, 1970.805, "movie_dialogue", "", "악마의 직접 진입과 휴전 규칙이 충돌한다."),
    ("angela_request", 2145.813, 2166.543, "movie_dialogue", "", "안젤라가 동생 사건을 의뢰한다."),
    ("angela_request", 2183.059, 2207.792, "movie_dialogue", "", "이사벨의 악마 환상과 타살 의심이 두 사건을 합친다."),
    ("direct_attack", 2361.821, 2400.485, "movie_dialogue", "", "정전과 날갯소리가 설명보다 먼저 위험을 체감시킨다."),
    ("direct_attack", 2423.007, 2441.442, "movie_dialogue", "", "공격 뒤 남은 유황 냄새가 악마의 직접 개입을 증명한다."),
    ("hell_ritual", 2474.100, 2525.026, "narration", "이사벨의 마지막 행선지를 확인하기 위해, 콘스탄틴은 그녀의 물건과 고양이를 준비합니다.", "이미 제기된 지옥 가능성과 현재 의식 준비를 연결한다."),
    ("isabel_truth", 2745.000, 2786.704, "movie_dialogue", "", "지옥에서 돌아온 뒤 이사벨의 선택이 원대사로 공개된다."),
    ("isabel_truth", 2799.676, 2805.807, "movie_dialogue", "", "현실에 가져온 증거가 체험의 진실성을 확정한다."),
    ("constantine_past", 3075.285, 3126.544, "movie_dialogue", "", "자살 시도와 지옥 체험, 두 세계의 규칙을 고백한다."),
    ("constantine_past", 3151.277, 3182.600, "movie_dialogue", "", "퇴마의 동기가 구원 욕망이었음이 드러난다."),
    ("isabel_clue", 3374.417, 3407.700, "movie_dialogue", "", "경찰이 못 찾는 쌍둥이만의 단서를 요구한다."),
    ("isabel_clue", 3460.378, 3486.654, "movie_dialogue", "", "유리창 메시지에서 지옥 성경의 좌표를 발견한다."),
    ("mammon_prophecy", 3521.606, 3544.796, "movie_dialogue", "", "사탄의 아들 마몬이라는 적이 처음 공개된다."),
    ("mammon_prophecy", 3573.992, 3600.435, "movie_dialogue", "", "강력한 영매와 신의 도움이 강림 조건임을 밝힌다."),
    ("beeman_death", 3611.196, 3634.719, "movie_dialogue", "", "비먼의 마지막 경고가 통화 도중 끊긴다."),
    ("beeman_death", 3634.719, 3650.902, "narration", "통화가 끊기자, 두 사람은 비먼에게 달려갑니다.", "현재 이동만 설명하고 그의 상태는 먼저 말하지 않는다."),
    ("beeman_death", 3650.902, 3663.915, "movie_dialogue", "", "도착한 두 사람이 비먼의 죽음을 직접 확인한다."),
    ("angela_guilt", 3790.667, 3839.090, "movie_dialogue", "", "안젤라는 능력을 숨겨 동생을 혼자 남겼다는 죄책감을 고백한다."),
    ("angela_guilt", 3845.138, 3860.904, "movie_dialogue", "", "진실을 보면 악마도 자신을 본다는 대가를 받아들인다."),
    ("angela_awaken", 3960.086, 4000.710, "movie_dialogue", "", "물 의식의 규칙과 선택을 원대사로 보여준다."),
    ("angela_awaken", 4103.188, 4137.846, "movie_dialogue", "", "돌아온 안젤라가 자신의 감각을 인정한다."),
    ("balthazar_trace", 4148.358, 4193.820, "narration", "각성한 안젤라는, 방 안에 남은 악마의 흔적을 더듬기 시작합니다.", "현재 행동과 방금 획득한 능력만 연결한다."),
    ("balthazar_trace", 4226.644, 4228.897, "movie_dialogue", "", "흔적의 주인이 발사자르임을 직접 확인한다."),
    ("balthazar_interrogation", 4363.865, 4392.936, "movie_dialogue", "", "발사자르와 맞붙어 심문할 기회를 만든다."),
    ("balthazar_interrogation", 4449.367, 4496.664, "movie_dialogue", "", "천국행을 역으로 위협해 악마의 입을 연다."),
    ("balthazar_reveal", 4538.998, 4553.847, "movie_dialogue", "", "예수의 피가 묻은 숙명의 창이 강림 도구임을 밝힌다."),
    ("angela_target", 4569.821, 4583.877, "movie_dialogue", "", "발사자르가 진짜 표적은 안젤라였다고 조롱한다."),
    ("angela_target", 4590.341, 4619.621, "movie_dialogue", "", "창과 영매의 연결이 안젤라에게 수렴한다."),
    ("angela_target", 4641.768, 4671.214, "movie_dialogue", "", "강림 조건이 완성됐음을 깨닫는 순간 안젤라가 위험해진다."),
    ("midnite_tracking", 4712.797, 4722.140, "narration", "안젤라가 사라지자, 콘스탄틴은 다시 미드나이트를 찾아갑니다.", "납치가 드러난 뒤 현재 목적지만 연결한다."),
    ("midnite_tracking", 4755.423, 4793.044, "movie_dialogue", "", "죽어가는 사람들을 외면할 거냐며 중립을 흔든다."),
    ("midnite_tracking", 4960.712, 4974.934, "movie_dialogue", "", "추적 의식 끝에 안젤라의 위치를 찾아낸다."),
    ("hospital_approach", 5015.266, 5040.458, "movie_dialogue", "", "채즈가 지식과 장비로 결전에 합류한다."),
    ("hospital_approach", 5050.051, 5070.000, "narration", "위치를 확인한 콘스탄틴과 채즈는, 안젤라가 붙잡힌 병원으로 향합니다.", "확인된 위치와 현재 이동만 설명한다."),
    ("hospital_approach", 5122.749, 5146.648, "movie_dialogue", "", "책과 현실은 다르다는 경고로 결전의 위험을 세운다."),
    ("hybrid_battle", 5260.845, 5296.548, "movie_dialogue", "", "규칙을 깬 혼혈종들에게 최후통첩하고 성수를 사용한다."),
    ("angela_possession", 5374.209, 5421.297, "movie_dialogue", "", "전투 뒤 안젤라를 찾아 강림을 막기 시작한다."),
    ("angela_possession", 5513.806, 5542.585, "ending", "", "안젤라 안의 존재가 나오려는 위기에서 멈춘다."),
]


EVENTS = [
    ("spear_found", [], True, "마누엘이 땅속에서 숙명의 창을 발견한다.", "폐허 속 남자가 낡은 창을 집어 든다.", "정체를 모르는 물건이 앞으로의 재앙을 연다.", "이 창은 무엇을 불러올까?", None, 108.0, "orient", "opening"),
    ("first_exorcism", [], True, "콘스탄틴이 소녀에게 붙은 악령을 거울에 가둔다.", "거울을 이용한 퇴마가 성공하지만 악령은 이승으로 나오려 한다.", "숙련된 퇴마사조차 규칙의 이상을 감지한다.", "왜 악령이 규칙을 깨고 나오려 했을까?", None, 255.005, "orient", "parallel_thread"),
    ("angela_confession", [], True, "형사 안젤라는 남들이 못 보는 것을 감지하는 자신을 두려워한다.", "고해소에서 지나치게 정확한 감각을 고백한다.", "이사벨을 외면한 과거와 연결될 내적 상처가 드러난다.", "안젤라는 무엇을 외면하고 있나?", None, 734.0, "none", "parallel_thread"),
    ("isabel_fall", ["angela_confession"], False, "이사벨이 병원 옥상에서 망설이다 추락한다.", "이사벨이 옥상 끝에 서서 망설인 뒤 떨어진다.", "안젤라가 진실을 추적할 감정적 원인이 생긴다.", "이사벨은 왜 죽음을 택했나?", "안젤라의 불안이 현실의 상실로 이어진다.", 840.0, "none", "continuous"),
    ("constantine_diagnosis", ["first_exorcism"], False, "콘스탄틴은 폐암과 짧은 시한을 통보받는다.", "의사가 검사 결과와 남은 시간을 설명한다.", "세상을 구하는 남자에게 자기 시간을 구할 길은 없다.", "그는 죽기 전에 무엇을 바꿀 수 있을까?", "콘스탄틴에게 시간이 거의 남지 않았다.", 903.238, "none", "parallel_thread"),
    ("angela_denial", ["isabel_fall"], False, "안젤라는 이사벨이 자살했다는 결론을 거부한다.", "시신 앞에서 자살이 아니라고 반복한다.", "관객이 본 추락과 언니의 확신이 충돌한다.", "자살처럼 보이는 죽음 뒤에 무엇이 있나?", None, 1009.761, "none", "parallel_thread"),
    ("beeman_rule_break", ["first_exorcism"], False, "비먼이 악령의 직접 진입은 전례가 없다고 확인한다.", "콘스탄틴이 퇴마의 이상을 설명하고 비먼이 규칙을 말한다.", "한 번의 퇴마가 세계 질서의 균열로 커진다.", "누가 균형의 규칙을 깨고 있나?", "악령은 원래 인간을 통로로 이승에 오지 못한다.", 1181.432, "causal_bridge", "bridge"),
    ("gabriel_refusal", ["constantine_diagnosis", "beeman_rule_break"], False, "가브리엘은 콘스탄틴의 구원 거래를 거절한다.", "가브리엘이 그의 이기적 동기를 지적한다.", "외적 사건과 별개로 주인공의 결핍이 선명해진다.", "구원은 거래로 얻을 수 있는가?", "콘스탄틴의 퇴마는 자신을 위한 일이었다.", 1391.559, "none", "bridge"),
    ("street_attack", ["beeman_rule_break"], False, "거리의 악마가 콘스탄틴을 직접 공격한다.", "낯선 남자의 몸이 벌레 무리로 무너지며 덮친다.", "규칙 위반은 조사 대상이 아니라 즉각적인 위협이 된다.", "경고를 믿어줄 세력은 누구인가?", "악마의 직접 개입이 현실에서 확인된다.", 1725.101, "none", "bridge"),
    ("midnite_warning", ["street_attack"], False, "콘스탄틴이 미드나이트에게 규칙 붕괴를 경고한다.", "중립지대에서 악마의 직접 진입을 주장한다.", "도움을 줄 수 있는 인물은 중립을 이유로 움직이지 않는다.", "미드나이트의 중립은 언제 깨질까?", "천국과 지옥은 휴전 중이며 그는 중립을 지킨다.", 1970.805, "causal_bridge", "bridge"),
    ("angela_request", ["angela_denial", "midnite_warning"], False, "안젤라가 콘스탄틴에게 이사벨 사건을 의뢰한다.", "동생의 환상과 타살 의심을 설명한다.", "두 주인공의 상처와 외부 사건이 하나로 합쳐진다.", "이사벨이 보던 존재는 실제였나?", "안젤라는 초자연적 원인을 의심해 콘스탄틴을 찾았다.", 2207.792, "none", "bridge"),
    ("direct_attack", ["angela_request", "street_attack"], False, "보이지 않는 존재가 두 사람을 직접 공격한다.", "정전, 날갯소리, 충격 뒤 유황 냄새가 남는다.", "안젤라는 부정하던 세계를 몸으로 경험한다.", "이사벨은 죽기 전에 무엇을 보았나?", "공격자는 지옥의 존재와 연결돼 있다.", 2436.813, "none", "continuous"),
    ("hell_ritual", ["angela_request", "direct_attack"], False, "콘스탄틴이 이사벨의 행선지를 확인할 의식을 준비한다.", "이사벨의 물건과 고양이, 물을 이용해 경계를 연다.", "수사는 증거 수집에서 지옥을 직접 확인하는 단계로 넘어간다.", "이사벨은 정말 지옥에 있는가?", None, 2525.026, "causal_bridge", "bridge"),
    ("isabel_truth", ["hell_ritual"], False, "콘스탄틴이 이사벨의 자살과 지옥행을 확인한다.", "지옥에서 이사벨을 보고 현실에 증거를 가져온다.", "죽음의 방식보다 그 선택의 이유가 새 미스터리가 된다.", "그녀는 무엇을 알리기 위해 목숨을 버렸나?", "이사벨은 스스로 뛰어내렸고 지옥에 있다.", 2780.281, "none", "continuous"),
    ("constantine_past", ["isabel_truth", "gabriel_refusal"], False, "콘스탄틴이 자신의 자살과 지옥 경험을 고백한다.", "죽음의 경계와 균형의 규칙을 안젤라에게 설명한다.", "그의 냉소가 지옥의 공포와 구원 욕망에서 비롯됐음이 보인다.", "두 사람은 이사벨의 경고를 찾을 수 있을까?", "콘스탄틴은 자기 구원을 위해 규칙 위반자를 사냥해 왔다.", 3171.756, "none", "continuous"),
    ("isabel_clue", ["isabel_truth", "constantine_past"], False, "안젤라가 쌍둥이만 아는 유리창 메시지를 찾아낸다.", "기억을 따라 입김으로 숨은 성경 좌표를 드러낸다.", "안젤라가 외면했던 자매의 연결이 수사의 열쇠가 된다.", "지옥 성경의 구절은 무엇을 예고하나?", "이사벨은 고린도전서 17장 1절을 남겼다.", 3483.735, "none", "continuous"),
    ("mammon_prophecy", ["isabel_clue", "beeman_rule_break"], False, "비먼이 마몬 강림의 조건을 해독한다.", "지옥 성경에서 마몬, 영매, 신의 도움을 읽는다.", "개별 악마 사건이 인간 세계 전체의 위기로 확대된다.", "마몬은 누구의 몸과 어떤 신의 도움을 노리나?", "마몬은 강력한 영매와 신의 도움을 필요로 한다.", 3600.435, "none", "continuous"),
    ("beeman_death", ["mammon_prophecy"], False, "비먼의 경고가 끊기고 두 사람이 그의 죽음을 확인한다.", "통화가 끊긴 뒤 은신처로 달려가 시신을 발견한다.", "정보를 얻을수록 콘스탄틴의 동료가 사라진다.", "안젤라는 더 깊이 들어갈 각오가 되었나?", "마몬의 편은 단서를 없애며 추적자를 살해한다.", 3663.915, "causal_bridge", "bridge"),
    ("angela_guilt", ["beeman_death", "constantine_past"], False, "안젤라는 능력을 숨겨 이사벨을 혼자 남겼다고 고백한다.", "어린 시절의 거짓말과 죄책감을 털어놓고 의식을 청한다.", "진실 추적은 동생을 버렸다는 죄책감에 대한 속죄가 된다.", "그녀가 능력을 되찾으면 무엇을 보게 될까?", "안젤라는 위험을 알면서도 진실을 보기로 선택한다.", 3860.904, "none", "continuous"),
    ("angela_awaken", ["angela_guilt"], False, "물 의식으로 안젤라의 영적 감각이 깨어난다.", "물속에서 경계를 보고 돌아와 자신의 능력을 인정한다.", "억눌렀던 감각은 단서이자 적에게 보이는 표식이 된다.", "새 감각은 살인자의 흔적을 찾을 수 있을까?", "안젤라는 이사벨과 같은 존재들을 볼 수 있다.", 4129.171, "none", "continuous"),
    ("balthazar_trace", ["angela_awaken", "beeman_death"], False, "안젤라가 남은 감각으로 발사자르의 흔적을 찾는다.", "방 안의 잔상을 더듬어 빛나는 흔적과 이름을 말한다.", "수동적인 목격자였던 안젤라가 추적의 주체가 된다.", "발사자르는 강림에 무엇을 제공했나?", "살인자의 흔적은 발사자르에게 이어진다.", 4228.897, "character_subtext", "continuous"),
    ("balthazar_interrogation", ["balthazar_trace"], False, "콘스탄틴이 발사자르를 붙잡아 천국행으로 위협한다.", "격투 뒤 축복을 준비하며 강림 방법을 묻는다.", "자신이 갈 수 없는 천국을 악마에게 가장 무서운 형벌로 사용한다.", "발사자르가 숨긴 마지막 조건은 무엇인가?", "발사자르는 죽음보다 천국행을 두려워한다.", 4496.664, "none", "bridge"),
    ("balthazar_reveal", ["balthazar_interrogation", "mammon_prophecy"], False, "발사자르가 숙명의 창과 예수의 피를 폭로한다.", "창이 마몬 탄생의 도구라고 말한다.", "도입의 창이 마침내 현재의 음모와 연결된다.", "강력한 영매는 누구인가?", "신의 도움은 숙명의 창에 묻은 예수의 피였다.", 4553.847, "none", "continuous"),
    ("angela_target", ["balthazar_reveal", "angela_awaken"], False, "진짜 표적이 안젤라였음이 드러나고 그녀가 납치된다.", "발사자르의 조롱과 강림 조건이 안젤라에게 수렴한다.", "콘스탄틴의 도움으로 얻은 각성이 적의 마지막 조건을 완성했다.", "안젤라가 숙주가 되기 전에 찾을 수 있을까?", "안젤라는 마몬에게 필요한 강력한 영매다.", 4671.214, "none", "continuous"),
    ("midnite_tracking", ["angela_target", "midnite_warning"], False, "콘스탄틴이 미드나이트의 중립을 깨고 위치를 찾아낸다.", "친구들의 죽음을 들이밀고 추적 의식의 도움을 얻는다.", "중립은 균형을 지키는 원칙에서 방관의 핑계로 바뀌었다.", "병원에 도착하기 전에 강림을 막을 수 있을까?", "미드나이트가 움직여 안젤라의 위치를 찾는다.", 4974.934, "causal_bridge", "bridge"),
    ("hospital_approach", ["midnite_tracking"], False, "콘스탄틴과 채즈가 병원 결전에 들어간다.", "채즈가 장비를 챙기고 두 사람이 병원으로 향한다.", "견습생이 관찰자에서 동료로 나선다.", "두 사람은 혼혈종의 방어선을 뚫을 수 있을까?", "안젤라는 병원에 붙잡혀 있다.", 5146.648, "causal_bridge", "bridge"),
    ("hybrid_battle", ["hospital_approach", "beeman_rule_break"], False, "콘스탄틴이 규칙을 깬 혼혈종들을 성수로 몰아낸다.", "최후통첩 뒤 성수 장치를 작동시킨다.", "초반부터 흔들리던 균형의 규칙이 공개적인 전쟁으로 무너진다.", "방어선 너머의 안젤라는 어떤 상태인가?", "혼혈종들은 이미 휴전의 균형을 깼다.", 5296.548, "none", "continuous"),
    ("angela_possession", ["hybrid_battle", "angela_target"], False, "안젤라의 몸에서 마몬이 나오려 한다.", "콘스탄틴이 안젤라를 붙잡고 몸속 존재를 막으려 한다.", "모든 단서가 한 사람의 몸과 한 번의 선택으로 좁혀진다.", "빛을 부르면 모습을 드러낼 진짜 배후는 누구인가?", "안젤라가 마몬의 강림 통로가 되고 있다.", 5542.585, "none", "continuous"),
]


SECTION_DEFS = [
    ("opening_wounds", "두 주인공과 이사벨의 상처는 어떻게 시작되는가?", "창, 규칙 위반, 이사벨의 죽음, 콘스탄틴의 시한이 각각 제시된다.", "서로 떨어진 사건들은 어떻게 하나가 되는가?", ["spear_found", "first_exorcism", "angela_confession", "isabel_fall", "constantine_diagnosis", "angela_denial", "beeman_rule_break"]),
    ("paths_converge", "서로 떨어진 사건들은 어떻게 하나가 되는가?", "안젤라의 의뢰와 직접 공격이 이사벨의 죽음을 규칙 붕괴와 연결한다.", "이사벨은 무엇을 알았기에 죽음을 택했는가?", ["gabriel_refusal", "street_attack", "midnite_warning", "angela_request", "direct_attack"]),
    ("hell_verification", "이사벨은 무엇을 알았기에 죽음을 택했는가?", "지옥에서 자살을 확인하고 그녀가 남긴 경고를 찾아야 함을 안다.", "콘스탄틴과 안젤라는 그 경고를 읽을 수 있는가?", ["hell_ritual", "isabel_truth", "constantine_past"]),
    ("mammon_message", "콘스탄틴과 안젤라는 그 경고를 읽을 수 있는가?", "쌍둥이의 메시지가 마몬 강림 예언을 가리킨다.", "안젤라는 외면한 능력을 받아들일 수 있는가?", ["isabel_clue", "mammon_prophecy", "beeman_death"]),
    ("angela_choice", "안젤라는 외면한 능력을 받아들일 수 있는가?", "죄책감을 고백한 안젤라가 위험을 감수하고 능력을 되찾는다.", "각성한 감각은 적의 계획을 어디로 이끄는가?", ["angela_guilt", "angela_awaken", "balthazar_trace"]),
    ("trap_revealed", "각성한 감각은 적의 계획을 어디로 이끄는가?", "숙명의 창과 영매라는 조건이 안젤라를 표적으로 가리킨다.", "납치된 안젤라를 어디서 찾을 수 있는가?", ["balthazar_interrogation", "balthazar_reveal", "angela_target"]),
    ("neutrality_breaks", "납치된 안젤라를 어디서 찾을 수 있는가?", "미드나이트가 중립을 깨고 병원의 위치를 찾아준다.", "병원의 방어선을 뚫고 강림을 막을 수 있는가?", ["midnite_tracking", "hospital_approach"]),
    ("pre_resolution_crisis", "병원의 방어선을 뚫고 강림을 막을 수 있는가?", "혼혈종을 밀어내지만 마몬은 이미 안젤라 안에서 나오려 한다.", "빛을 부르면 나타날 진짜 배후는 누구인가?", ["hybrid_battle", "angela_possession"]),
]


def protect_dialogue_boundaries(start: float, end: float, cues) -> tuple[float, float]:
    for cue in cues:
        if cue.start < start < cue.end:
            start = max(0.0, cue.start - 0.12)
        if cue.start < end < cue.end:
            end = cue.end + 0.12
    return round(start, 3), round(end, 3)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cues = parse_srt(SUBTITLE)
    adjusted = []
    previous_end = -1.0
    for event_id, start, end, kind, narration, purpose in CLIPS:
        start, end = protect_dialogue_boundaries(start, end, cues)
        if start < previous_end - 0.001:
            raise ValueError(f"TIME_REVERSAL: {event_id} {start} < {previous_end}")
        previous_end = end
        adjusted.append((event_id, start, end, kind, narration, purpose))

    by_event: dict[str, list[tuple[float, float]]] = {}
    for event_id, start, end, *_ in adjusted:
        by_event.setdefault(event_id, []).append((start, end))

    event_records = {}
    for (event_id, causes, entry, summary, visible, stake, opened, answered, reveal, role, transition) in EVENTS:
        intervals = by_event[event_id]
        record = {
            "id": event_id,
            "source_start": min(a for a, _ in intervals),
            "source_end": max(b for _, b in intervals),
            "summary": summary,
            "cause_ids": causes,
            "entry_point": entry,
            "characters": [],
            "visible_action": visible,
            "emotional_stake": stake,
            "question_opened": opened,
            "question_answered": answered,
            "reveal_time": max(min(float(reveal), max(b for _, b in intervals)), min(a for a, _ in intervals)),
            "must_show": True,
            "selected_intervals": [[a, b] for a, b in intervals],
            "narration_role": role,
            "transition_in": transition,
            "needs_visual_review": False,
        }
        narration_clips = [item for item in adjusted if item[0] == event_id and item[4]]
        if role != "none":
            record["narration_start_time"] = narration_clips[0][1]
            record["narration_evidence_time"] = min(narration_clips[0][1], float(reveal))
        event_records[event_id] = record

    story_map = {
        "schema_version": 1,
        "project_title": "Constantine Story-First Review V5",
        "timeline_mode": "chronological",
        "spoiler_cutoff_source_sec": 5580,
        "sections": [
            {
                "id": sid,
                "status": "approved",
                "audience_question": question,
                "exit_answer": answer,
                "next_question": next_question,
                "events": [event_records[event_id] for event_id in event_ids],
            }
            for sid, question, answer, next_question, event_ids in SECTION_DEFS
        ],
    }
    (ROOT / "story_map.v1.json").write_text(json.dumps(story_map, ensure_ascii=False, indent=2), encoding="utf-8")

    segments = []
    for order, (event_id, start, end, kind, narration, purpose) in enumerate(adjusted, 1):
        segments.append({
            "order": order,
            "source_start": start,
            "source_end": end,
            "kind": kind,
            "story_beat": next(sid for sid, *_, ids in SECTION_DEFS if event_id in ids),
            "story_event_id": event_id,
            "purpose": purpose,
            "narration": narration,
            "narration_tts_en": "",
            "keep_original_audio": True,
            "audio_level": 0.18 if narration else 0.96,
            "transition": "fade" if event_records[event_id]["transition_in"] in {"bridge", "parallel_thread"} else "cut",
        })
    total = sum(item["source_end"] - item["source_start"] for item in segments)
    plan = {
        "project_title": "Constantine Story-First Review V5",
        "summary": "관객이 사실을 알게 되는 시간순으로 원인·행동·감정·결과를 연결한 음성 OFF 편집본",
        "target_duration_sec": round(total, 3),
        "style_notes": [
            "strict audience-reveal chronology",
            "no fixed-duration sampling",
            "original dialogue carries discoveries and emotion",
            "narration describes current action or established meaning only",
            "voice generation OFF; no preview ducking",
        ],
        "segments": segments,
    }
    (OUTPUT / "edit_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    durations = [item["source_end"] - item["source_start"] for item in segments]
    boundary_violations = []
    for segment in segments:
        for cue in cues:
            if cue.start < segment["source_start"] < cue.end or cue.start < segment["source_end"] < cue.end:
                boundary_violations.append({"segment": segment["order"], "cue": cue.index})
    qa = {
        "segments": len(segments),
        "events": len(EVENTS),
        "sections": len(SECTION_DEFS),
        "narration_blocks": sum(bool(item["narration"]) for item in segments),
        "duration_seconds": round(total, 3),
        "clip_min": round(min(durations), 3),
        "clip_median": round(statistics.median(durations), 3),
        "clip_max": round(max(durations), 3),
        "clip_stdev": round(statistics.pstdev(durations), 3),
        "source_monotonic": all(segments[i]["source_end"] <= segments[i + 1]["source_start"] for i in range(len(segments) - 1)),
        "dialogue_boundary_violations": boundary_violations,
        "future_leak_checks": "validator plus manual line-by-line evidence audit",
        "spoiler_cutoff_source_sec": 5580,
    }
    (OUTPUT / "PLAN_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
