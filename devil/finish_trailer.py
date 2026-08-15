"""Put an end card and music on the trailer cut, then balance the whole thing.

Three things the cut is missing to be finished: somewhere to send the viewer, music under the
picture, and levels that hold together once both are added. The end card is drawn rather than
filmed, so it carries nothing from the source; the music comes from a file named on the
command line, which is how it gets swapped without touching anything else.

    python devil/finish_trailer.py --music "The Final Resolve.mp3"
    python devil/finish_trailer.py --music path/to/cleared.mp3 --out devil_trailer_v4.mp4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

CARD_SECONDS = 9.0
CARD_FADE = 1.0
MUSIC_UNDER = 0.22       # under narration and film, felt rather than heard
MUSIC_CARD = 0.62        # the card has nothing else on it
MUSIC_SOURCE_START = 8.0


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="devil_trailer_v2.mp4")
    parser.add_argument("--out", default="devil_trailer_final.mp4")
    parser.add_argument("--music", type=Path, default=None)
    parser.add_argument("--title", default="THE DEVIL ALL THE TIME")
    parser.add_argument("--cast", default="TOM HOLLAND   ROBERT PATTINSON   SEBASTIAN STAN")
    parser.add_argument("--call", default="Watch it, then decide who was right")
    args = parser.parse_args()

    import pipeline

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    source = ROOT / "output" / args.source
    if not source.exists():
        raise SystemExit(f"예고편이 없습니다: {source}")
    work = ROOT / "work" / "trailer_finish"
    work.mkdir(parents=True, exist_ok=True)
    width = int(config.get("render_width", 1920))
    height = int(config.get("render_height", 1080))
    fps = int(config.get("render_fps", 24))
    body = duration(source)

    # Sizes as fractions of frame height so the card scales with the render rather than being
    # tied to 1080. Drawn on black: nothing here comes from the film.
    font = "C\\:/Windows/Fonts/malgunbd.ttf"
    layers = [
        (args.title, round(height * 0.062), int(height * 0.40), "0xF5F0E6"),
        (args.cast, round(height * 0.026), int(height * 0.52), "0xAFE8FF"),
        (args.call, round(height * 0.030), int(height * 0.63), "0xC8C8C8"),
    ]
    draw = ",".join(
        f"drawtext=fontfile='{font}':text='{text}':fontcolor={colour}:fontsize={size}:"
        f"x=(w-text_w)/2:y={y}:alpha='min(1,max(0,(t-{0.6 + i * 0.35:.2f})/0.7))'"
        for i, (text, size, y, colour) in enumerate(layers))
    card = work / "endcard.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", f"{CARD_SECONDS:.3f}",
         "-vf", f"{draw},fade=t=out:st={CARD_SECONDS - CARD_FADE:.2f}:d={CARD_FADE:.2f},"
                "format=yuv420p",
         "-c:v", "libx264", "-preset", str(config.get("render_preset", "medium")),
         "-crf", str(config.get("render_crf", 19)),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-y", str(card)],
        check=True)

    concat = work / "concat.txt"
    concat.write_text(f"file '{source.as_posix()}'\nfile '{card.as_posix()}'\n", encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(concat), "-c", "copy", "-y", str(joined)],
                   check=True)
    total = duration(joined)
    out = ROOT / "output" / args.out

    if args.music and args.music.exists():
        # A 107-second track cannot cover a six-minute cut, so it loops. The seam is smoothed
        # by fading each pass out and the next one in over the overlap rather than butting
        # them together, which would click on every repeat.
        track = duration(args.music) - MUSIC_SOURCE_START
        loops = 0 if total <= track else int(total // max(track, 1.0)) + 1
        # Low under the trailer, up on the card where nothing competes with it.
        rise = body - 0.5
        gain = (f"{MUSIC_UNDER:.3f}+{MUSIC_CARD - MUSIC_UNDER:.3f}"
                f"*min(1,max(0,(t-{rise:.3f})/1.2))")
        stem = work / "trailer_music.m4a"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-stream_loop", str(loops), "-i", str(args.music), "-vn",
             "-af", f"atrim=start={MUSIC_SOURCE_START:.3f}:duration={total:.3f},"
                    "asetpts=PTS-STARTPTS,aresample=48000,"
                    f"volume=eval=frame:volume='{gain}',"
                    f"afade=t=in:st=0:d=2.0,afade=t=out:st={total - 2.5:.3f}:d=2.5",
             "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k", "-y", str(stem)],
            check=True)
        limiter = float(config.get("audio_limiter", 0.891251))
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(joined), "-i", str(stem),
             "-filter_complex",
             f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
             f"alimiter=limit={limiter:.6f}:level=false[a]",
             "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", "-y", str(out)], check=True)
    else:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(joined),
                        "-c", "copy", "-movflags", "+faststart", "-y", str(out)], check=True)

    pipeline.master_audio(config, out)
    print(f"  엔딩 카드 {CARD_SECONDS:.0f}초  '{args.call}'")
    print(f"  음악 {args.music.name if args.music else '없음'}"
          + (f"  본편 {MUSIC_UNDER} -> 카드 {MUSIC_CARD}" if args.music else ""))
    print(f"  완료: {out.relative_to(ROOT.parent)}  {duration(out)/60:.2f}분")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
