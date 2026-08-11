from __future__ import annotations

import json
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(r"C:\cineyoutube")
CORPUS = ROOT / "Constantine" / "work" / "reference_corpus"
ITEMS = [
    {
        "id": "1bj4tjZwjXQ", "channel": "movie trip 무비트립", "label": "사용자 기준 영상",
        "video": ROOT / "Constantine" / "work" / "reference" / "reference.mp4",
        "srt": ROOT / "work" / "references" / "1bj4tjZwjXQ.ko.srt",
    },
    {
        "id": "mn3SxPGZUrE", "channel": "지무비 : G Movie", "label": "오컬트 영화 리뷰",
        "video": CORPUS / "mn3SxPGZUrE.mp4", "srt": CORPUS / "mn3SxPGZUrE.ko.srt",
    },
    {
        "id": "IaVTL08U7w8", "channel": "고몽", "label": "드라마 영화 리뷰",
        "video": CORPUS / "IaVTL08U7w8.mp4", "srt": CORPUS / "IaVTL08U7w8.ko.srt",
    },
    {
        "id": "N4uUtFYnAw4", "channel": "B Man 삐맨", "label": "판타지·악마 영화 리뷰",
        "video": CORPUS / "N4uUtFYnAw4.mp4", "srt": CORPUS / "N4uUtFYnAw4.ko.srt",
    },
    {
        "id": "B68bXxwQ1Ss", "channel": "movie trip", "label": "action movie review",
        "video": CORPUS / "B68bXxwQ1Ss.mp4", "srt": ROOT / "work" / "references" / "B68bXxwQ1Ss.ko.srt",
    },
    {
        "id": "umzi1CWE5mw", "channel": "Movie 101", "label": "user-selected storytelling reference",
        "video": CORPUS / "umzi1CWE5mw" / "umzi1CWE5mw.mp4",
        "srt": CORPUS / "umzi1CWE5mw" / "umzi1CWE5mw.ko-orig.srt",
    },
]


def seconds(value: str) -> float:
    h, m, tail = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(tail)


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    lo = int(x)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def parse(path: Path):
    blocks = re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8-sig").strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        timing = next((line for line in lines if " --> " in line), None)
        if not timing:
            continue
        start, end = timing.split(" --> ")
        text = " ".join(lines[lines.index(timing) + 1 :]).strip()
        cues.append((seconds(start), seconds(end), text))
    return cues


def analyze(item):
    cues = parse(item["srt"])
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(item["video"])],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout.strip())
    intervals = []
    for start, end, _ in cues:
        if intervals and start <= intervals[-1][1] + 0.08:
            intervals[-1][1] = max(intervals[-1][1], end)
        else:
            intervals.append([start, end])
    speech = sum(end - start for start, end in intervals)
    gaps = [intervals[i + 1][0] - intervals[i][1] for i in range(len(intervals) - 1)]

    run = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(item["video"]),
        "-vf", "select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "NUL",
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", run.stderr)]
    boundaries = [0.0, *cuts, duration]
    shots = [b - a for a, b in zip(boundaries, boundaries[1:]) if b > a]

    clean = [text for _, _, text in cues if not re.fullmatch(r"[>\s]*\[.*?\]", text)]
    joined = " ".join(clean)
    connectors = {word: joined.count(word) for word in ("그런데", "하지만", "그러던", "바로", "결국", "한편", "이때", "그렇게")}
    action_terms = {word: joined.count(word) for word in ("찾", "들어", "나타", "다가", "공격", "도망", "향", "꺼내", "잡")}
    lengths = [len(re.sub(r"\s+", "", text)) for text in clean if text]
    return {
        "id": item["id"], "channel": item["channel"], "label": item["label"],
        "duration_seconds": round(duration, 2),
        "subtitle_cues": len(cues),
        "speech_coverage_percent": round(100 * speech / duration, 1),
        "speech_gap_median_seconds": round(statistics.median(gaps), 2),
        "speech_gap_p90_seconds": round(percentile(gaps, .9), 2),
        "scene_cuts": len(cuts),
        "cuts_per_minute": round(60 * len(cuts) / duration, 1),
        "shot_median_seconds": round(statistics.median(shots), 2),
        "shot_p75_seconds": round(percentile(shots, .75), 2),
        "caption_chars_median": round(statistics.median(lengths), 1),
        "connectors": connectors,
        "action_terms": action_terms,
    }


results = [analyze(item) for item in ITEMS]
summary = {
    "references": results,
    "cross_channel_medians": {
        key: round(statistics.median(r[key] for r in results), 2)
        for key in ("speech_coverage_percent", "speech_gap_median_seconds", "cuts_per_minute", "shot_median_seconds", "caption_chars_median")
    },
}
(CORPUS / "CORPUS_METRICS.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
