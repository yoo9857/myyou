"""Mechanical delivery gates for a movie-review project.

Every check here exists because it was missed by hand at least once. The existing
story/narration gates are prose judgements; these are numbers, so they can be run.

Usage:
    python scripts/delivery_gates.py Constantine/story_review_v5/delivery_gates.json

The config names the files; the thresholds live here so every project is held to the
same bar. Exit code is 1 if any gate fails, so this can sit in front of a publish step.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

# ---- thresholds -------------------------------------------------------------
MIN_WIDTH, MIN_HEIGHT = 1920, 1080
MAX_CRF = 20
BANNED_PRESETS = {"ultrafast", "superfast", "veryfast"}
DURATION_TOLERANCE_SEC = 0.002
# Compare the narration against the film's own DIALOGUE, not its overall level: ambience
# and effects drag the average down and hide a narrator that is far too loud.
# A reviewer should sit at or slightly above the actors — below and the narration gets
# buried, far above and it shouts over the film.
DIALOGUE_BALANCE_RANGE_DB = (0.0, 4.0)
MIN_DUCK_LEAD_DB = 6.0
PROGRAMME_LUFS_RANGE = (-20.0, -13.0)
MAX_TRUE_PEAK_DBTP = -1.0
OPTICAL_SIZE_TOLERANCE = 0.05  # 5% on rendered x-height
LOUDNORM = "loudnorm=I=-14:TP=-1:LRA=11:print_format=json"


class Gates:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def check(self, group: str, name: str, ok: bool, detail: str) -> bool:
        self.rows.append((group, name, ok, detail))
        return ok

    def skip(self, group: str, name: str, why: str) -> None:
        self.rows.append((group, name, None, f"건너뜀 — {why}"))

    def report(self) -> int:
        width = max(len(r[1]) for r in self.rows) + 2
        current = None
        failed = 0
        for group, name, ok, detail in self.rows:
            if group != current:
                print(f"\n[{group}]")
                current = group
            mark = "  --" if ok is None else ("  OK" if ok else "FAIL")
            if ok is False:
                failed += 1
            print(f"  {mark}  {name:<{width}} {detail}")
        total = sum(1 for r in self.rows if r[2] is not None)
        passed = sum(1 for r in self.rows if r[2] is True)
        skipped = sum(1 for r in self.rows if r[2] is None)
        print(f"\n통과 {passed}/{total}, 실패 {failed}, 건너뜀 {skipped}")
        return 1 if failed else 0


def sh(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def probe(path: Path, entries: str, stream: str | None = None) -> list[str]:
    command = ["ffprobe", "-v", "error"]
    if stream:
        command += ["-select_streams", stream]
    command += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    return sh(command).splitlines()


def loudness(path: Path, window: tuple[float, float] | None = None,
             prefilter: str = "") -> tuple[float, float] | None:
    command = ["ffmpeg", "-v", "info"]
    if window:
        command += ["-ss", f"{window[0]:.3f}", "-t", f"{window[1]:.3f}"]
    chain = f"{prefilter}," if prefilter else ""
    command += ["-i", str(path), "-map", "0:a:0", "-af", chain + LOUDNORM, "-f", "null", "-"]
    err = subprocess.run(command, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    try:
        blob = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    except ValueError:
        return None
    value = float(blob["input_i"])
    if not math.isfinite(value) or value < -70:
        return None
    return value, float(blob["input_tp"])


def picture_area(path: Path, at: float) -> tuple[int, int] | None:
    err = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", f"{at:.2f}", "-t", "2", "-i", str(path),
         "-vf", "cropdetect=round=2", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    found = re.findall(r"crop=(\d+):(\d+):", err)
    if not found:
        return None
    best = statistics.mode([f"{w}x{h}" for w, h in found])
    w, h = best.split("x")
    return int(w), int(h)


def srt_windows(path: Path) -> list[tuple[float, float]]:
    pattern = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})")
    out = []
    for g in pattern.findall(path.read_text(encoding="utf-8-sig")):
        a = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        b = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        out.append((a, b))
    return out


def font_family(path: Path) -> str | None:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    try:
        font = TTFont(str(path), fontNumber=0)
        for record in font["name"].names:
            if record.nameID == 1:
                return record.toUnicode()
    except Exception:
        return None
    return None


def x_height_ratio(path: Path) -> float | None:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    try:
        font = TTFont(str(path), fontNumber=0)
        return font["OS/2"].sxHeight / font["head"].unitsPerEm
    except Exception:
        return None


# ---- gate groups ------------------------------------------------------------
def gate_render_config(g: Gates, cfg: dict, root: Path) -> None:
    path = root / cfg["render_config"]
    if not path.exists():
        g.skip("렌더 설정", "config 존재", str(path))
        return
    c = json.loads(path.read_text(encoding="utf-8"))
    w, h = int(c.get("render_width", 0)), int(c.get("render_height", 0))
    g.check("렌더 설정", "해상도 설정", w >= MIN_WIDTH and h >= MIN_HEIGHT,
            f"{w}x{h} (최소 {MIN_WIDTH}x{MIN_HEIGHT})")
    crf = int(c.get("render_crf", 99))
    g.check("렌더 설정", "CRF", crf <= MAX_CRF, f"{crf} (최대 {MAX_CRF})")
    preset = str(c.get("render_preset", "?")).lower()
    g.check("렌더 설정", "preset", preset not in BANNED_PRESETS,
            f"{preset} (금지 {sorted(BANNED_PRESETS)})")


def gate_video(g: Gates, cfg: dict, root: Path) -> None:
    final = root / cfg["final_video"]
    if not final.exists():
        g.skip("영상", "최종본 존재", str(final))
        return
    dims = probe(final, "stream=width,height", "v:0")
    w, h = int(dims[0]), int(dims[1])
    g.check("영상", "최종본 해상도", w >= MIN_WIDTH and h >= MIN_HEIGHT, f"{w}x{h}")

    area = picture_area(final, float(cfg.get("picture_probe_sec", 60)))
    if area is None:
        g.skip("영상", "실제 그림 영역", "cropdetect 실패")
    else:
        g.check("영상", "실제 그림 영역", area[0] >= MIN_WIDTH,
                f"{area[0]}x{area[1]} (레터박스 제외, 가로 {MIN_WIDTH} 이상)")

    ref = cfg.get("timing_reference")
    if not ref:
        g.skip("영상", "길이 보존", "기준 파일 미지정")
        return
    ref_path = root / ref
    if not ref_path.exists():
        g.skip("영상", "길이 보존", f"{ref} 없음")
        return
    d_new = float(probe(final, "format=duration")[0])
    d_ref = float(probe(ref_path, "format=duration")[0])
    f_new = probe(final, "stream=nb_frames", "v:0")
    f_ref = probe(ref_path, "stream=nb_frames", "v:0")
    g.check("영상", "길이 보존", abs(d_new - d_ref) <= DURATION_TOLERANCE_SEC,
            f"{d_new:.6f}s vs 기준 {d_ref:.6f}s (차이 {(d_new-d_ref)*1000:+.3f}ms)")
    if f_new and f_ref:
        g.check("영상", "프레임 수 보존", f_new[0] == f_ref[0],
                f"{f_new[0]} vs 기준 {f_ref[0]}")


def gate_audio(g: Gates, cfg: dict, root: Path) -> None:
    final = root / cfg["final_video"]
    if final.exists():
        measured = loudness(final)
        if measured:
            lufs, peak = measured
            lo, hi = PROGRAMME_LUFS_RANGE
            g.check("오디오", "전체 라우드니스", lo <= lufs <= hi,
                    f"{lufs:.2f} LUFS (허용 {lo}~{hi})")
            g.check("오디오", "트루피크", peak <= MAX_TRUE_PEAK_DBTP,
                    f"{peak:.2f} dBTP (최대 {MAX_TRUE_PEAK_DBTP})")
        else:
            g.skip("오디오", "전체 라우드니스", "측정 실패")

    qa_rel = cfg.get("balance_qa")
    if not qa_rel or not (root / qa_rel).exists():
        g.skip("오디오", "더킹 우위", "밸런스 QA 없음")
    else:
        qa = json.loads((root / qa_rel).read_text(encoding="utf-8"))
        duck = qa.get("changes", {}).get("duck", {})
        lines = duck.get("per_line") or []
        if not lines:
            g.skip("오디오", "더킹 우위", "구간별 기록 없음")
        else:
            weak = [l for l in lines
                    if l.get("resulting_lead_db", 0) < MIN_DUCK_LEAD_DB
                    and l.get("film_lufs", -99) > -60]
            g.check("오디오", "더킹 우위", not weak,
                    f"{len(lines)}구간 중 {len(weak)}개가 +{MIN_DUCK_LEAD_DB}dB 미달"
                    + (f" (cue {[l['cue'] for l in weak]})" if weak else ""))
        summed = qa.get("measured", {}).get("capcut_sum_true_peak_dbtp")
        if summed is None:
            g.skip("오디오", "CapCut 합산 피크", "기록 없음")
        else:
            g.check("오디오", "CapCut 합산 피크", summed <= MAX_TRUE_PEAK_DBTP,
                    f"{summed:.2f} dBTP (CapCut은 리미터 없이 트랙을 합산한다)")

    voice = cfg.get("narration_stem")
    dialogue_srt = cfg.get("movie_caption_srt")
    bed = cfg.get("bed_video")
    if not (voice and dialogue_srt and bed):
        g.skip("오디오", "대사 대비 나레이션", "스템/자막/베드 경로 미지정")
        return
    voice_p, bed_p, srt_p = root / voice, root / bed, root / dialogue_srt
    if not all(p.exists() for p in (voice_p, bed_p, srt_p)):
        g.skip("오디오", "대사 대비 나레이션", "파일 없음")
        return
    narration_windows = [(a, b) for a, b in srt_windows(root / cfg["narration_srt"])] \
        if cfg.get("narration_srt") else []
    clean = [(a, b) for a, b in srt_windows(srt_p)
             if not any(a < nb and na < b for na, nb in narration_windows)][:40]
    step = max(1, len(clean) // 20)
    dlg = [v[0] for v in (loudness(bed_p, (a, b - a)) for a, b in clean[::step]) if v]
    nar = [v[0] for v in (loudness(voice_p, (a, b - a)) for a, b in narration_windows[:20]) if v]
    if not dlg or not nar:
        g.skip("오디오", "대사 대비 나레이션", "표본 부족")
        return
    diff = statistics.median(nar) - statistics.median(dlg)
    lo, hi = DIALOGUE_BALANCE_RANGE_DB
    g.check("오디오", "대사 대비 나레이션", lo <= diff <= hi,
            f"{diff:+.2f} dB (대사 {statistics.median(dlg):.2f} / "
            f"나레이션 {statistics.median(nar):.2f}, 허용 +{lo:.0f}~+{hi:.0f})")


def gate_capcut(g: Gates, cfg: dict, root: Path) -> None:
    project = cfg.get("capcut_project")
    if not project:
        g.skip("CapCut", "프로젝트", "미지정")
        return
    base = Path(os.path.expandvars(project))
    if not base.is_dir():
        g.skip("CapCut", "프로젝트", f"{base} 없음")
        return

    running = sh(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"])
    live = sum(1 for line in running.splitlines() if line.lower().startswith("capcut"))
    g.check("CapCut", "종료 상태", live == 0,
            f"{live}개 실행 중 (열려 있으면 저장이 덮어쓴다)")

    mirrors = [p for p in base.rglob("*")
               if p.is_file() and p.name in ("draft_content.json", "template-2.tmp")]
    hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in mirrors}
    g.check("CapCut", "미러 동일", len(hashes) == 1,
            f"{len(mirrors)}개 파일, 해시 {len(hashes)}종")

    doc = json.loads((base / "draft_content.json").read_text(encoding="utf-8"))
    missing, mismatch = [], []
    for kind in ("videos", "audios"):
        for item in doc.get("materials", {}).get(kind, []):
            path = item.get("path")
            if not path:
                continue
            p = Path(path)
            if not p.exists():
                missing.append(p.name)
            elif kind == "videos":
                dims = probe(p, "stream=width,height", "v:0")
                if dims and (int(dims[0]), int(dims[1])) != (item.get("width"), item.get("height")):
                    mismatch.append(f"{p.name} JSON {item.get('width')}x{item.get('height')}"
                                    f" != 실제 {dims[0]}x{dims[1]}")
    g.check("CapCut", "참조 파일 존재", not missing, ", ".join(missing) or "전부 존재")
    g.check("CapCut", "영상 치수 일치", not mismatch,
            "; ".join(mismatch) or "JSON과 실제 파일 일치")

    texts = {t["id"]: t for t in doc.get("materials", {}).get("texts", [])}
    tracks = {tr.get("name"): [s["material_id"] for s in tr["segments"]]
              for tr in doc.get("tracks", []) if tr.get("type") == "text"}
    for track, srt_key in (("MOVIE_DIALOGUE", "movie_caption_srt"),
                           ("REVIEW_NARRATION", "narration_srt")):
        if track not in tracks or not cfg.get(srt_key):
            g.skip("CapCut", f"{track} 개수", "대응 SRT 미지정")
            continue
        expected = len(srt_windows(root / cfg[srt_key]))
        g.check("CapCut", f"{track} 개수", len(tracks[track]) == expected,
                f"{len(tracks[track])}개 vs SRT {expected}개")

    # The font the project claims vs the font file it actually points at.
    bad_font, boxed = [], []
    metrics: dict[str, tuple[float, float]] = {}
    for track, ids in tracks.items():
        sample = texts.get(ids[0]) if ids else None
        if not sample:
            continue
        declared = str(sample.get("font_name", ""))
        fp = Path(str(sample.get("font_path", "")))
        family = font_family(fp) if fp.exists() else None
        if family and declared and family.split()[0].lower() not in declared.lower():
            bad_font.append(f"{track}: 이름 '{declared}' vs 실제 '{family}'")
        ratio = x_height_ratio(fp) if fp.exists() else None
        if ratio:
            metrics[track] = (ratio, float(sample.get("font_size", 0)))
        for i in ids:
            if float(texts[i].get("background_alpha", 0)) > 0:
                boxed.append(track)
                break
    g.check("CapCut", "폰트 이름·파일 일치", not bad_font,
            "; ".join(bad_font) or "선언한 폰트와 실제 파일이 같다")
    g.check("CapCut", "배경 박스 없음", not boxed,
            f"박스 켜진 트랙: {sorted(set(boxed))}" if boxed else "전부 꺼짐")

    if len(metrics) == 2 and cfg.get("check_optical_size", True):
        (t1, (r1, s1)), (t2, (r2, s2)) = metrics.items()
        h1, h2 = r1 * s1, r2 * s2
        rel = abs(h1 - h2) / max(h1, h2)
        g.check("CapCut", "자막 광학 크기 일치", rel <= OPTICAL_SIZE_TOLERANCE,
                f"{t1} {h1:.3f} vs {t2} {h2:.3f} (차이 {rel*100:.1f}%, "
                f"허용 {OPTICAL_SIZE_TOLERANCE*100:.0f}% — 같은 숫자여도 폰트가 다르면 다르게 보인다)")
    else:
        g.skip("CapCut", "자막 광학 크기 일치", "폰트 지표 부족")

    if cfg.get("movie_caption_srt") and cfg.get("narration_srt"):
        mv = srt_windows(root / cfg["movie_caption_srt"])
        nr = srt_windows(root / cfg["narration_srt"])
        overlaps = sum(1 for a, b in mv if any(a < nb and na < b for na, nb in nr))
        g.check("CapCut", "자막 시간 겹침", overlaps == 0, f"{overlaps}개")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    cfg_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    root = (cfg_path.parent / cfg.get("root", ".")).resolve()
    print(f"검사 대상: {root}")
    g = Gates()
    gate_render_config(g, cfg, root)
    gate_video(g, cfg, root)
    gate_audio(g, cfg, root)
    gate_capcut(g, cfg, root)
    return g.report()


if __name__ == "__main__":
    raise SystemExit(main())
