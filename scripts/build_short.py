"""Cut a vertical Short out of a finished review.

Takes a window from the 16:9 master and rebuilds it as 1080x1920: the film sits as a
band across the middle at full width, a blurred blow-up of the same picture fills the
space above and below, and the captions are burned in because Shorts carry no separate
caption track.

Keep the window under 60 seconds. A Short of 1-3 minutes with any active Content ID
claim is blocked regardless of the rights holder's policy, while a sub-minute Short
follows the policy instead — so the shorter form is the only one where a permissive
rights holder still leaves the video playable.

Usage:
    python scripts/build_short.py <config.json>
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920


def srt_blocks(path: Path) -> list[tuple[float, float, str]]:
    pattern = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})")
    out = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        m = pattern.search(lines[1])
        if not m:
            continue
        g = m.groups()
        start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        out.append((start, end, "\n".join(lines[2:])))
    return out


def stamp(value: float) -> str:
    value = max(0.0, value)
    h, rest = divmod(value, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def ass_time(value: float) -> str:
    value = max(0.0, value)
    h, rest = divmod(value, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass(dst: Path, tracks: list[dict], start: float, end: float) -> dict[str, int]:
    """Burn-in subtitles as ASS, not SRT + force_style.

    An SRT carries no script resolution, so libass falls back to 384x288 and any MarginV
    above ~288 pushes the text off a 1080x1920 frame entirely — the captions render, just
    outside the picture. Declaring PlayResX/PlayResY makes every size and margin below a
    plain pixel value.
    """
    styles, events, counts = [], [], {}
    for track in tracks:
        styles.append(
            f"Style: {track['name']},{track['font_name']},{track['size']},"
            f"{track['colour']},{track['colour']},&H00000000,&H80000000,"
            f"{1 if track.get('bold') else 0},{1 if track.get('italic') else 0},0,0,"
            f"100,100,{track.get('spacing', 0)},0,1,{track.get('outline', 4)},"
            f"{track.get('shadow', 2)},2,80,80,{track['margin_v']},1"
        )
        kept = 0
        for a, b, text in srt_blocks(track["srt"]):
            if b <= start or a >= end:
                continue
            body = text.replace("\n", "\\N").replace("{", "(").replace("}", ")")
            events.append(
                f"Dialogue: 0,{ass_time(max(a, start) - start)},"
                f"{ass_time(min(b, end) - start)},{track['name']},,0,0,0,,{body}"
            )
            kept += 1
        counts[track["name"]] = kept

    dst.write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\nYCbCr Matrix: TV.709\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
        "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        + "\n".join(styles) + "\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        + "\n".join(events) + "\n",
        encoding="utf-8",
    )
    return counts


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    cfg_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    root = (cfg_path.parent / cfg.get("root", ".")).resolve()

    source = root / cfg["source_video"]
    start, end = float(cfg["start_sec"]), float(cfg["end_sec"])
    duration = end - start
    if duration > 60:
        raise SystemExit(f"{duration:.1f}s is over the 60 s line where policy stops applying")

    work = root / cfg.get("work_dir", "work/shorts")
    work.mkdir(parents=True, exist_ok=True)
    out_path = root / cfg["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Relative paths only: a Windows drive letter's colon breaks the filter parser.
    fonts = work / "fonts"
    fonts.mkdir(exist_ok=True)
    for key in ("dialogue_font", "narration_font"):
        src = Path(cfg[key])
        if src.exists():
            shutil.copy2(src, fonts / src.name)

    counts = write_ass(work / "subs.ass", [
        {"name": "DLG", "srt": root / cfg["movie_caption_srt"],
         "font_name": cfg["dialogue_font_name"], "size": cfg.get("dialogue_size", 52),
         "colour": "&H00FFFFFF", "margin_v": cfg.get("dialogue_margin", 210),
         "outline": 4, "shadow": 2},
        {"name": "NAR", "srt": root / cfg["narration_srt"],
         "font_name": cfg["narration_font_name"], "size": cfg.get("narration_size", 62),
         "colour": "&H00D2EBF6", "margin_v": cfg.get("narration_margin", 470),
         "outline": 4, "shadow": 2, "italic": True, "spacing": 1},
    ], start, end)
    print(f"자막: 영화 대사 {counts['DLG']}개, 나레이션 {counts['NAR']}개")

    # A 2.39:1 picture at full width is only 452 px tall in a 1920 frame — under a quarter
    # of the screen. Trading side crop for height puts faces at a size that reads on a
    # phone; band_height is that trade, and the crop width follows from it.
    crop_w, crop_h, crop_x, crop_y = (int(v) for v in
                                      cfg.get("picture_crop", "1920:804:0:138").split(":"))
    band_h = int(cfg.get("band_height", 1080))
    band_h -= band_h % 2
    keep_w = min(crop_w, round(crop_h * W / band_h))
    keep_w -= keep_w % 2
    offset = cfg.get("crop_bias", 0.5)  # 0 = keep the left edge, 1 = keep the right
    keep_x = round((crop_w - keep_w) * float(offset))
    keep_x -= keep_x % 2
    print(f"밴드 {band_h}px (화면의 {band_h/H*100:.0f}%), "
          f"원본 가로의 {keep_w/crop_w*100:.0f}% 유지")

    graph = (
        f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},split=2[fg][bgsrc];"
        f"[bgsrc]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=28:2,eq=brightness=-0.16[bg];"
        f"[fg]crop={keep_w}:{crop_h}:{keep_x}:0,scale={W}:{band_h}[band];"
        f"[bg][band]overlay=0:(H-h)/2[stacked];"
        f"[stacked]ass=subs.ass:fontsdir=fonts[v]"
    )

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source),
        "-filter_complex", graph, "-map", "[v]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", str(cfg.get("fps", 24)),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-y", str(out_path),
    ]
    print(subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, check=True, cwd=work)

    dims = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out_path)],
        text=True).strip()
    got = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out_path)], text=True).strip())
    report = {
        "output": str(out_path),
        "resolution": dims,
        "duration_sec": round(got, 3),
        "under_60s": got < 60,
        "captions_burned": counts,
        "source_window": [start, end],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
