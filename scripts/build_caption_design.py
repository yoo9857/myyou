"""Style the two caption tracks the way the previous reviews looked, and burn them in.

The pipeline delivers plain SRT for CapCut, which carries no styling, so the mp4 that comes
out of a render is unstyled - a different look from the finished Constantine review, where
narration sat in warm yellow above the film's own dialogue in white.

The proportions come from that project's ASS: authored against a 384x288 script resolution
at sizes 21 and 18, which is 7.3 and 6.3 percent of frame height. Those percentages are what
carries over, so the same design lands correctly at 1080p instead of being scaled by libass
from a resolution nothing here uses.

    python scripts/build_caption_design.py devil/config.json          styled ASS + burned mp4
    python scripts/build_caption_design.py devil/config.json --ass-only

The burned file sits beside the master rather than replacing it: CapCut still imports the
clean master plus the SRTs, and the burned copy is the one that can be watched as it is.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

REFERENCE_HEIGHT = 288.0
NARRATION_SIZE = 21.0 / REFERENCE_HEIGHT      # warm yellow, above the dialogue line
DIALOGUE_SIZE = 18.0 / REFERENCE_HEIGHT
NARRATION_MARGIN = 48.0 / REFERENCE_HEIGHT
DIALOGUE_MARGIN = 18.0 / REFERENCE_HEIGHT

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_colour(rgb, alpha=1.0):
    """CapCut stores colour as 0-1 RGB; ASS wants &HAABBGGRR with AA as transparency."""
    red, green, blue = (max(0, min(255, round(c * 255))) for c in (rgb + [0, 0, 0])[:3])
    return f"&H{round((1 - alpha) * 255):02X}{blue:02X}{green:02X}{red:02X}"


def style_line(name, spec, frame_height, picture_height, side, fallback_font, fallback_ratio):
    """Turn one saved CapCut caption style into an ASS style line.

    CapCut's font_size is a percentage of frame height and its vertical transform runs from
    the centre, so both resolve against the picture rather than the frame. A background alpha
    above zero means a box, which in ASS is BorderStyle 3 rather than an outline.
    """
    material = spec.get("material", {}) if spec else {}
    style = spec.get("style", {}) if spec else {}
    font = material.get("font_name") or fallback_font
    ratio = float(material.get("font_size", fallback_ratio * 100)) / 100
    size = max(12, round(ratio * picture_height))
    colour = style.get("fill", {}).get("content", {}).get("solid", {}).get("color", [1, 1, 1])
    alpha = float(material.get("background_alpha", 0.0) or 0.0)
    boxed = alpha > 0.01
    back = ass_colour([0, 0, 0], alpha) if boxed else "&H78000000"
    border_style = 3 if boxed else 1
    outline = 0.0 if boxed else round(0.0055 * picture_height, 1)
    shadow = 0.0 if boxed else round(0.0028 * picture_height, 1)
    # CapCut centres the text at transform_y, measured from the middle of the *frame* as a
    # fraction of half its height, negative downward. ASS MarginV is the gap from the frame
    # bottom to the bottom of the text. Measuring against the picture instead of the frame put
    # the narration on the edge of the image and the dialogue into the letterbox bar.
    y = float(spec.get("transform_y", -0.7)) if spec else -0.7
    margin = max(8, round(frame_height / 2 * (1 + y) - size / 2))
    return (f"Style: {name},{font},{size},{ass_colour(colour)},&H000000FF,&H000A0805,{back},"
            f"0,0,0,0,100,100,0,0,{border_style},{outline},{shadow},2,{side},{side},{margin},1")


CROP = re.compile(r"crop=(\d+):(\d+):(\d+):(\d+)")


def pipeline_picture_area(video: Path, fraction: float) -> tuple[int, int] | None:
    """Measure the lit picture inside the frame, sampled where the shot is not dark.

    cropdetect reports the bright region, so one dark frame reads as a tiny picture. The
    caller takes the largest of several samples for the same reason the delivery gate does.
    """
    total = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)], text=True).strip())
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{total * fraction:.2f}", "-t", "2",
         "-i", str(video), "-vf", "cropdetect=24:2:0", "-f", "null", "-"],
        capture_output=True, text=True)
    found = CROP.findall(result.stderr)
    return (int(found[-1][0]), int(found[-1][1])) if found else None


STAMP = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})")


def read_srt(path):
    """Read cues keeping their line breaks.

    pipeline.parse_srt joins a cue's lines with a space, which is right nearly everywhere and
    wrong here: a break between two speakers is the thing that says a second person started
    talking, and joining it put both halves on one line.
    """
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        rows = [r for r in block.splitlines() if r.strip()]
        if len(rows) < 3:
            continue
        found = STAMP.search(rows[1])
        if not found:
            continue
        g = [int(x) for x in found.groups()]
        cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                     g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                     "\n".join(rows[2:])))
    return cues


def stamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{secs:05.2f}"


def escape(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("{", "(").replace("}", ")").replace("\n", r"\N").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--ass-only", action="store_true")
    parser.add_argument("--narration-font", default="Cormorant Garamond")
    parser.add_argument("--dialogue-font", default="Pretendard Medium")
    parser.add_argument("--caption-style", default=str(
        CODE_ROOT / "assets" / "subtitle-style" / "channel-captions-v6.json"),
        help="Design captured from an approved CapCut project; one place the look lives.")
    parser.add_argument("--watermark", default=None,
                        help="PNG laid top-right, the way the channel's projects place it.")
    # A trailer cut has its own master and its own caption track, so both are nameable.
    parser.add_argument("--video", default=None, help="Video to burn into, under output/.")
    parser.add_argument("--narration-srt", default="narration.srt")
    parser.add_argument("--dialogue-srt", default="movie_captions.srt")
    parser.add_argument("--ass", default="captions_styled.ass")
    args = parser.parse_args()

    import pipeline

    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent
    package = root / "output" / "capcut_import"
    width = int(config.get("render_width", 1920))
    height = int(config.get("render_height", 1080))
    master = root / "output" / (args.video or str(config.get("output_video", "rough_cut.mp4")))

    # Sizes and margins are proportions of the picture, not of the frame. This source is
    # 2.39:1 inside a 16:9 render, so 138 pixels top and bottom are black bars - a margin
    # measured from the frame edge put the film's own dialogue into the bar below the image.
    picture_height, bar = height, 0
    if master.exists():
        area = None
        for fraction in (0.2, 0.4, 0.6, 0.8):
            found = pipeline_picture_area(master, fraction)
            if found and (area is None or found[1] > area[1]):
                area = found
        if area:
            picture_height = area[1]
            bar = max(0, (height - picture_height) // 2)

    tracks = [("Narration", package / args.narration_srt),
              ("Dialogue", package / args.dialogue_srt)]
    lines = []
    for style, path in tracks:
        if not path.exists():
            # A cut may legitimately have only one of the two tracks.
            print(f"  건너뜀: {path.name} 없음")
            continue
        for start, end, text in read_srt(path):
            if text.strip():
                lines.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},"
                             f"{style},,0,0,0,,{escape(text)}")
    lines.sort(key=lambda entry: entry.split(",")[1])

    design = {}
    if args.caption_style and Path(args.caption_style).exists():
        design = json.loads(Path(args.caption_style).read_text(encoding="utf-8")).get("tracks", {})
    side = round(32.0 / 384.0 * width)
    header = HEADER.format(
        width=width, height=height,
        styles="\n".join([
            style_line("Narration", design.get("REVIEW_NARRATION"), height, picture_height,
                       side, args.narration_font, NARRATION_SIZE),
            style_line("Dialogue", design.get("MOVIE_DIALOGUE"), height, picture_height,
                       side, args.dialogue_font, DIALOGUE_SIZE),
        ]))
    ass_path = package / args.ass
    ass_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"  스타일 자막 {len(lines)}줄 -> {ass_path.relative_to(root)}")
    for label, name in (("REVIEW_NARRATION", "해설"), ("MOVIE_DIALOGUE", "대사")):
        spec = design.get(label)
        if spec:
            material = spec["material"]
            box = float(material.get("background_alpha", 0) or 0)
            print(f"  {name} {material['font_name']} "
                  f"{round(float(material['font_size']) / 100 * picture_height)}px"
                  + (f", 배경 {box:.0%}" if box > 0.01 else ""))
        else:
            print(f"  {name} 저장된 디자인 없음 — 기본값 사용")
    print(f"  그림 {width}x{picture_height} (레터박스 {bar}px)")
    if args.ass_only:
        return 0

    if not master.exists():
        raise SystemExit(f"최종본이 없습니다: {master}")
    burned = master.with_name(master.stem + "_captioned.mp4")
    # Relative name with cwd, because a Windows drive letter's colon is read as a filter
    # option separator. Audio is copied: this pass is picture only.
    mark = Path(args.watermark).resolve() if args.watermark else None
    if mark and mark.exists():
        # Same corner and size the channel's CapCut projects use: scale 0.0983 of a canvas-fitted
        # 1024 square, centred at 0.927/0.868 of the half-frame from the middle.
        side_px = round(0.0983 * height)
        x = round(width / 2 + 0.9267 * (width / 2) - side_px / 2)
        y = round(height / 2 - 0.8682 * (height / 2) - side_px / 2)
        chain = (f"[1:v]scale={side_px}:{side_px}[wm];"
                 f"[0:v][wm]overlay={x}:{y}[marked];[marked]subtitles={ass_path.name}[v]")
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(master),
                   "-i", str(mark), "-filter_complex", chain, "-map", "[v]", "-map", "0:a?"]
    else:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(master),
                   "-vf", f"subtitles={ass_path.name}"]
    subprocess.run(
        [*command,
         "-c:v", "libx264", "-preset", str(config.get("render_preset", "medium")),
         "-crf", str(config.get("render_crf", 19)), "-c:a", "copy",
         "-movflags", "+faststart", "-y", str(burned)],
        check=True, cwd=package,
    )
    print(f"  자막 입힘 -> {burned.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
