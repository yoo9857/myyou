"""Split the trailer into separate stems so the balance is the editor's to set.

Everything has been baked into one mix, which means every complaint about a level - the music
is too loud, the narration is too loud - costs a re-render and a round trip. Split, the same
adjustments are a fader in CapCut.

Four files come out, all the same length, all starting at zero:

    picture      the cut with no sound at all
    film         the film's own audio, unducked
    narration    the recorded lines in their trailer positions
    music        the bed, level and fades already shaped

build_capcut_project.py lays the last three on their own audio tracks, so nothing is mixed
until it is exported.

    python devil/export_trailer_stems.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Must be the cut *before* the narration was mixed in. Pointing this at the narrated
    # version put the voice inside the film stem, so REVIEW_VOICE beside it played every line
    # twice - which is the whole reason the stems exist.
    parser.add_argument("--source", default="devil_trailer_cut.mp4",
                        help="Cut carrying the film audio only, before narration or end card.")
    parser.add_argument("--final", default="devil_trailer_final.mp4",
                        help="Cut with the end card, for the total length.")
    parser.add_argument("--music", type=Path, default=None)
    args = parser.parse_args()

    import pipeline

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    package = ROOT / "output" / "capcut_import"
    stems = package / "trailer_stems"
    stems.mkdir(parents=True, exist_ok=True)
    body = ROOT / "output" / args.source
    final = ROOT / "output" / args.final
    if not body.exists() or not final.exists():
        raise SystemExit("예고편 컷이 없습니다. run_trailer.py를 먼저 돌리십시오.")
    total = duration(final)

    picture = stems / "trailer_picture.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(final),
                    "-an", "-c:v", "copy", "-movflags", "+faststart", "-y", str(picture)],
                   check=True)

    # The film stem comes off the pre-endcard cut and is padded to the full length, so every
    # stem starts at zero and ends together - dropping one into CapCut needs no nudging.
    film = stems / "trailer_film.m4a"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(body),
                    "-vn", "-af", f"aresample=48000,apad,atrim=duration={total:.3f}",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-y", str(film)], check=True)

    plan_srt = pipeline.parse_srt(package / "trailer_narration.srt")
    script = json.loads((ROOT / "output" / "narration_script_v5.json").read_text(encoding="utf-8"))
    by_text = {i["tts_en"]: int(i["order"]) for i in script["items"] if i["use_narration"]}
    audio_dir = package / "narration_audio"
    inputs, filters, labels = [], [], []
    for index, cue in enumerate(plan_srt):
        order = by_text.get(cue.text.strip())
        clip = audio_dir / f"clip_{order:03d}.mp3" if order else None
        if not clip or not clip.exists():
            continue
        inputs += ["-i", str(clip)]
        filters.append(f"[{len(labels)}:a]aresample=48000,"
                       f"adelay={int(round(cue.start * 1000))}:all=1[v{len(labels)}]")
        labels.append(f"[v{len(labels)}]")
    if not labels:
        raise SystemExit("해설 음성을 찾지 못했습니다.")
    narration = stems / "trailer_narration.m4a"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex",
         ";".join(filters) + ";" + "".join(labels) +
         f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
         f"apad,atrim=duration={total:.3f}[a]",
         "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-y", str(narration)], check=True)

    made = [picture, film, narration]
    if args.music and args.music.exists():
        track = duration(args.music)
        loops = 0 if total <= track else int(total // max(track, 1.0)) + 1
        music = stems / "trailer_music.m4a"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-stream_loop", str(loops), "-i", str(args.music), "-vn",
             "-af", f"atrim=duration={total:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                    f"afade=t=in:st=0:d=2.0,afade=t=out:st={total - 3.0:.3f}:d=3.0",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-y", str(music)], check=True)
        made.append(music)

    print(f"  길이 {total/60:.2f}분, 모두 0초에서 시작")
    for path in made:
        print(f"    {path.name:26} {path.stat().st_size/1048576:6.1f} MB")
    print(f"  {stems.relative_to(ROOT.parent)}")
    print("  CapCut에서 각 트랙 볼륨을 직접 조절하십시오. 스템 자체에는 레벨을 넣지 않았습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
