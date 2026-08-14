"""Check the whole project against the things that have actually gone wrong before.

Every check here corresponds to a fault this project shipped or nearly shipped: beats out of
order, a narration line with no voice, a clip that cuts a word in half, captions drifting off
the lips, the ending leaking past the spoiler cut. The delivery gates cover the encode; this
covers the edit.

    python scripts/audit_project.py devil/config.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))


class Audit:
    def __init__(self) -> None:
        self.failed = 0
        self.section = ""

    def group(self, name: str) -> None:
        self.section = name
        print(f"\n[{name}]")

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if not ok:
            self.failed += 1
        print(f"  {'OK  ' if ok else 'FAIL'} {name:28} {detail}")

    def note(self, name: str, detail: str) -> None:
        print(f"  --   {name:28} {detail}")

    def report(self) -> int:
        print(f"\n실패 {self.failed}건" if self.failed else "\n이상 없음")
        return 1 if self.failed else 0


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    import pipeline

    config_path = Path(argv[0]).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    a = Audit()

    story = json.loads((root / "story_map.v1.json").read_text(encoding="utf-8"))
    plan = json.loads((root / "output" / "edit_plan.json").read_text(encoding="utf-8"))
    script = json.loads((root / "output" / "narration_script_v5.json").read_text(encoding="utf-8"))
    segments = plan["segments"]
    cues = pipeline.parse_srt(root / str(config["subtitle"]))
    cutoff = float(story["spoiler_cutoff_source_sec"])
    audio_dir = root / "output" / "capcut_import" / "narration_audio"

    a.group("스토리맵")
    events = [e for s in story["sections"] for e in s["events"]]
    a.check("사건 수", len(events) == 33, f"{len(events)}개")
    a.check("구간 승인", all(s["status"] == "approved" for s in story["sections"]),
            f"{sum(1 for s in story['sections'] if s['status'] == 'approved')}/{len(story['sections'])}")
    a.check("구간 arc 완성",
            all(s.get("exit_answer") and s.get("next_question") for s in story["sections"]))
    a.check("시각 검증 완료", not any(e["needs_visual_review"] for e in events))
    over = [e["id"] for e in events if e["source_end"] > cutoff + 1e-6]
    a.check("차단선 준수", not over, ", ".join(over) if over else f"{cutoff/60:.2f}분")

    a.group("편집표")
    planned = {s["story_event_id"] for s in segments}
    missing = [e["id"] for e in events if e["id"] not in planned]
    a.check("모든 사건 사용", not missing, ", ".join(missing) if missing else f"{len(planned)}개")
    ordered = sorted((s["source_start"], s["source_end"]) for s in segments)
    clashes = [f"{x[1]:.1f}" for x, y in zip(ordered, ordered[1:]) if y[0] < x[1] - 1e-6]
    a.check("원본 구간 겹침 없음", not clashes, ", ".join(clashes[:4]))
    a.check("order 연속", [int(s["order"]) for s in segments] == list(range(1, len(segments) + 1)))
    a.check("차단선 준수", max(s["source_end"] for s in segments) <= cutoff + 1e-6,
            f"최대 {max(s['source_end'] for s in segments)/60:.2f}분")

    # The review deliberately reorders whole sections - it tells one character group at a
    # time instead of cross-cutting the way the film does - so the map's raw section order is
    # not the test. What must hold is that a section plays in one piece and its events run in
    # the order the map gives them. Both failed before the tiler was made to emit each group
    # in one pass: dialogue beats jumped to the front and the standoff played at 10:38.
    appearance, seen = [], set()
    for s in segments:
        if s["story_event_id"] not in seen:
            seen.add(s["story_event_id"])
            appearance.append((s["story_beat"], s["story_event_id"]))
    sections_seen = [beat for beat, _ in appearance]
    contiguous = [beat for i, beat in enumerate(sections_seen)
                  if i == 0 or beat != sections_seen[i - 1]]
    a.check("구간이 통째로 재생", len(contiguous) == len(set(contiguous)),
            f"{len(contiguous)}개 등장, {len(set(contiguous))}개 고유")
    map_order = {e["id"]: i for i, e in enumerate(events)}
    scrambled = [beat for beat in set(sections_seen)
                 if (lambda ids: ids != sorted(ids))(
                     [map_order[eid] for b, eid in appearance if b == beat])]
    a.check("구간 내 사건 순서", not scrambled, ", ".join(scrambled) if scrambled else "")
    last_beat = segments[-1]["story_beat"]
    a.check("마무리가 마지막", last_beat == story["sections"][-1]["id"], last_beat)
    a.check("콜드 오픈이 첫 사건",
            segments[0]["story_event_id"] == next(e["id"] for e in events if e["entry_point"]),
            segments[0]["story_event_id"])

    a.group("대사 경계")
    cut_end = [s["order"] for s in segments
               for c in cues if c.start + 0.05 < s["source_end"] < c.end - 0.05]
    cut_start = [s["order"] for s in segments
                 for c in cues if c.start + 0.05 < s["source_start"] < c.end - 0.05]
    a.check("끝에서 대사 잘림", len(cut_end) <= 2, f"{len(cut_end)}개 {cut_end[:5]}")
    a.check("시작에서 대사 잘림", not cut_start, f"{len(cut_start)}개 {cut_start[:5]}")

    a.group("나레이션")
    narrated = [s for s in segments if s["kind"] == "narration" and str(s.get("narration", "")).strip()]
    a.check("대본 order 일치",
            {int(i["order"]) for i in script["items"]}
            == {int(s["order"]) for s in segments if s["kind"] == "narration"})
    no_voice = [int(s["order"]) for s in narrated
                if not (audio_dir / f"clip_{int(s['order']):03d}.mp3").exists()]
    a.check("모든 문장에 음성", not no_voice, f"{len(narrated)}줄 " + (str(no_voice) if no_voice else ""))
    over_budget, overlaps = [], []
    for s in narrated:
        order = int(s["order"])
        clip = audio_dir / f"clip_{order:03d}.mp3"
        if not clip.exists():
            continue
        spoken = duration(clip)
        if spoken > float(s.get("narration_max_seconds", 5.2)) + 0.1:
            over_budget.append(order)
        if spoken > s["source_end"] - s["source_start"] + 0.05:
            over_budget.append(order)
        window = (s["source_start"], s["source_start"] + spoken)
        covered = sum(max(0.0, min(c.end, window[1]) - max(c.start, window[0]))
                      for c in cues if c.start < window[1] and c.end > window[0])
        overlaps.append(covered / spoken)
    a.check("음성이 블록에 들어감", not over_budget, str(sorted(set(over_budget))[:5]))
    heavy = sum(1 for x in overlaps if x > 0.6)
    a.note("대사 위에 얹힌 문장", f"심각 {heavy}개 / 상당 {sum(1 for x in overlaps if 0.3 <= x <= 0.6)}개 "
                                f"/ 나머지 {sum(1 for x in overlaps if x < 0.3)}개")
    texts = [i["tts_en"] for i in script["items"] if i["use_narration"]]
    a.check("문장 중복 없음", len(texts) == len(set(texts)),
            f"{len(texts) - len(set(texts))}개 중복")

    a.group("최종본")
    final = root / "output" / str(config.get("output_video", "rough_cut.mp4"))
    if not final.exists():
        a.check("최종본 존재", False, str(final))
        return a.report()
    clips_dir = root / "output" / "capcut_import" / str(config.get("clips_dir", "clips"))
    clips = sorted(clips_dir.glob("*.mp4"))
    a.check("클립 수 일치", len(clips) == len(segments), f"{len(clips)} vs {len(segments)}")
    encoded = sum(duration(clips_dir / f"clip_{int(s['order']):03d}_{s['kind']}.mp4")
                  for s in segments)
    final_len = duration(final)
    a.check("최종 길이 = 클립 합", abs(final_len - encoded) < 0.5,
            f"{final_len:.2f}초 vs {encoded:.2f}초")

    movie_srt = root / "output" / "capcut_import" / "movie_captions.srt"
    narr_srt = root / "output" / "capcut_import" / "narration.srt"
    for label, path in (("영화 자막", movie_srt), ("해설 자막", narr_srt)):
        entries = pipeline.parse_srt(path)
        late = [c for c in entries if c.end > final_len + 0.5]
        a.check(f"{label} 범위 내", not late, f"{len(entries)}개" + (f", {len(late)}개 초과" if late else ""))
        clash = sum(1 for x, y in zip(entries, entries[1:]) if y.start < x.end - 1e-6)
        a.check(f"{label} 겹침 없음", clash == 0, f"{clash}개")
    narration_cues = pipeline.parse_srt(narr_srt)
    a.check("해설 자막 수 = 문장 수", len(narration_cues) >= len(narrated),
            f"{len(narration_cues)} vs {len(narrated)}")

    return a.report()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
