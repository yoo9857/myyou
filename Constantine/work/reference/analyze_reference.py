from __future__ import annotations

import json
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRT = Path(r"C:\cineyoutube\work\references\1bj4tjZwjXQ.ko.srt")
VIDEO = ROOT / "reference.mp4"


def ts(value: str) -> float:
    h, m, tail = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(tail)


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


blocks = re.split(r"\r?\n\r?\n", SRT.read_text(encoding="utf-8-sig").strip())
cues = []
for block in blocks:
    lines = block.splitlines()
    timing = next((line for line in lines if " --> " in line), None)
    if not timing:
        continue
    start, end = timing.split(" --> ")
    text_lines = lines[lines.index(timing) + 1 :]
    text = " ".join(text_lines).strip()
    cues.append((ts(start), ts(end), text))

# YouTube auto captions overlap. Merge their intervals to measure real speech coverage.
intervals = []
for start, end, _ in cues:
    if intervals and start <= intervals[-1][1] + 0.08:
        intervals[-1][1] = max(intervals[-1][1], end)
    else:
        intervals.append([start, end])
speech_seconds = sum(end - start for start, end in intervals)
gaps = [intervals[i + 1][0] - intervals[i][1] for i in range(len(intervals) - 1)]

command = [
    "ffmpeg", "-hide_banner", "-nostats", "-i", str(VIDEO),
    "-vf", "select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "NUL",
]
run = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
cuts = [float(v) for v in re.findall(r"pts_time:([0-9.]+)", run.stderr)]
duration_run = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(VIDEO)],
    text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
)
duration = float(duration_run.stdout.strip())
boundaries = [0.0, *cuts, duration]
shots = [b - a for a, b in zip(boundaries, boundaries[1:]) if b > a]

report = {
    "video_duration_seconds": round(duration, 3),
    "subtitle_cues": len(cues),
    "merged_speech_regions": len(intervals),
    "speech_coverage_percent": round(100 * speech_seconds / duration, 1),
    "silence_gap_median_seconds": round(statistics.median(gaps), 2) if gaps else 0,
    "silence_gap_p90_seconds": round(percentile(gaps, 0.9), 2) if gaps else 0,
    "scene_cuts_threshold_025": len(cuts),
    "cuts_per_minute": round(60 * len(cuts) / duration, 1),
    "shot_length_median_seconds": round(statistics.median(shots), 2),
    "shot_length_p25_seconds": round(percentile(shots, 0.25), 2),
    "shot_length_p75_seconds": round(percentile(shots, 0.75), 2),
    "shot_length_p90_seconds": round(percentile(shots, 0.9), 2),
    "transcript_samples": [
        {"start": cues[i][0], "end": cues[i][1], "text": cues[i][2]}
        for i in [0, min(20, len(cues)-1), min(80, len(cues)-1), min(160, len(cues)-1), len(cues)-1]
    ],
}
(ROOT / "reference_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
