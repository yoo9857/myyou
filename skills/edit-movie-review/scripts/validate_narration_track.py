from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str


def seconds(value: str) -> float:
    h, m, rest = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def parse_srt(path: Path) -> list[Cue]:
    blocks = re.split(r"\n{2,}", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip())
    timing = re.compile(r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})")
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        pos = next((i for i, line in enumerate(lines) if timing.search(line)), None)
        if pos is None:
            continue
        match = timing.search(lines[pos])
        assert match
        cues.append(Cue(len(cues) + 1, seconds(match.group(1)), seconds(match.group(2)), " ".join(lines[pos + 1 :])))
    return cues


def collisions(left: list[Cue], right: list[Cue]) -> list[tuple[int, int]]:
    hits = []
    for a in left:
        for b in right:
            if b.start >= a.end:
                break
            if max(a.start, b.start) < min(a.end, b.end):
                hits.append((a.index, b.index))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate movie-dialogue and reviewer narration SRT tracks")
    parser.add_argument("--movie-srt", required=True, type=Path)
    parser.add_argument("--narration-srt", required=True, type=Path)
    parser.add_argument("--video-duration", type=float)
    parser.add_argument("--margin", type=float, default=0.12)
    parser.add_argument("--max-korean-chars-per-sec", type=float, default=5.8)
    parser.add_argument("--allow-meta-viewpoint", action="store_true")
    parser.add_argument("--allow-formal-style", action="store_true")
    args = parser.parse_args()

    movie = parse_srt(args.movie_srt)
    narration = parse_srt(args.narration_srt)
    errors = []
    for label, cues in (("movie", movie), ("narration", narration)):
        for previous, current in zip(cues, cues[1:]):
            if current.start < previous.end:
                errors.append(f"{label.upper()}_OVERLAP:{previous.index}:{current.index}")
        for cue in cues:
            if cue.start < 0 or cue.end <= cue.start:
                errors.append(f"{label.upper()}_BAD_TIME:{cue.index}")
            if args.video_duration is not None and cue.end > args.video_duration + 0.05:
                errors.append(f"{label.upper()}_PAST_VIDEO:{cue.index}")

    for a, b in collisions(narration, movie):
        errors.append(f"TRACK_COLLISION:narration={a}:movie={b}")
    for narration_cue in narration:
        following = next((cue for cue in movie if cue.start >= narration_cue.end), None)
        if following and following.start - narration_cue.end < args.margin - 0.001:
            errors.append(
                f"MOVIE_RESUME_MARGIN:narration={narration_cue.index}:"
                f"movie={following.index}:gap={following.start - narration_cue.end:.3f}"
            )

    meta_words = ("관객", "시청자", "영화는", "장면은", "연출은")
    for cue in narration:
        if not args.allow_meta_viewpoint:
            for word in meta_words:
                if word in cue.text:
                    errors.append(f"META_VIEWPOINT:{cue.index}:{word}")
        if not args.allow_formal_style and ("입니다" in cue.text or "습니다" in cue.text):
            errors.append(f"FORMAL_REPORT_STYLE:{cue.index}")
        korean_chars = len(re.findall(r"[가-힣]", cue.text))
        rate = korean_chars / max(cue.end - cue.start, 0.001)
        if rate > args.max_korean_chars_per_sec:
            errors.append(f"SPEECH_RATE:{cue.index}:{rate:.2f}")

    report = {
        "movie_cues": len(movie),
        "narration_cues": len(narration),
        "margin_sec": args.margin,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
