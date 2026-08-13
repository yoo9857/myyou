"""Measure a reference review's spoken-flow structure from its captions.

Produces the metrics JSON that `work/references/learning_registry.json` points at, in the
same shape as the existing entries so profiles stay comparable.

What the numbers are and are not:

YouTube automatic captions transcribe *everything spoken* — the reviewer and the film's
own dialogue alike — and they roll, so consecutive cues overlap. So this merges
overlapping cues into continuous "spoken regions" and reports coverage of those. Coverage
is therefore continuity of speech, not narration share, and a caption-free window is not
silence: it may hold movie dialogue in another language, action, music or effects.

Usage:
    python scripts/analyze_reference.py <video_url_or_id> [--profile "short-breath ..."]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "work" / "references"
MERGE_TOLERANCE = 0.08
WINDOW = 300.0


def video_id(value: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", value)
    return m.group(1) if m else value


def probe_metadata(vid: str) -> dict:
    out = subprocess.run(
        ["yt-dlp", "--skip-download", "--no-warnings", "--dump-single-json",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", errors="replace")
    d = json.loads(out)
    return {
        "title": d.get("title"),
        "channel": d.get("channel") or d.get("uploader"),
        "duration_seconds": float(d.get("duration") or 0.0),
        "view_count": d.get("view_count"),
        "upload_date": d.get("upload_date"),
    }


def fetch_subs(vid: str) -> Path:
    existing = sorted(REFS.glob(f"{vid}.*.srt"))
    if not existing:
        subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
             "--sub-langs", "ko,ko-orig,en,en-orig", "--convert-subs", "srt",
             "--no-warnings", "-o", "%(id)s.%(ext)s",
             f"https://www.youtube.com/watch?v={vid}"],
            cwd=REFS, check=True, capture_output=True,
        )
        existing = sorted(REFS.glob(f"{vid}.*.srt"))
    if not existing:
        raise SystemExit(f"no captions available for {vid}")
    # Prefer the original-language track over a translation.
    for path in existing:
        if "orig" in path.name:
            return path
    return existing[0]


def cues(path: Path) -> list[tuple[float, float]]:
    pattern = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})")
    out = []
    for g in pattern.findall(path.read_text(encoding="utf-8-sig", errors="replace")):
        a = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        b = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        if b > a:
            out.append((a, b))
    return sorted(out)


def merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1] + MERGE_TOLERANCE:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "p75": 0.0, "p90": 0.0}
    ordered = sorted(values)
    def pick(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))]
    return {"median": round(statistics.median(ordered), 2),
            "p75": round(pick(0.75), 2), "p90": round(pick(0.90), 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--profile", default="unclassified")
    args = ap.parse_args()

    vid = video_id(args.video)
    REFS.mkdir(parents=True, exist_ok=True)
    meta = probe_metadata(vid)
    sub_path = fetch_subs(vid)
    raw = cues(sub_path)
    regions = merge(raw)
    duration = meta["duration_seconds"] or (regions[-1][1] if regions else 0.0)

    spoken = sum(b - a for a, b in regions)
    gaps = [regions[i + 1][0] - regions[i][1] for i in range(len(regions) - 1)]
    gaps = [g for g in gaps if g > 0]

    windows = []
    edge = 0.0
    while edge < duration:
        top = min(edge + WINDOW, duration)
        covered = sum(max(0.0, min(b, top) - max(a, edge)) for a, b in regions)
        windows.append({
            "window": f"{int(edge)//60:02d}:{int(edge)%60:02d}-{int(top)//60:02d}:{int(top)%60:02d}",
            "percent": round(covered / (top - edge) * 100, 1),
        })
        edge = top

    rq = quantiles([b - a for a, b in regions])
    gq = quantiles(gaps)
    metrics = {
        "source": f"https://www.youtube.com/watch?v={vid}",
        "video_id": vid,
        "title": meta["title"],
        "channel": meta["channel"],
        "duration_seconds": duration,
        "analysis_basis": "YouTube Korean automatic captions; overlapping caption intervals "
                          f"merged with {MERGE_TOLERANCE}-second tolerance",
        "limitations": "Automatic captions transcribe reviewer speech and movie dialogue "
                       "together, so coverage measures spoken-flow continuity rather than "
                       "narration share. Caption-free windows may contain movie dialogue, "
                       "reactions, action, music, or effects and must not be read as silence.",
        "subtitle_cues": len(raw),
        "merged_korean_caption_regions": len(regions),
        "caption_interval_coverage_percent": round(spoken / duration * 100, 1) if duration else 0.0,
        "merged_caption_region_duration_median_seconds": rq["median"],
        "merged_caption_region_duration_p75_seconds": rq["p75"],
        "merged_caption_region_duration_p90_seconds": rq["p90"],
        "narrator_free_gap_median_seconds": gq["median"],
        "narrator_free_gap_p75_seconds": gq["p75"],
        "narrator_free_gap_p90_seconds": gq["p90"],
        "narrator_free_gaps_ge_2_seconds": sum(1 for g in gaps if g >= 2),
        "narrator_free_gaps_ge_4_seconds": sum(1 for g in gaps if g >= 4),
        "narrator_free_gaps_ge_8_seconds": sum(1 for g in gaps if g >= 8),
        "coverage_by_window": windows,
        "editorial_profile": args.profile,
        "copyright_rule": "Learn timing, density, handoff structure, and dialogue placement "
                          "only. Do not copy sentences, jokes, or channel-specific wording.",
        "caption_file": str(sub_path.relative_to(ROOT)).replace("\\", "/"),
    }
    out_path = REFS / f"{vid}.metrics.json"
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"기록: {out_path.relative_to(ROOT)}")
    for key in ("title", "channel", "duration_seconds", "subtitle_cues",
                "merged_korean_caption_regions", "caption_interval_coverage_percent",
                "merged_caption_region_duration_median_seconds",
                "narrator_free_gap_median_seconds", "narrator_free_gaps_ge_4_seconds"):
        print(f"  {key:44} {metrics[key]}")
    print("  구간별 발화 밀도:")
    for w in windows:
        bar = "#" * int(w["percent"] / 3)
        print(f"    {w['window']}  {w['percent']:5.1f}%  {bar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
