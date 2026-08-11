from __future__ import annotations

import json
import math
import os
from pathlib import Path

from pipeline import parse_srt

ROOT = Path(r"C:\cineyoutube\Constantine\pro_review")
SUBTITLE = ROOT / ".." / "Constantine.2005.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].ko.srt"
OUTPUT = ROOT / "output"

# Each beat owns a source interval, an exact screen-time budget, and original
# connective copy. The structural cadence comes from the reference metrics;
# no wording is copied from the reference video.
BEATS = [
    ("setup", 0, 180, 50, [
        ("전쟁이 끝난 뒤 사라졌던 숙명의 창이 멕시코에서 모습을 드러냅니다.", "A spear lost after the war suddenly resurfaces in Mexico."),
        ("평범한 청소부가 손에 넣는 순간, 그의 몸은 인간의 한계를 벗어나죠.", "The moment a laborer finds it, his body moves beyond human limits."),
        ("이 물건이 향하는 곳은 천사의 도시라 불리는 로스앤젤레스입니다.", "The weapon is headed for Los Angeles, the so-called City of Angels."),
    ]),
    ("setup", 180, 720, 150, [
        ("한편 퇴마사 존 콘스탄틴은 평소와 다른 빙의 사건을 맡습니다.", "Meanwhile, exorcist John Constantine takes a possession unlike the usual cases."),
        ("소녀 안의 존재는 버티는 게 아니라 밖으로 나오려 하고 있었죠.", "The thing inside the girl is not hiding; it is trying to come out."),
        ("악마는 직접 이승에 들어올 수 없다는 규칙부터 흔들리기 시작합니다.", "The oldest rule is breaking: demons should never enter this world directly."),
        ("콘스탄틴은 악마를 거울에 가두는 위험한 방법을 택합니다.", "Constantine chooses a dangerous method and traps the demon inside a mirror."),
        ("퇴마는 성공하지만, 그가 본 징후는 단순한 빙의가 아니었습니다.", "The exorcism works, but what he witnessed was far more than possession."),
        ("그에게 운전기사 채즈는 제자가 되고 싶지만 아직 차 밖에도 못 나옵니다.", "His driver Chas wants to be a student, but he is still kept outside."),
        ("농담처럼 끝난 현장 뒤로, 더 큰 침입이 이미 시작되고 있었죠.", "Behind the jokes, a much larger invasion has already begun."),
        ("그리고 콘스탄틴에게도 이 사건을 서둘러야 할 개인적인 이유가 생깁니다.", "Constantine also receives a personal reason to solve this crisis quickly."),
        ("악마를 상대해 온 남자를 쓰러뜨린 것은 다름 아닌 폐암이었습니다.", "The man who survived demons is being defeated by lung cancer."),
        ("남은 시간이 짧다는 진단은 그의 모든 선택을 거래로 바꿔 놓습니다.", "A terminal diagnosis turns every choice he makes into a desperate bargain."),
    ]),
    ("inciting_incident", 720, 1080, 90, [
        ("같은 밤, 형사 안젤라는 쌍둥이 동생 이사벨의 죽음을 통보받습니다.", "That same night, detective Angela learns that her twin sister Isabel is dead."),
        ("병원의 결론은 자살이지만 안젤라는 그 말을 조금도 믿지 않죠.", "The hospital calls it suicide, but Angela refuses to believe that conclusion."),
        ("독실한 이사벨이 스스로 지옥을 택할 리 없다는 확신 때문입니다.", "She knows devout Isabel would never willingly condemn herself to hell."),
        ("한 사람은 죽음을 피하려 하고, 다른 한 사람은 죽음의 이유를 쫓습니다.", "One is trying to escape death; the other is chasing the reason behind it."),
        ("아직 만나지 않은 두 사람의 사건은 이미 같은 곳을 향하고 있었죠.", "Before they even meet, both investigations are already heading to the same place."),
        ("이사벨은 마지막 순간, 누군가에게 들려주려는 이름을 남깁니다.", "In her final moment, Isabel leaves behind a name meant for someone to hear."),
    ]),
    ("rising_action", 1080, 1620, 105, [
        ("콘스탄틴은 친구 비먼에게 규칙을 깨려 한 악마의 전례를 조사시킵니다.", "Constantine asks Beeman to investigate a demon that tried to break the rules."),
        ("동시에 가브리엘에게 수명과 천국행을 요구하지만 답은 냉정합니다.", "He also asks Gabriel for more life and a place in heaven, but gets a cold answer."),
        ("그의 퇴마는 희생이 아니라 지옥을 피하려는 계산으로 평가됐기 때문이죠.", "His exorcisms count as calculation, not sacrifice, because he only fears hell."),
        ("바로 그때 안젤라가 동생의 죽음을 조사해 달라며 그를 찾아옵니다.", "At that moment, Angela finds him and asks for help investigating her sister."),
        ("콘스탄틴은 거절하지만 이사벨의 사건에는 익숙한 악취가 배어 있습니다.", "Constantine refuses, yet Isabel's case carries a supernatural scent he recognizes."),
        ("거리에서는 혼혈종이 대놓고 그를 공격하며 경고를 현실로 만듭니다.", "A half-breed attacks him openly, turning his warning into immediate reality."),
        ("결국 그는 중립지대의 주인 파파 미드나잇에게 확인을 받으려 합니다.", "He finally seeks confirmation from Papa Midnite, keeper of neutral ground."),
    ]),
    ("rising_action", 1620, 2160, 95, [
        ("미드나잇의 클럽은 천국과 지옥 양쪽이 싸움을 멈추는 장소입니다.", "Midnite's club is neutral ground where heaven and hell are forbidden to fight."),
        ("하지만 미드나잇은 악마의 직접 침입은 불가능하다며 경고를 무시하죠.", "Midnite dismisses the warning because a direct demonic crossing should be impossible."),
        ("그 틈을 타 혼혈 악마 발사자르는 콘스탄틴의 죽음을 조롱합니다.", "The half-demon Balthazar uses the moment to mock Constantine's approaching death."),
        ("도움을 얻지 못한 콘스탄틴 앞에 안젤라가 다시 나타납니다.", "With no help from Midnite, Constantine finds Angela waiting for him again."),
        ("악마를 믿지 않는 형사와 신을 원망하는 퇴마사는 처음부터 충돌하죠.", "A detective who denies demons clashes with an exorcist who resents God."),
        ("그러나 건물의 불이 꺼지고, 보이지 않던 존재들이 두 사람을 포위합니다.", "Then the lights fail, and unseen creatures surround them both."),
    ]),
    ("rising_action", 2160, 2520, 65, [
        ("콘스탄틴은 안젤라를 노리는 날개 달린 악마들을 단숨에 태워 버립니다.", "Constantine burns away the winged demons hunting Angela."),
        ("눈앞의 증거를 본 안젤라는 이제 동생의 말을 외면할 수 없습니다.", "After seeing the evidence, Angela can no longer dismiss her sister's claims."),
        ("콘스탄틴은 이사벨이 어디로 갔는지 직접 확인하겠다고 제안하죠.", "Constantine offers to discover exactly where Isabel went after death."),
        ("그가 고른 통로는 주문도 문도 아닌, 양쪽을 넘나드는 고양이입니다.", "His doorway is neither a spell nor a gate, but a cat that walks between worlds."),
    ]),
    ("rising_action", 2520, 3240, 150, [
        ("고양이와 물을 매개로 콘스탄틴은 잠시 지옥의 경계로 넘어갑니다.", "Using water and the cat, Constantine briefly crosses into the edge of hell."),
        ("그곳에서 이사벨을 발견하며 자살이라는 사실 자체는 확인됩니다.", "There he finds Isabel and confirms that she truly did take her own life."),
        ("문제는 독실한 그녀가 왜 영원한 고통까지 감수했느냐는 것이죠.", "The real question is why a devout woman accepted eternal suffering."),
        ("콘스탄틴은 자신도 어린 시절 죽었다가 지옥에서 돌아왔다고 고백합니다.", "Constantine admits he also died as a child and returned from hell."),
        ("그가 악마를 보는 능력을 저주라 부르는 이유도 바로 그 경험 때문입니다.", "That experience is why he calls his ability to see demons a curse."),
        ("안젤라는 동생 역시 같은 존재들을 봤지만 혼자 외면했다고 털어놓습니다.", "Angela confesses that Isabel saw the same beings, while she chose to look away."),
        ("두 사람은 이사벨이 죽음으로 쌍둥이 언니에게 메시지를 남겼다고 판단하죠.", "They realize Isabel used her death to leave a message only her twin could find."),
        ("병실의 창문에는 성경에 존재하지 않는 장과 절이 나타납니다.", "A chapter and verse that do not exist in the Bible appear on the hospital window."),
        ("단서는 틀린 것이 아니라, 인간의 성경을 가리킨 것이 아니었습니다.", "The clue is not wrong; it simply does not point to the human Bible."),
        ("비먼은 지옥의 성경을 펼쳐 그 문장이 예고하는 존재를 찾아냅니다.", "Beeman opens the Bible of hell and finds the being foretold by the verse."),
    ]),
    ("reversal", 3240, 3600, 80, [
        ("예언의 주인공은 사탄의 아들 마몬, 아버지의 왕국을 탐내는 존재입니다.", "The prophecy names Mammon, Satan's son, who wants a kingdom of his own."),
        ("그가 이승에 오려면 강력한 영매와 신의 도움이 동시에 필요합니다.", "To enter this world, he needs both a powerful psychic and divine assistance."),
        ("해답을 전하던 비먼은 누군가의 공격을 받고 목숨을 잃습니다.", "Before he can explain everything, Beeman is attacked and killed."),
        ("죽어 가는 친구가 남긴 단서는 사건이 이미 강림 단계에 왔음을 뜻하죠.", "His final clue means the plan has already reached the point of incarnation."),
        ("그리고 안젤라는 자신도 이사벨과 같은 것들을 봤다고 인정합니다.", "Angela finally admits she once saw the same things as Isabel."),
    ]),
    ("rising_action", 3600, 4140, 110, [
        ("안젤라는 동생을 외면한 죄책감 때문에 잃었던 능력을 되찾기로 합니다.", "Driven by guilt, Angela decides to reclaim the gift she once rejected."),
        ("콘스탄틴은 한번 저들을 보면 저들도 그녀를 본다고 분명히 경고하죠.", "Constantine warns that once she sees them, they will also see her."),
        ("그럼에도 안젤라는 물속으로 들어가 지옥의 모습을 정면으로 마주합니다.", "Angela still enters the water and faces hell directly."),
        ("깨어난 감각은 그녀의 뛰어난 사격 실력까지 다른 의미로 바꿉니다.", "Her awakened senses give a darker meaning to her impossible accuracy."),
        ("이제 그녀는 악마의 흔적을 보고 냄새까지 맡을 수 있게 됩니다.", "She can now see demonic traces and even smell their presence."),
        ("그 능력은 숨어 있던 발사자르의 위치를 곧바로 드러내죠.", "That gift immediately exposes Balthazar's hiding place."),
        ("친구들을 잃은 콘스탄틴은 균형보다 복수를 먼저 선택합니다.", "After losing his friends, Constantine chooses revenge over balance."),
    ]),
    ("reversal", 4140, 4680, 115, [
        ("콘스탄틴은 발사자르에게 악마가 가장 두려워하는 천국행을 들이밉니다.", "Constantine threatens Balthazar with the one fate a demon fears: heaven."),
        ("심문 끝에 예수의 피가 묻은 숙명의 창이 강림의 도구임이 밝혀집니다.", "The interrogation reveals the Spear of Destiny as the instrument of incarnation."),
        ("신의 아들을 죽인 피가 이번에는 사탄의 아들을 낳는 열쇠가 된 것이죠.", "Blood that killed God's son will now become the key to birthing Satan's son."),
        ("마지막 조건인 강력한 영매 역시 이미 적들의 눈앞에 있었습니다.", "The final requirement, a powerful psychic, is already within their reach."),
        ("발사자르의 진짜 표적은 처음부터 안젤라였다는 사실이 드러납니다.", "Balthazar reveals that Angela was the true target from the beginning."),
        ("더 끔찍한 건 콘스탄틴의 의식이 그녀의 능력을 완전히 깨웠다는 점입니다.", "Worse, Constantine's ritual fully awakened the very power the enemy needed."),
        ("도움을 주려던 선택이 적의 계획을 완성한 셈이 되어 버렸죠.", "His attempt to help has effectively completed the enemy's plan."),
        ("그 사실을 깨닫는 순간 안젤라는 보이지 않는 힘에 납치됩니다.", "The moment they understand the trap, an unseen force abducts Angela."),
    ]),
    ("crisis", 4680, 5040, 65, [
        ("콘스탄틴은 중립을 고집하던 미드나잇에게 마지막 도움을 요구합니다.", "Constantine demands one final favor from Midnite, who still clings to neutrality."),
        ("친구들의 죽음과 임박한 강림 앞에서 중립이라는 명분도 무너지기 시작하죠.", "With friends dead and incarnation near, the excuse of neutrality begins to collapse."),
        ("사형수의 의자를 이용한 추적 끝에 안젤라의 위치가 드러납니다.", "A psychic search through an execution chair finally reveals Angela's location."),
        ("이제 남은 시간은 마몬이 그녀의 몸을 열기 전까지뿐입니다.", "They now have only until Mammon opens a path through her body."),
    ]),
    ("crisis", 5040, 5500, 111, [
        ("혼자 가려던 콘스탄틴을 채즈가 막아서며 처음으로 전투에 합류합니다.", "Chas stops Constantine from going alone and finally joins the fight."),
        ("두 사람의 무기는 총보다 평범한 스프링클러와 십자가에 가깝습니다.", "Their real weapons are not guns, but sprinklers and a blessed cross."),
        ("건물 전체의 물을 성수로 바꾸는 순간 혼혈종들의 우위가 뒤집힙니다.", "When every drop becomes holy water, the half-breeds lose their advantage."),
        ("콘스탄틴은 균형을 깬 대가를 치르라며 지옥의 군단을 몰아붙입니다.", "Constantine drives back the horde and demands payment for breaking the balance."),
        ("그러나 전투의 목적은 승리가 아니라 안젤라를 제시간에 찾는 것입니다.", "But winning the fight means nothing unless they reach Angela in time."),
        ("마몬은 이미 그녀의 몸 안에서 인간 세상으로 나오고 있었죠.", "Mammon is already pushing through her body into the human world."),
        ("채즈와 콘스탄틴은 배운 모든 퇴마 의식을 한꺼번에 쏟아냅니다.", "Chas and Constantine unleash every exorcism rite they know."),
        ("잠시 안젤라를 되찾은 듯했지만 방 안의 기운은 오히려 더 강해집니다.", "They seem to recover Angela, yet the force inside the room only grows stronger."),
    ]),
]


