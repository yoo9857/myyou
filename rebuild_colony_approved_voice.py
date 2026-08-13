from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"
BASE_VIDEO = OUTPUT / "rough_cut_v4_curiosity_hook.mp4"
SOURCE_AUDIO = ROOT / "work" / "audio" / "movie_audio_16k_mono.mp3"
OLD_SRT = (
    ROOT / "backups" / "colony_before_voice_caption_v2_20260812"
    / "output" / "capcut_import" / "narration.srt"
)
OLD_TIMELINE = (
    ROOT / "backups" / "colony_before_voice_caption_v2_20260812"
    / "output" / "capcut_import" / "timeline.csv"
)
NEW_SRT = CAPCUT / "narration.srt"
MANIFEST = CAPCUT / "narration_audio" / "manifest.json"
FILTER_SCRIPT = ROOT / "work" / "approved_voice_filtergraph.txt"
NEW_AUDIO_VIDEO = OUTPUT / "rough_cut_v5_approved_voice_clean_audio.mp4"
CURRENT_CAPTIONED = OUTPUT / "rough_cut_v5_selected_voice_cinema_captions.mp4"
NEW_CAPTIONED = OUTPUT / "rough_cut_v5_approved_voice_cinema_captions.mp4"


def run(command: list[str]) -> None:
    print(subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def srt_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def srt_intervals(path: Path) -> list[tuple[float, float]]:
    pattern = re.compile(
        r"(?m)^(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})$"
    )
    return [
        (srt_time(start), srt_time(end))
        for start, end in pattern.findall(path.read_text(encoding="utf-8-sig"))
    ]


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 0.02:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def main() -> int:
    if not CURRENT_CAPTIONED.exists():
        # This render is the caption source: its burnt-in video track is copied
        # verbatim. It is not kept around after a successful run, so rebuild it first.
        raise FileNotFoundError(
            f"{CURRENT_CAPTIONED.name} is absent. Run build_colony_selected_voice_video.py "
            "first to burn the caption tracks, then re-run this script."
        )
    required = [BASE_VIDEO, SOURCE_AUDIO, OLD_SRT, OLD_TIMELINE, NEW_SRT, MANIFEST]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

    old_intervals = srt_intervals(OLD_SRT)
    new_intervals = srt_intervals(NEW_SRT)
    replace_intervals = merge_intervals(old_intervals + new_intervals)
    with OLD_TIMELINE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    timeline_by_order = {int(row["order"]): float(row["timeline_start"]) for row in rows}

    def owning_row(start: float, end: float) -> dict[str, str]:
        for row in rows:
            timeline_start = float(row["timeline_start"])
            timeline_end = float(row["timeline_end"])
            if timeline_start - 0.002 <= start and end <= timeline_end + 0.002:
                return row
        raise RuntimeError(f"No source mapping for replacement interval {start:.3f}-{end:.3f}")

    mute = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in replace_intervals)
    filters = [
        f"[0:a]aresample=48000,volume='if(gt({mute},0),0,1)':eval=frame[base]"
    ]
    source_labels = "".join(f"[src{index}]" for index in range(len(replace_intervals)))
    filters.append(f"[1:a]asplit={len(replace_intervals)}{source_labels}")
    mix_labels = ["[base]"]

    for index, (start, end) in enumerate(replace_intervals):
        row = owning_row(start, end)
        timeline_start = float(row["timeline_start"])
        source_start = float(row["source_start"]) + start - timeline_start
        source_end = source_start + end - start
        local_duck = []
        for narration_start, narration_end in new_intervals:
            overlap_start = max(start, narration_start)
            overlap_end = min(end, narration_end)
            if overlap_start < overlap_end:
                local_duck.append(
                    f"between(t,{overlap_start - start:.3f},{overlap_end - start:.3f})"
                )
        volume = "0.96"
        if local_duck:
            volume = f"'if(gt({'+'.join(local_duck)},0),0.20,0.96)':eval=frame"
        delay_ms = round(start * 1000)
        label = f"clean{index}"
        filters.append(
            f"[src{index}]atrim=start={source_start:.3f}:end={source_end:.3f},"
            f"asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={volume},adelay={delay_ms}:all=1[{label}]"
        )
        mix_labels.append(f"[{label}]")

    inputs = ["-i", str(BASE_VIDEO), "-i", str(SOURCE_AUDIO)]
    for input_index, item in enumerate(manifest, 2):
        order = int(item["order"])
        voice = CAPCUT / "narration_audio" / str(item["file"])
        if not voice.exists():
            raise FileNotFoundError(voice)
        delay_ms = round(timeline_by_order[order] * 1000)
        label = f"voice{order}"
        inputs.extend(["-i", str(voice)])
        filters.append(
            f"[{input_index}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"volume=1.0,adelay={delay_ms}:all=1[{label}]"
        )
        mix_labels.append(f"[{label}]")

    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=first:normalize=0,"
        "alimiter=limit=0.891251[aout]"
    )
    FILTER_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    FILTER_SCRIPT.write_text(";\n".join(filters) + "\n", encoding="utf-8")

    run(
        [
            "ffmpeg", "-y", "-v", "error", *inputs,
            # ffmpeg 7.1+ removed -filter_complex_script; -/opt reads the value from a file.
            "-/filter_complex", str(FILTER_SCRIPT),
            "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(NEW_AUDIO_VIDEO),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(CURRENT_CAPTIONED),
            "-i", str(NEW_AUDIO_VIDEO), "-map", "0:v:0", "-map", "1:a:0",
            "-c", "copy", "-movflags", "+faststart", str(NEW_CAPTIONED),
        ]
    )
    print(
        json.dumps(
            {
                "old_narration_intervals_removed": len(old_intervals),
                "approved_narration_count": len(manifest),
                "clean_replacement_intervals": len(replace_intervals),
                "audio_video": str(NEW_AUDIO_VIDEO),
                "captioned_video": str(NEW_CAPTIONED),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
