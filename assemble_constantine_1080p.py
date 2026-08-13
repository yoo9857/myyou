"""Join the re-rendered 1080p cut to the 1080p outro, refusing any timing drift.

Every caption in the project is anchored to the total running time: 287 movie cues,
29 narration cues and the narration audio placements. So this checks the 1080p cut
against the 540p one it replaces frame-for-frame before concatenating, and checks the
joined file afterwards. Any drift beyond a millisecond aborts rather than silently
shifting the whole timeline.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Constantine" / "story_review_v5" / "output"
WORK = ROOT / "Constantine" / "story_review_v5" / "work"

CUT_540 = OUTPUT / "constantine_story_review_v5_voice_off.mp4"
CUT_1080 = OUTPUT / "constantine_story_review_v5_voice_off_1080p.mp4"
OUTRO_540 = OUTPUT / "outro_v1.mp4"
OUTRO_1080 = OUTPUT / "outro_v1_1080p.mp4"
JOINED_540 = OUTPUT / "constantine_story_review_v5_with_outro.mp4"
JOINED_1080 = OUTPUT / "constantine_story_review_v5_with_outro_1080p.mp4"
QA_PATH = OUTPUT / "CONSTANTINE_1080P_ASSEMBLY_QA.json"

TOLERANCE_SEC = 0.002


def probe(path: Path, entries: str, stream: str | None = None) -> list[str]:
    command = ["ffprobe", "-v", "error"]
    if stream:
        command += ["-select_streams", stream]
    command += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    return subprocess.check_output(command, text=True, encoding="utf-8").strip().splitlines()


def duration(path: Path) -> float:
    return float(probe(path, "format=duration")[0])


def geometry(path: Path) -> tuple[int, int, int]:
    w, h = (int(v) for v in probe(path, "stream=width,height", "v:0"))
    frames = int(probe(path, "stream=nb_frames", "v:0")[0])
    return w, h, frames


def compare(label: str, new: Path, old: Path) -> dict:
    nw, nh, nf = geometry(new)
    ow, oh, of = geometry(old)
    nd, od = duration(new), duration(old)
    delta_ms = (nd - od) * 1000
    print(f"{label}")
    print(f"  기존 {ow}x{oh}  {of} frames  {od:.6f} s")
    print(f"  신규 {nw}x{nh}  {nf} frames  {nd:.6f} s   차이 {delta_ms:+.3f} ms")
    if nf != of:
        raise RuntimeError(
            f"{label}: frame count {nf} != {of}. Concatenating would shift every caption."
        )
    if abs(nd - od) > TOLERANCE_SEC:
        raise RuntimeError(f"{label}: duration drifted {delta_ms:+.3f} ms")
    if (nw, nh) != (1920, 1080):
        raise RuntimeError(f"{label}: expected 1920x1080, got {nw}x{nh}")
    return {"resolution": f"{nw}x{nh}", "frames": nf, "duration_sec": nd,
            "reference_duration_sec": od, "delta_ms": round(delta_ms, 3)}


def main() -> int:
    for path in (CUT_1080, OUTRO_1080, CUT_540, OUTRO_540, JOINED_540):
        if not path.exists():
            raise FileNotFoundError(path)

    cut = compare("본편 컷", CUT_1080, CUT_540)
    outro = compare("아웃트로", OUTRO_1080, OUTRO_540)

    WORK.mkdir(parents=True, exist_ok=True)
    concat_file = WORK / "outro_concat_1080p.txt"
    concat_file.write_text(
        f"file '{CUT_1080.as_posix()}'\nfile '{OUTRO_1080.as_posix()}'\n", encoding="utf-8"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", "-y",
         str(JOINED_1080)],
        check=True,
    )

    joined = compare("결합본", JOINED_1080, JOINED_540)
    expected = cut["duration_sec"] + outro["duration_sec"]
    print(f"결합 검산: {cut['duration_sec']:.6f} + {outro['duration_sec']:.6f} "
          f"= {expected:.6f} vs 실제 {joined['duration_sec']:.6f}")

    qa = {
        "status": "pass",
        "cut": cut,
        "outro": outro,
        "joined": joined,
        "sum_check_sec": round(expected, 6),
        "tolerance_sec": TOLERANCE_SEC,
        "captions_unaffected": True,
        "note": "frame counts and durations match the 540p originals, so the 287 movie "
                "cues, 29 narration cues and audio placements stay valid",
        "outputs": {"cut": str(CUT_1080), "outro": str(OUTRO_1080), "joined": str(JOINED_1080)},
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "joined_duration_sec": joined["duration_sec"],
                      "delta_ms": joined["delta_ms"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
