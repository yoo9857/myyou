from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

from pipeline import parse_srt

ROOT = Path(r"C:\cineyoutube\Constantine\pro_review")
OUTPUT = ROOT / "output"
VIDEO = OUTPUT / "constantine_flow_review_v2_subtitled.mp4"

plan = json.loads((OUTPUT / "edit_plan.json").read_text(encoding="utf-8"))
segments = plan["segments"]
narration = parse_srt(OUTPUT / "narration.srt")
movie = parse_srt(OUTPUT / "movie_captions.srt")
combined = parse_srt(OUTPUT / "captions_combined.srt")
clips = sorted((OUTPUT / "capcut_import" / "clips").glob("*.mp4"))

probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(VIDEO)],
    capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
)
duration = float(probe.stdout.strip())
narration_seconds = sum(c.end - c.start for c in narration)
narration_gaps = [narration[i + 1].start - narration[i].end for i in range(len(narration) - 1)]
caption_overlaps = sum(combined[i + 1].start < combined[i].end - 0.02 for i in range(len(combined) - 1))
main = segments[1:]

report = {
    "voice_generation": "OFF",
    "final_duration_seconds": round(duration, 3),
    "segment_count": len(segments),
    "narrated_segment_count": len(narration),
    "movie_caption_count": len(movie),
    "combined_caption_count": len(combined),
    "caption_overlaps": caption_overlaps,
    "narration_text_window_percent": round(100 * narration_seconds / duration, 1),
    "narration_gap_median_seconds": round(statistics.median(narration_gaps), 2),
    "narration_gap_p90_seconds": round(sorted(narration_gaps)[int(0.9 * (len(narration_gaps) - 1))], 2),
    "narration_gap_max_seconds": round(max(narration_gaps), 2),
    "clip_length_min_seconds": round(min(s["source_end"] - s["source_start"] for s in segments), 2),
    "clip_length_median_seconds": round(statistics.median(s["source_end"] - s["source_start"] for s in segments), 2),
    "clip_length_max_seconds": round(max(s["source_end"] - s["source_start"] for s in segments), 2),
    "main_sequence_source_monotonic": all(main[i + 1]["source_start"] >= main[i]["source_start"] for i in range(len(main) - 1)),
    "main_sequence_last_source_second": max(s["source_end"] for s in main),
    "rendered_clip_count": len(clips),
    "zero_byte_clip_count": sum(p.stat().st_size == 0 for p in clips),
}
(ROOT / "work" / "QA_FLOW.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
