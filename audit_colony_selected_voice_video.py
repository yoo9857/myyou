from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"
VIDEO = OUTPUT / "rough_cut_v5_selected_voice_cinema_captions.mp4"
MOVIE_SRT = CAPCUT / "movie_captions.srt"
NARRATION_SRT = CAPCUT / "narration.srt"
MANIFEST = CAPCUT / "narration_audio" / "manifest.json"
REPORT = OUTPUT / "COLONY_SELECTED_VOICE_VIDEO_QA.json"


def srt_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_srt(path: Path) -> list[tuple[float, float]]:
    pattern = re.compile(
        r"(?m)^(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})$"
    )
    return [(srt_time(start), srt_time(end)) for start, end in pattern.findall(path.read_text(encoding="utf-8-sig"))]


def probe(path: Path) -> dict[str, object]:
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,sample_rate,channels",
            "-of", "json", str(path),
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    return json.loads(raw)


def main() -> int:
    movie = parse_srt(MOVIE_SRT)
    narration = parse_srt(NARRATION_SRT)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    overlaps = [
        {"movie": [ms, me], "narration": [ns, ne]}
        for ms, me in movie
        for ns, ne in narration
        if ms < ne and ns < me
    ]
    media = probe(VIDEO)
    duration = float(media["format"]["duration"])
    streams = media["streams"]
    video_stream = next(stream for stream in streams if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in streams if stream["codec_type"] == "audio")
    report = {
        "status": "pass" if not overlaps and len(narration) == len(manifest) else "fail",
        "voice_id": "Vuo6zmtjWmlDbzqgIDos",
        "voice_model": "eleven_v3",
        "voice_settings": "provider defaults; no style/accent override",
        "duration_sec": round(duration, 3),
        "duration_in_target_window": 19 * 60 <= duration <= 25 * 60,
        "video": {
            "codec": video_stream["codec_name"],
            "width": video_stream["width"],
            "height": video_stream["height"],
        },
        "audio": {
            "codec": audio_stream["codec_name"],
            "sample_rate": int(audio_stream["sample_rate"]),
            "channels": audio_stream["channels"],
        },
        "movie_caption_count": len(movie),
        "narration_caption_count": len(narration),
        "narration_audio_count": len(manifest),
        "movie_narration_overlap_count": len(overlaps),
        "overlaps": overlaps,
        "caption_style": {
            "movie": "clean white, lower safe area, no box",
            "narration": "warm ivory, raised above movie captions, no box",
        },
        "final_video": str(VIDEO),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
