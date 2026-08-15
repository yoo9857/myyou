"""Build a trailer cut end to end, so asking for one produces all of it.

A trailer was asked for once and delivered in pieces: the cut, then the narration, then the
character captions, then the channel's caption design, then the watermark, then the CapCut
project, each only after being named. All of it is one thing. This runs the whole chain.

    python scripts/run_trailer.py devil/config.json --music "cleared.mp3"
    python scripts/run_trailer.py devil/config.json --from captions

Nothing here calls a paid API. The narration reuses lines already recorded for the long
review, so a trailer can be rebuilt as often as it needs to be.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--music", type=Path, default=None)
    parser.add_argument("--watermark", type=Path,
                        default=CODE_ROOT / "assets" / "Vera_Lindqvist_icon_05.png")
    parser.add_argument("--name", default=None, help="CapCut draft name.")
    parser.add_argument("--from", dest="start", default=None,
                        help="Resume at a step: cut, narration, dialogue, finish, captions, capcut, script")
    args = parser.parse_args()

    config_path = args.config.resolve()
    root = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    name = args.name or (root.name.upper() + "_TRAILER")
    stem = f"{root.name}_trailer"
    py = [sys.executable]

    steps = [
        ("cut", "예고편 컷", py + [str(root / "build_trailer_cut.py"), "--render"]),
        ("narration", "해설 배치 + 더킹",
         py + [str(root / "add_trailer_narration.py"), "--out", f"{stem}_v2.mp4"]),
        ("dialogue", "영화 대사 자막",
         py + [str(root / "build_trailer_dialogue_srt.py")]),
        ("finish", "엔딩 카드 + 음악",
         py + [str(root / "finish_trailer.py"), "--source", f"{stem}_v2.mp4",
               "--out", f"{stem}_final.mp4"]
         + (["--music", str(args.music)] if args.music else [])),
        ("captions", "자막 디자인 + 워터마크",
         py + [str(CODE_ROOT / "scripts" / "build_caption_design.py"), str(config_path),
               "--video", f"{stem}_final.mp4",
               "--narration-srt", "trailer_narration.srt",
               "--dialogue-srt", "trailer_movie_captions.srt",
               "--ass", "trailer_captions.ass",
               "--watermark", str(args.watermark)]),
        ("capcut", "CapCut 프로젝트",
         py + [str(CODE_ROOT / "scripts" / "build_capcut_project.py"), str(config_path),
               "--name", name, "--video", f"{stem}_final.mp4",
               "--narration-srt", "trailer_narration.srt",
               "--dialogue-srt", "trailer_movie_captions.srt"]),
    ]

    if not args.music:
        print("  경고: 음악 없이 진행합니다. 저작권이 확인된 파일을 --music으로 주십시오.\n")

    started = args.start is None
    env = {**os.environ, "MOVIE_REVIEW_ROOT": str(root), "PYTHONIOENCODING": "utf-8"}
    for key, title, command in steps:
        if key == args.start:
            started = True
        if not started:
            continue
        print(f"\n[{key}] {title}")
        result = subprocess.run(command, cwd=CODE_ROOT, env=env)
        if result.returncode != 0:
            # CapCut holds its drafts open and refuses to be written under; that is the one
            # failure worth naming, because the fix is to close it rather than to debug.
            if key == "capcut":
                print("  CapCut을 닫고 --from capcut 으로 다시 실행하십시오.")
            return result.returncode

    final = root / "output" / f"{stem}_final_captioned.mp4"
    print(f"\n  완성본: {final.relative_to(root.parent) if final.exists() else '(없음)'}")
    print(f"  CapCut: {name}")
    print("  한글 대본이 필요하면 예고편 자막 두 트랙을 번역해 MD로 내보내면 됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
