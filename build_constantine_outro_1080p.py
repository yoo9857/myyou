"""Rebuild the Constantine outro at 1920x1080 to match the re-rendered 1080p cut.

The outro was originally produced by a one-off command that never made it into the
repo, so it is reconstructed from outro_plan.v1.json plus the observable properties of
the 540p file it replaces: 337 frames at 24 fps, h264 + aac 48 kHz stereo.

Audio is rendered silent on purpose. The mix mutes the movie bed from OUTRO_START and
supplies the outro music as its own stem, so any audio baked in here would be discarded
anyway -- and keeping it would risk doubling the music if that ever changed.

The frame count is asserted, because the concat that follows uses -c copy and the whole
caption timeline hangs off the total duration.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "Constantine" / "story_review_v5"
OUTPUT = REVIEW / "output"
PLAN = OUTPUT / "outro_plan.v1.json"
REFERENCE = OUTPUT / "outro_v1.mp4"
DESTINATION = OUTPUT / "outro_v1_1080p.mp4"

WIDTH, HEIGHT, FPS = 1920, 1080, 24
CRF, PRESET = "19", "medium"
EXPECTED_FRAMES = 337


def probe(path: Path, entries: str, stream: str | None = None) -> str:
    command = ["ffprobe", "-v", "error"]
    if stream:
        command += ["-select_streams", stream]
    command += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    return subprocess.check_output(command, text=True, encoding="utf-8").strip()


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source = REVIEW / json.loads((REVIEW / "config.json").read_text(encoding="utf-8"))["video"]
    if not source.exists():
        raise FileNotFoundError(source)

    frames = int(probe(REFERENCE, "stream=nb_frames", "v:0"))
    if frames != EXPECTED_FRAMES:
        raise RuntimeError(f"{REFERENCE.name} has {frames} frames, expected {EXPECTED_FRAMES}")
    duration = frames / FPS
    fade = float(plan.get("video_fade_out_sec", 0.9))
    fade_start = duration - fade
    start = float(plan["source_start"])

    video_filters = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},format=yuv420p,"
        f"fade=t=out:st={fade_start:.6f}:d={fade:.3f}"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
        # Read a little extra and pin the output frame count instead of trusting -t:
        # at the fps-filter boundary -t 14.041667 emitted 338 frames, one too many.
        "-ss", f"{start:.3f}", "-t", f"{duration + 0.5:.6f}", "-i", str(source),
        "-f", "lavfi", "-t", f"{duration:.6f}", "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", video_filters, "-frames:v", str(EXPECTED_FRAMES),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-y", str(DESTINATION),
    ]
    print(subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, check=True)

    got_frames = int(probe(DESTINATION, "stream=nb_frames", "v:0"))
    got_duration = float(probe(DESTINATION, "format=duration"))
    reference_duration = float(probe(REFERENCE, "format=duration"))
    size = probe(DESTINATION, "stream=width,height", "v:0").split("\n")
    report = {
        "output": str(DESTINATION),
        "resolution": f"{size[0]}x{size[1]}",
        "frames": got_frames,
        "frames_match_reference": got_frames == EXPECTED_FRAMES,
        "duration_sec": got_duration,
        "reference_duration_sec": reference_duration,
        "duration_delta_ms": round((got_duration - reference_duration) * 1000, 3),
        "audio": "silent (the mix mutes the bed here and adds the music stem)",
    }
    print(json.dumps(report, indent=2))
    if got_frames != EXPECTED_FRAMES:
        raise RuntimeError(f"frame count drifted to {got_frames}; concat would shift captions")
    if abs(got_duration - reference_duration) > 0.002:
        raise RuntimeError(
            f"duration drifted by {report['duration_delta_ms']} ms; captions would shift"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
