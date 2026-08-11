from __future__ import annotations

import json
import html
import re
import subprocess
from pathlib import Path

from pipeline import parse_srt, write_srt


ROOT = Path(__file__).resolve().parent / "Constantine"
V5 = ROOT / "story_review_v5"
OUTPUT = V5 / "output"
CLIPS = OUTPUT / "capcut_import" / "clips"
SOURCE = ROOT / "Constantine.2005.2160p.4K.BluRay.x265.10bit.AAC5.1-[YTS.MX].mkv"
SOURCE_EN = OUTPUT / "source_english.srt"

ENGLISH_REVIEW = [
    "In Mexico's ruins, Manuel uncovers an ancient spear…",
    "From then on, an ordinary life quietly twists.",
    "Hardly museum material—it changes whoever finds it.",
    "In Los Angeles, John Constantine enters a possessed girl's room.",
    "He skips the prayer and reads the signs left behind.",
    "He should be praying, yet he searches with suspicious calm.",
    "Isabel jumped, but Angela refuses to accept it.",
    "Shaken by the exorcism, Constantine visits Beeman…",
    "The demon's name matters less than who broke the rules.",
    "After the attack, he turns to the neutral Midnite.",
    "Here, Heaven and Hell agree to stop fighting.",
    "To trace Isabel, Constantine gathers her things—and a cat.",
    "The search leaves evidence behind and follows the dead.",
    "Tap water, a cat, and a trip to Hell. Oddly practical.",
    "Hell looks like a ruined world layered over reality.",
    "Then Beeman's voice dies, and they race to him.",
    "Angela never wanted the gift—only a way to reach Isabel.",
    "Once she sees the truth, it starts looking back.",
    "Her senses restored, Angela follows the demon's trace…",
    "She is no longer the client, but the eyes hunting the demon.",
    "Her 'useless' visions become a demon-only GPS.",
    "The same gift makes Angela both clue and target.",
    "Angela vanishes, sending Constantine back to Midnite.",
    "Neutrality now sounds like an excuse to stand still.",
    "Constantine and Chas race to the hospital holding Angela…",
    "The enemy thins out, but so does the time left.",
    "Mammon's arrival is no longer prophecy. It is here.",
    "With no answer from either side, Constantine pushes on…",
    "His final choice is yours to discover.",
]


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        encoding="utf-8",
    ).strip())


def clean_caption(text: str) -> str:
    plain = re.sub(r"<[^>]+>", "", html.unescape(text))
    return re.sub(r"\s+", " ", plain).strip()


def subtract_review(start: float, end: float, review: list[tuple[float, float, str]]) -> list[tuple[float, float]]:
    parts = [(start, end)]
    for ns, ne, _ in review:
        blocked_start, blocked_end = ns - 0.12, ne + 0.12
        next_parts: list[tuple[float, float]] = []
        for ps, pe in parts:
            if pe <= blocked_start or ps >= blocked_end:
                next_parts.append((ps, pe))
                continue
            if blocked_start - ps >= 0.2:
                next_parts.append((ps, blocked_start))
            if pe - blocked_end >= 0.2:
                next_parts.append((blocked_end, pe))
        parts = next_parts
        if not parts:
            break
    return parts


def main() -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE), "-map", "0:s:0", "-c:s", "srt", str(SOURCE_EN)],
        check=True,
    )
    source_cues = parse_srt(SOURCE_EN)
    plan = json.loads((OUTPUT / "edit_plan.json").read_text(encoding="utf-8"))
    korean_review = parse_srt(OUTPUT / "narration_v4_outro.srt")
    if len(korean_review) != len(ENGLISH_REVIEW):
        raise ValueError("English review line count does not match the approved review timeline")
    review_entries = [(cue.start, cue.end, text) for cue, text in zip(korean_review, ENGLISH_REVIEW)]

    mapped: list[tuple[float, float, str]] = []
    timeline = 0.0
    for seg in plan["segments"]:
        clip = CLIPS / f"clip_{int(seg['order']):03d}_{seg['kind']}.mp4"
        encoded_duration = duration(clip)
        source_start = float(seg["source_start"])
        source_end = float(seg["source_end"])
        for cue in source_cues:
            if cue.start >= source_end:
                break
            if cue.end <= source_start:
                continue
            start = timeline + max(cue.start, source_start) - source_start
            end = timeline + min(cue.end, source_end) - source_start
            text = clean_caption(cue.text)
            if end - start >= 0.2 and text:
                mapped.append((start, end, text))
        timeline += encoded_duration

    movie_entries: list[tuple[float, float, str]] = []
    for start, end, text in mapped:
        for part_start, part_end in subtract_review(start, end, review_entries):
            movie_entries.append((part_start, part_end, text))
    movie_entries.sort(key=lambda item: (item[0], item[1]))
    combined = sorted(movie_entries + review_entries, key=lambda item: (item[0], item[1]))
    write_srt(movie_entries, OUTPUT / "movie_captions_en.srt")
    write_srt(review_entries, OUTPUT / "narration_v4_outro_en.srt")
    write_srt(combined, OUTPUT / "captions_combined_v4_outro_en.srt")
    report = {
        "source_english_cues": len(source_cues),
        "mapped_before_suppression": len(mapped),
        "movie_cues": len(movie_entries),
        "review_cues": len(review_entries),
        "timeline_main_sec": round(timeline, 6),
        "review_margin_sec": 0.12,
        "language": "en",
        "source_stream": "0:s:0",
    }
    (OUTPUT / "ENGLISH_SUBTITLE_QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
