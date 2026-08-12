from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"
BASE_VIDEO = OUTPUT / "rough_cut_v4_curiosity_hook.mp4"
AUDIO_VIDEO = OUTPUT / "rough_cut_v5_selected_voice.mp4"
CAPTIONED_VIDEO = OUTPUT / "rough_cut_v5_selected_voice_cinema_captions.mp4"
MANIFEST = CAPCUT / "narration_audio" / "manifest.json"
TIMELINE = CAPCUT / "timeline.csv"
MOVIE_SRT = CAPCUT / "movie_captions.srt"
NARRATION_SRT = CAPCUT / "narration.srt"
MOVIE_ASS = CAPCUT / "movie_captions_cinema_v2.ass"
NARRATION_ASS = CAPCUT / "narration_cinema_v2.ass"


def run(command: list[str]) -> None:
    print(subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def media_duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(path),
            ],
            text=True,
            encoding="utf-8",
        ).strip()
    )


def make_ass(source: Path, target: Path, style_line: str) -> None:
    run(["ffmpeg", "-y", "-v", "error", "-i", str(source), str(target)])
    text = target.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Style: Default,"):
            lines[index] = style_line
            break
    else:
        raise RuntimeError(f"Default ASS style not found in {target}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    required = [BASE_VIDEO, MANIFEST, TIMELINE, MOVIE_SRT, NARRATION_SRT]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

    narration = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with TIMELINE.open("r", encoding="utf-8-sig", newline="") as handle:
        timeline_rows = {int(row["order"]): row for row in csv.DictReader(handle)}

    inputs = ["-i", str(BASE_VIDEO)]
    filters: list[str] = []
    mix_labels = ["[bed]"]
    duck_parts: list[str] = []
    audit_items: list[dict[str, object]] = []
    for input_index, item in enumerate(narration, 1):
        order = int(item["order"])
        audio_path = CAPCUT / "narration_audio" / str(item["file"])
        start = float(timeline_rows[order]["timeline_start"])
        voice_duration = media_duration(audio_path)
        end = start + voice_duration + 0.15
        duck_parts.append(f"between(t,{start:.3f},{end:.3f})")
        delay_ms = round(start * 1000)
        label = f"vo{input_index}"
        inputs.extend(["-i", str(audio_path)])
        filters.append(
            f"[{input_index}:a]aresample=48000,adelay={delay_ms}|{delay_ms},"
            f"volume=1.0[{label}]"
        )
        mix_labels.append(f"[{label}]")
        audit_items.append(
            {
                "order": order,
                "timeline_start": round(start, 3),
                "timeline_end": round(end, 3),
                "voice_duration": round(voice_duration, 3),
                "file": str(audio_path),
            }
        )

    duck_expression = "+".join(duck_parts)
    filters.insert(
        0,
        f"[0:a]aresample=48000,volume='if(gt({duck_expression},0),0.20,0.96)':"
        "eval=frame[bed]",
    )
    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=first:normalize=0,"
        "alimiter=limit=0.891251[aout]"
    )
    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(BASE_VIDEO),
            *inputs[2:], "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(AUDIO_VIDEO),
        ]
    )

    make_ass(
        MOVIE_SRT,
        MOVIE_ASS,
        "Style: Default,Noto Sans KR,18,&H00F8FAFA,&H000000FF,&H00000000,"
        "&H78000000,-1,0,0,0,100,100,0,0,1,1.5,0.7,2,24,24,18,1",
    )
    make_ass(
        NARRATION_SRT,
        NARRATION_ASS,
        "Style: Default,Noto Sans KR,21,&H00AFE8FF,&H000000FF,&H000A0805,"
        "&H80080604,-1,0,0,0,100,100,0.2,0,1,1.3,0.8,2,32,32,48,1",
    )
    filter_video = (
        "subtitles='output/capcut_import/movie_captions_cinema_v2.ass',"
        "subtitles='output/capcut_import/narration_cinema_v2.ass'"
    )
    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(AUDIO_VIDEO),
            "-vf", filter_video, "-c:v", "libx264", "-preset", "fast",
            "-crf", "19", "-c:a", "copy", "-movflags", "+faststart",
            str(CAPTIONED_VIDEO),
        ]
    )

    report = {
        "voice_id": "Vuo6zmtjWmlDbzqgIDos",
        "voice_settings": "voice defaults (no request override)",
        "narration_count": len(narration),
        "movie_caption_style": "clean white cinema subtitle",
        "narration_caption_style": "warm ivory, raised, no background box",
        "audio_video": str(AUDIO_VIDEO),
        "captioned_video": str(CAPTIONED_VIDEO),
        "duration_sec": round(media_duration(CAPTIONED_VIDEO), 3),
        "narration": audit_items,
    }
    (OUTPUT / "COLONY_SELECTED_VOICE_VIDEO_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
