from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW_ROOT = ROOT / "Constantine" / "story_review_v5"
OUTPUT = REVIEW_ROOT / "output"
AUDIO_ROOT = OUTPUT / "narration_audio_nayva_v1"
MANIFEST = AUDIO_ROOT / "manifest.json"
SOURCE_VIDEO = OUTPUT / "constantine_story_review_v5_with_outro.mp4"
MUSIC_SOURCE = ROOT / "The Final Resolve.mp3"
VOICE_STEM = OUTPUT / "constantine_nayva_voice_stem.wav"
MUSIC_STEM = OUTPUT / "constantine_outro_music_stem.wav"
BED_VIDEO = OUTPUT / "constantine_story_review_v5_ducked_bed.mp4"
FINAL_VIDEO = OUTPUT / "constantine_story_review_v5_nayva_final.mp4"
QA_PATH = OUTPUT / "FINAL_NAYVA_AUDIO_QA.json"
FINAL_DURATION = 1501.021321
OUTRO_START = 1487.0
OUTRO_DURATION = FINAL_DURATION - OUTRO_START
MUSIC_SOURCE_START = 15.0
MUSIC_RISE_REL = 12.1
MUSIC_FADE_REL = 13.1


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def duration(path: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        encoding="utf-8",
    )
    return float(raw.strip())


def build_voice_stem(cues: list[dict[str, object]]) -> None:
    command = ["ffmpeg", "-y", "-v", "error"]
    filters: list[str] = []
    labels: list[str] = []
    for input_index, cue in enumerate(cues):
        path = Path(str(cue["fitted_file"]))
        if not path.exists():
            raise FileNotFoundError(path)
        command += ["-i", str(path)]
        delay_ms = round(float(cue["start_sec"]) * 1000)
        label = f"v{input_index}"
        filters.append(
            f"[{input_index}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={delay_ms}|{delay_ms}[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
        + f"apad=whole_dur={FINAL_DURATION:.6f},atrim=0:{FINAL_DURATION:.6f}[voice]"
    )
    filter_script = AUDIO_ROOT / "voice_stem.ffscript"
    filter_script.write_text(";\n".join(filters) + "\n", encoding="utf-8")
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[voice]",
        "-c:a",
        "pcm_s24le",
        str(VOICE_STEM),
    ]
    run(command)


def build_music_stem() -> None:
    fade_duration = max(0.1, OUTRO_DURATION - MUSIC_FADE_REL)
    volume_expression = "0.10+0.22*clip((t-12.1)/0.5,0,1)"
    audio_filter = (
        f"atrim=start={MUSIC_SOURCE_START:.3f}:duration={OUTRO_DURATION:.6f},"
        "asetpts=PTS-STARTPTS,aresample=48000,"
        f"volume=eval=frame:volume='{volume_expression}',"
        f"afade=t=out:st={MUSIC_FADE_REL:.3f}:d={fade_duration:.6f}"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(MUSIC_SOURCE),
            "-af",
            audio_filter,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(MUSIC_STEM),
        ]
    )


def build_ducked_bed() -> None:
    # The prior outro already contains a very quiet copy of the same song.
    # Mute that region before laying the approved music stem back once.
    filter_complex = (
        f"[0:a]aresample=48000,volume=eval=frame:volume='if(gte(t,{OUTRO_START:.3f}),0,1)'[movie];"
        "[movie][1:a]sidechaincompress=threshold=0.008:ratio=14:attack=140:release=650:makeup=1[bed]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(SOURCE_VIDEO),
            "-i",
            str(VOICE_STEM),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[bed]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{FINAL_DURATION:.6f}",
            str(BED_VIDEO),
        ]
    )


def build_final() -> None:
    delay_ms = round(OUTRO_START * 1000)
    filter_complex = (
        f"[2:a]adelay={delay_ms}|{delay_ms}[music];"
        "[0:a][1:a][music]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.88:attack=5:release=80:level=false[mix]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(BED_VIDEO),
            "-i",
            str(VOICE_STEM),
            "-i",
            str(MUSIC_STEM),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-movflags",
            "+faststart",
            "-t",
            f"{FINAL_DURATION:.6f}",
            str(FINAL_VIDEO),
        ]
    )


def main() -> int:
    report = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cues = list(report["cues"])
    if len(cues) != 29:
        raise RuntimeError(f"Expected 29 voice cues, found {len(cues)}")
    build_voice_stem(cues)
    build_music_stem()
    build_ducked_bed()
    build_final()
    qa = {
        "schema_version": 1,
        "final_video": str(FINAL_VIDEO),
        "source_video": str(SOURCE_VIDEO),
        "voice": report["voice"],
        "voice_model": report["model"],
        "voice_cues": len(cues),
        "voice_stem": str(VOICE_STEM),
        "movie_bed_video": str(BED_VIDEO),
        "movie_duck": {"threshold": 0.008, "ratio": 14, "attack_ms": 140, "release_ms": 650},
        "outro_music": str(MUSIC_SOURCE),
        "outro_music_stem": str(MUSIC_STEM),
        "outro_start_sec": OUTRO_START,
        "music_source_start_sec": MUSIC_SOURCE_START,
        "music_speech_gain": 0.10,
        "music_post_speech_gain": 0.32,
        "music_rise_relative_sec": MUSIC_RISE_REL,
        "music_fade_relative_sec": MUSIC_FADE_REL,
        "source_duration_sec": duration(SOURCE_VIDEO),
        "voice_stem_duration_sec": duration(VOICE_STEM),
        "music_stem_duration_sec": duration(MUSIC_STEM),
        "final_duration_sec": duration(FINAL_VIDEO),
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