def choose_clip(cues, slot_start: float, slot_end: float, duration: float, dialogue: bool) -> tuple[float, float]:
    latest = slot_end - duration
    center = (slot_start + slot_end) / 2
    start = slot_start + max(0, slot_end - slot_start - duration) * 0.45
    if dialogue:
        candidates = [c for c in cues if c.start >= slot_start and c.end <= slot_end]
        if candidates:
            cue = min(candidates, key=lambda c: abs((c.start + c.end) / 2 - center))
            start = min(max(slot_start, cue.start - 1.0), latest)
    start = max(slot_start, min(start, latest))
    return round(start, 3), round(start + duration, 3)


def main() -> None:
    cues = parse_srt(SUBTITLE.resolve())
    segments = [{
        "order": 1, "source_start": 5528.0, "source_end": 5542.0, "kind": "hook",
        "story_beat": "cold_open", "purpose": "정체불명의 강대한 존재가 개입하기 직전의 위기로 시작",
        "narration": "죽음을 앞둔 퇴마사는, 세상의 규칙이 깨졌음을 먼저 알아챘다.",
        "narration_tts_en": "A dying exorcist is the first to realize the rules have been broken.",
        "keep_original_audio": False, "audio_level": 0.16, "transition": "cut",
    }]
    order = 2
    for beat_index, (beat, source_start, source_end, budget, narration_lines) in enumerate(BEATS):
        count = max(len(narration_lines) + 1, round(budget / 10))
        raw = [0.78, 1.12, 0.9, 1.25, 0.82, 1.05, 0.96]
        weights = [raw[i % len(raw)] for i in range(count)]
        durations = [budget * w / sum(weights) for w in weights]
        # Make exact total despite rounding.
        durations = [round(d, 3) for d in durations]
        durations[-1] = round(durations[-1] + budget - sum(durations), 3)
        slots = [(source_start + (source_end-source_start)*i/count, source_start + (source_end-source_start)*(i+1)/count) for i in range(count)]
        narr_positions = []
        for j in range(len(narration_lines)):
            narr_positions.append(min(count - 1, math.floor((j + 0.5) * count / len(narration_lines))))
        # Resolve the rare duplicate caused by flooring.
        narr_positions = sorted(set(narr_positions))
        while len(narr_positions) < len(narration_lines):
            narr_positions.append(next(i for i in range(count) if i not in narr_positions))
            narr_positions.sort()
        line_by_pos = {pos: narration_lines[i] for i, pos in enumerate(narr_positions)}
        for pos, ((slot_start, slot_end), duration) in enumerate(zip(slots, durations)):
            use_narration = pos in line_by_pos
            clip_start, clip_end = choose_clip(cues, slot_start, slot_end, duration, not use_narration)
            ko, en = line_by_pos.get(pos, ("", ""))
            segments.append({
                "order": order,
                "source_start": clip_start,
                "source_end": clip_end,
                "kind": "narration" if use_narration else "movie_dialogue",
                "story_beat": beat,
                "purpose": ko or "핵심 대사와 반응으로 직전 설명을 확인",
                "narration": ko,
                "narration_tts_en": en,
                "keep_original_audio": not use_narration,
                "audio_level": 0.18 if use_narration else 0.94,
                "transition": "cut",
            })
            order += 1
    plan = {
        "project_title": "Constantine Professional Review V2",
        "summary": "참고 영상의 구조적 리듬을 반영한 인과 중심 재편집. 최종 배후 공개 직전 종료.",
        "target_duration_sec": 1200,
        "style_notes": [
            "reference speech coverage 59.6%, detected cuts 12.5/minute",
            "narration forms the causal spine; original dialogue supplies punctuation",
            "variable source ranges with no copied reference wording",
        ],
        "segments": segments,
        "narration_version": 2,
        "narration_voice": {"provider": "ElevenLabs", "model": "eleven_v3", "voice_name": "Nayva", "voice_id": "cfc7wVYq4gw4OpcEEAom"},
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "edit_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    timeline = 0.0
    rows = [
        "# Constantine V2 순서·흐름 검토표",
        "",
        "음성 OFF 상태입니다. 나레이션 문장은 화면 흐름을 검토하기 위한 자막 원고입니다.",
        "",
        "| # | 완성본 시간 | 원본 시간 | 유형 | 내용/연결 |",
        "|---:|---:|---:|---|---|",
    ]
    for segment in segments:
        duration = segment["source_end"] - segment["source_start"]
        timeline_end = timeline + duration
        def mmss(value: float) -> str:
            return f"{int(value // 60):02d}:{int(value % 60):02d}"
        detail = segment["narration"] or segment["purpose"]
        rows.append(
            f"| {segment['order']} | {mmss(timeline)}-{mmss(timeline_end)} | "
            f"{mmss(segment['source_start'])}-{mmss(segment['source_end'])} | {segment['kind']} | {detail} |"
        )
        timeline = timeline_end
    (OUTPUT / "FLOW_REVIEW.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps({
        "segments": len(segments),
        "narrated_segments": sum(bool(s["narration"]) for s in segments),
        "duration": round(sum(s["source_end"] - s["source_start"] for s in segments), 3),
        "mean_clip": round(sum(s["source_end"] - s["source_start"] for s in segments) / len(segments), 2),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
