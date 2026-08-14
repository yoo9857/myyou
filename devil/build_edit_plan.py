"""Turn the approved story map into an edit plan at the approved runtime and rhythm.

The story map says which beats matter and where they are; it selects 40 minutes of film.
This narrows that to 18 and imposes the rhythm the approved rules ask for:

  reviewer_share_floor               narration ~40 percent of runtime, kept dialogue ~14
  narration_cycle_not_block_length   a ~7 s block roughly every 18 s
  save_dialogue_for_confrontations   the film's own dialogue in long blocks, at the clashes
  shorter_total_runtime              17-19 minutes
  phase_density_curve_confirmed      dense open, thinner middle, dense close

Narration and film time are budgeted separately and then tiled alternately inside each
beat. Budgeting one block per beat was the first attempt and it produced 26 blocks on a
33-second cycle — a fifth of the runtime narrated, which is the fault the reference exposed
in the previous project. The tiling is what makes the density reachable.

Each narration slot carries the beat's intent as placeholder text. narration_pass.py writes
the actual lines; this file only decides where a line belongs and how long it may run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORY_MAP = ROOT / "story_map.v1.json"
OUT = ROOT / "output" / "edit_plan.json"
CONFIG = ROOT / "config.json"

sys.path.insert(0, str(ROOT.parent))
import pipeline  # noqa: E402  - for the subtitle parser only

# Where the film speaks. A narration block placed without consulting this lands the narrator
# on top of the characters: 33 of 49 lines overlapped the film's dialogue, most of them by
# 84 to 98 percent of the spoken line. The block slides forward into the nearest quiet pocket
# instead, which the film provides readily - events run 40 to 160 seconds and a block is 7.
_config = json.loads(CONFIG.read_text(encoding="utf-8"))
_subtitle = ROOT / str(_config.get("subtitle", ""))
DIALOGUE = pipeline.parse_srt(_subtitle) if _subtitle.exists() else []
SLIDE_STEP = 0.25
# Only the first few seconds of a block carry the voice, so that is what has to stay clear.
# Measured on the finished lines: 2.7 to 5.2 seconds, so 5 covers all of them.
SPOKEN_SECONDS = 5.0
# How far a block may slide. Every second skipped becomes film footage, so a long
# reach buys quiet at the cost of runtime and narration share: 45 s produced 21.1
# minutes at 29 percent narrated, both outside the approved range.
MAX_SLIDE = 10.0


def dialogue_overlap(start: float, end: float) -> float:
    return sum(max(0.0, min(cue.end, end) - max(cue.start, start))
               for cue in DIALOGUE if cue.start < end and cue.end > start)


# A beat's window is an authored approximation; the spoiler cut is not. So a line is allowed
# to finish just past the window rather than be chopped - two were, one of them losing 1.34
# seconds of "give you a proper burial" - but never past the cut.
WINDOW_GRACE = 1.6


def snap_to_speech(start: float, end: float, hard_limit: float) -> float:
    """Move a cut off the middle of a spoken line.

    A boundary placed by budget alone lands wherever the arithmetic put it, and several
    landed inside a line - the scene changed with a character halfway through a word. Where
    the line can be allowed to finish inside the beat's own window it is; where it cannot,
    the cut retreats to just before the line starts so it is never heard beginning.
    """
    for cue in DIALOGUE:
        if cue.start + 0.05 < end < cue.end - 0.05:
            finish = cue.end + 0.12
            if finish <= hard_limit and finish - start <= MAX_CLIP:
                return finish
            retreat = cue.start - 0.05
            return retreat if retreat - start >= 2.0 else end
        if cue.start > end:
            break
    return end


def snap_off_speech(start: float, hard_limit: float) -> float:
    """Move a cut off the middle of a line it would otherwise open on.

    Entering a scene with a character already mid-word reads as a mistake the same way
    leaving one does. The clip starts after the line finishes instead; it cannot start
    earlier, because the previous block may already own that footage and a plan may not use
    the same source twice.
    """
    for cue in DIALOGUE:
        if cue.start + 0.05 < start < cue.end - 0.05:
            resume = cue.end + 0.08
            return resume if resume < hard_limit - 2.0 else start
        if cue.start > start:
            break
    return start


def quietest_start(earliest: float, latest: float, block: float) -> float:
    """Slide a block between two bounds and return the start with least dialogue over the voice."""
    if latest <= earliest:
        return earliest
    best, best_overlap = earliest, None
    offset = earliest
    while offset <= latest + 1e-9:
        overlap = dialogue_overlap(offset, offset + min(SPOKEN_SECONDS, block))
        if best_overlap is None or overlap < best_overlap - 1e-9:
            best, best_overlap = offset, overlap
            if overlap <= 0.0:
                break
        offset += SLIDE_STEP
    return best

# Budgeted 6 percent over the 18:00 the reference runs, because tiling always lands under
# budget: a group stops emitting when the event window runs out or when the last narration
# block leaves no room for a film run after it. Aiming at 18:00 exactly produced 17:00.
TARGET = 1145.0             # budgets for 19:05, lands near 18:00
NARRATION_SHARE = 0.40      # approved
KEPT_DIALOGUE_SHARE = 0.14  # the beats where the film speaks for itself
NARRATION_BLOCK = 7.0       # approved: blocks near 6 s, 7 keeps the count under the cap
# A sentence of 9 to 14 words runs about 3 to 4 seconds through the approved voice, so
# anything shorter than this cannot hold one and is dropped rather than truncated.
MIN_NARRATION_BLOCK = 5.0
MIN_FILM_RUN = 5.0          # never cut back to narration faster than this
MAX_CLIP = 26.0            # under the validator's 30 s ceiling
DIALOGUE_BLOCK_MIN = 13.0   # long enough to cover a 10 s must-show promise after the
# start has been pushed off a spoken line; at 9 the two setup dialogue beats covered 80.

GROUPS = {
    "setup": (0.289, ["cold_open_prayer_log", "willard_war_and_charlotte", "arvin_boyhood"]),
    "roy_helen": (0.108, ["roy_and_helen_parallel", "roy_ends"]),
    "arvin_lenora": (0.179, ["arvin_and_lenora_grow", "preacher_arrives",
                             "predators_established", "lenora_breaks"]),
    "confrontation": (0.338, ["arvin_acts", "roads_converge", "cornered"]),
    "closing": (0.085, ["closing_wrap"]),
}

# save_dialogue_for_confrontations asks for the film's own dialogue in about ten ten-second
# blocks, concentrated where characters face each other. Splitting the kept budget by each
# group's runtime share instead gave setup 46 seconds against the confrontation's 54 - all
# but even, which is the opposite of concentrated. These weights put most of it at the
# clashes and leave the setup beats a single block each.
KEPT_WEIGHTS = {
    "setup": 0.12,
    "roy_helen": 0.10,
    "arvin_lenora": 0.14,
    "confrontation": 0.60,
    "closing": 0.04,
}

story = json.loads(STORY_MAP.read_text(encoding="utf-8"))
sections = {s["id"]: s for s in story["sections"]}
cutoff = float(story["spoiler_cutoff_source_sec"])


def weight(event: dict) -> float:
    if event["narration_role"] in ("rule_clarify", "orient"):
        return 1.0     # connective: one short block and move on
    return 1.5


segments: list[dict] = []
order = 0
report = []

for group, (share, section_ids) in GROUPS.items():
    events = [(sid, e) for sid in section_ids for e in sections[sid]["events"]]
    kept = [(sid, e) for sid, e in events if e["narration_role"] == "none"]
    narrated = [(sid, e) for sid, e in events if e["narration_role"] != "none"]

    group_budget = TARGET * share
    kept_budget = TARGET * KEPT_DIALOGUE_SHARE * KEPT_WEIGHTS[group]
    kept_budget = min(kept_budget, group_budget * 0.5) if kept else 0.0
    narration_budget = (group_budget - kept_budget) * (
        NARRATION_SHARE / (1.0 - KEPT_DIALOGUE_SHARE))
    film_budget = group_budget - kept_budget - narration_budget

    total_w = sum(weight(e) for _, e in narrated) or 1.0
    spent = 0.0

    def emit(kind: str, start: float, end: float, sid: str, event: dict, text: str = "") -> float:
        global order
        hard_limit = min(cutoff, float(event["source_end"]))
        # Snapping the start forward keeps the block's requested length rather than eating
        # into it, and is skipped when there is no room left for the whole block. Shortening
        # instead cost a block outright: the Luger handover sits in a stretch of almost
        # continuous speech, its start kept being pushed, and the beat vanished from the
        # review along with the line already recorded for it.
        requested = max(0.0, min(end, hard_limit) - start)
        shifted = snap_off_speech(start, hard_limit)
        if shifted > start and shifted + requested <= hard_limit:
            start, end = shifted, shifted + requested
        grace_limit = min(hard_limit + WINDOW_GRACE, cutoff)
        end = snap_to_speech(start, min(max(end, start), hard_limit), grace_limit)
        end = min(end, grace_limit)
        # A narration block is a place for one spoken sentence. Clamping it to whatever is
        # left of the event window produced a 2.72-second block, and the voice line written
        # for it came back 2.815 seconds and failed the length gate. Below the floor the
        # block is not shortened, it is not emitted, and the film simply runs on.
        floor = MIN_NARRATION_BLOCK if kind == "narration" else 2.0
        if end - start < floor:
            return 0.0
        order += 1
        segments.append({
            "order": order,
            "source_start": round(start, 3),
            "source_end": round(end, 3),
            "kind": kind,
            "story_beat": sid,
            "story_event_id": event["id"],
            "purpose": event["question_opened"],
            "narration": text,
            "keep_original_audio": True,
            "audio_level": 0.32 if kind == "narration" else 0.96,
            "transition": event["transition_in"],
        })
        # Where the block actually ended, so the caller can resume from there. Advancing the
        # cursor by the block's length instead would land inside a block that had been shifted
        # forward, and a plan may not use the same source footage twice.
        emit.last_end = end
        return end - start

    # One pass in the story map's own order. Emitting all the kept beats first and the
    # narrated ones after put every group's dialogue beats at its front: the review opened on
    # a diner and a schoolyard instead of the cold open that is flagged as the entry point,
    # and the standoff - the beat the whole ending is built to stop on - played at 10:38,
    # before the preacher it comes after. The treatment differs per beat; the order does not.
    for sid, event in events:
        if event["narration_role"] == "none":
            allotted = kept_budget / len(kept)
            window_end = min(float(event["source_end"]), cutoff)
            length = max(DIALOGUE_BLOCK_MIN, min(allotted, MAX_CLIP))
            # ending_cut_at_the_draw wants the confrontation played out and the review
            # stopped on the last line before the shooting. A block anchored to the start of
            # the standoff ended at 125:12 and dropped the final plea at 126:04 - a minute of
            # the one beat the ending rests on. A beat that runs up to the cutoff ends there.
            if window_end >= cutoff - 2.0:
                src = max(float(event["source_start"]), window_end - min(allotted, MAX_CLIP))
            else:
                src = float(event["source_start"])
            spent += emit("movie_dialogue", src, src + length, sid, event)
            continue

        w = weight(event) / total_w
        narration_secs = narration_budget * w
        film_secs = film_budget * w
        src = float(event["source_start"])
        limit = min(float(event["source_end"]), cutoff)

        blocks = max(1, round(narration_secs / NARRATION_BLOCK))
        gap = max(MIN_FILM_RUN, min(film_secs / blocks, MAX_CLIP)) if blocks else 0.0
        cursor = src
        for index in range(blocks):
            if cursor >= limit - 2.0:
                break
            text = event["summary"] if index == 0 else event["visible_action"]
            # Slide the block forward into the quietest pocket and let the footage it skipped
            # become the film run before it. Capped at one film run's length the search was
            # too short to escape a dialogue-heavy stretch - 11 lines still sat under the
            # characters at over 60 percent - so it reaches up to 45 seconds, minus whatever
            # the blocks after this one still need. Reserving that space is what keeps the
            # block count fixed, and the count is what lets the recorded voice be reused.
            reserve = (blocks - index - 1) * (NARRATION_BLOCK + MIN_FILM_RUN)
            latest = min(cursor + MAX_SLIDE, limit - NARRATION_BLOCK - reserve)
            speak_at = quietest_start(cursor, latest, NARRATION_BLOCK)
            if speak_at > cursor + MIN_FILM_RUN:
                lead = emit("movie_dialogue", cursor, speak_at, sid, event)
                if lead:
                    cursor = emit.last_end
                    spent += lead
            used = emit("narration", cursor, cursor + NARRATION_BLOCK, sid, event, text)
            if not used:
                break
            cursor = emit.last_end
            spent += used
            if cursor < limit - 2.0 and index < blocks - 1 or (
                    index == blocks - 1 and gap >= MIN_FILM_RUN):
                used = emit("movie_dialogue", cursor, cursor + gap, sid, event)
                if used:
                    cursor = emit.last_end
                    spent += used

    report.append((group, group_budget, spent))

total = sum(s["source_end"] - s["source_start"] for s in segments)
plan = {
    "project_title": story["project_title"],
    "summary": "노컴스티프와 콜크리크, 두 세대에 걸친 신앙과 폭력의 연쇄. "
               "결말 직전 서로 총을 겨눈 대치에서 끝난다.",
    "target_duration_sec": TARGET,
    "style_notes": "승인된 참고 학습 규칙 적용: 해설 블록 7초·주기 18초, 해설 점유율 40%, "
                   "원음은 대결에 길게, 17~19분, 결말은 총성 직전 차단.",
    "spoiler_cutoff_source_sec": cutoff,
    "segments": segments,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

narration = [s for s in segments if s["kind"] == "narration"]
film = [s for s in segments if s["kind"] == "movie_dialogue"]
nsec = sum(s["source_end"] - s["source_start"] for s in narration)
print(f"기록: {OUT.relative_to(ROOT.parent)}")
print(f"  세그먼트 {len(segments)}개, 합계 {total:.0f}초 = {total/60:.1f}분 (목표 {TARGET/60:.0f}분)")
print(f"  해설 {len(narration)}블록 {nsec:.0f}초 ({nsec/total*100:.1f}%, 목표 40%)")
print(f"  해설 주기 {total/len(narration):.1f}초 (목표 18초)")
print(f"  원음 {len(film)}블록 {total-nsec:.0f}초")
run = worst = 0
for s in segments:
    run = run + 1 if s["kind"] == "narration" else 0
    worst = max(worst, run)
print(f"  연속 해설 최대 {worst}개 (3 이상 실패)")
longest = max(s["source_end"] - s["source_start"] for s in segments)
print(f"  최장 클립 {longest:.1f}초 (한계 30초)")
print()
for group, budget, spent in report:
    print(f"  {group:14} 예산 {budget:6.0f}초  실제 {spent:6.0f}초")
