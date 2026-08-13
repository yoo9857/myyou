"""Cut a 60-second probe so the rights holder's Content ID policy can be read first.

This is gate zero. A finished 25-minute review was blocked in every country because
Warner Bros. had set the film's asset to block, and the claim covered the whole runtime.
No edit fixes that — Content ID matches a few seconds as readily as an hour — so the
policy has to be known before production starts, not after.

The probe is deliberately dull to make: three short samples from different parts of the
film, joined. Spreading them means a scene that happens to be quiet or black does not
give a false all-clear.

Usage:
    python scripts/copyright_probe.py "<source film>" [--out probe.mp4] [--at 0.25 0.5 0.75]

Then upload the result as **private**, wait a few minutes, and read
Studio -> the video -> restrictions -> claim details:

    no claim                  -> proceed
    claim, monetise or track  -> proceed; revenue may go to the holder
    claim, block              -> pick another film, do not start production

Read the claim type too: "audiovisual" means picture and sound both matched, so muting
the film will not clear it either.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="probe.mp4")
    ap.add_argument("--at", nargs="*", type=float, default=[0.25, 0.5, 0.75],
                    help="fractions of the runtime to sample from")
    # Total stays under 60 s so the same clip also answers the Shorts question: a Short
    # over one minute is blocked by any claim regardless of policy, while a sub-minute one
    # follows the policy.
    ap.add_argument("--total", type=float, default=57.0, help="total probe seconds, under 60")
    args = ap.parse_args()
    args.each = args.total / max(1, len(args.at))

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"not found: {source}")
    total = duration(source)
    out = Path(args.out)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        parts = []
        for index, fraction in enumerate(args.at):
            start = max(0.0, min(total - args.each, total * fraction))
            part = tmpdir / f"part_{index}.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-hwaccel", "cuda",
                 "-ss", f"{start:.3f}", "-t", f"{args.each:.3f}", "-i", str(source),
                 "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                 "-y", str(part)],
                check=True,
            )
            parts.append((start, part))
            print(f"  {start/60:5.1f}분 지점에서 {args.each:.0f}초", flush=True)

        listing = tmpdir / "concat.txt"
        listing.write_text(
            "\n".join(f"file '{p.as_posix()}'" for _, p in parts) + "\n", encoding="utf-8")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", "-movflags", "+faststart", "-y", str(out)],
            check=True,
        )

    got = duration(out)
    report = {
        "probe": str(out),
        "source": str(source),
        "source_duration_min": round(total / 60, 1),
        "probe_duration_sec": round(got, 2),
        "sampled_at_minutes": [round(s / 60, 1) for s, _ in parts],
        "next_step": "Upload as PRIVATE, then read Studio -> restrictions -> claim details. "
                     "Policy 'block' means pick another film.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if got > 60.5:
        print("\n주의: 60초를 넘었습니다. 숏츠 정책 확인에는 60초 미만이어야 합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
