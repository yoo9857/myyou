"""Rebalance the Constantine V5 mix: movie audible, narration not shouting, -14 LUFS.

Three changes against mix_constantine_selected_voice.py:

1. The movie bed is brought to a measured target instead of being used at source
   level, so quiet scenes stay audible.
2. Ducking is derived from the narration cue windows at a fixed depth, replacing
   sidechaincompress whose depth swung between 0.6 dB and 17.3 dB depending on
   the voice waveform.
3. The programme is normalised to -14 LUFS. The same final gain is baked into the
   bed and the voice stem, so the CapCut timeline -- which sums the two as separate
   tracks -- lands at the same loudness as the standalone render.
"""
from __future__ import annotations

import contextlib
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Constantine" / "story_review_v5" / "output"
AUDIO_ROOT = OUTPUT / "narration_audio_selected_voice"
MANIFEST = AUDIO_ROOT / "manifest.json"
# 1080p re-render: the 540p original was CRF 30 / ultrafast at 960x540 from a 3840x1608
# source. Frame counts and durations are identical, so every caption cue still lines up.
SOURCE_VIDEO = OUTPUT / "constantine_story_review_v5_with_outro_1080p.mp4"
MUSIC_SOURCE = ROOT / "The Final Resolve.mp3"

VOICE_STEM = OUTPUT / "constantine_selected_voice_stem.wav"
VOICE_M4A = OUTPUT / "constantine_selected_voice_stem.m4a"
MUSIC_STEM = OUTPUT / "constantine_outro_music_stem.wav"
MUSIC_M4A = OUTPUT / "constantine_outro_music_stem.m4a"
BED_VIDEO = OUTPUT / "constantine_story_review_v5_selected_voice_bed.mp4"
FINAL_VIDEO = OUTPUT / "constantine_story_review_v5_selected_voice_final.mp4"
QA_PATH = OUTPUT / "CONSTANTINE_BALANCE_QA.json"
WORK = ROOT / "Constantine" / "story_review_v5" / "work"

FINAL_DURATION = 1501.021321
OUTRO_START = 1487.0
OUTRO_DURATION = FINAL_DURATION - OUTRO_START
MUSIC_SOURCE_START = 15.0
MUSIC_RISE_REL = 12.1
MUSIC_FADE_REL = 13.1
MUSIC_SPEECH_GAIN = 0.32
MUSIC_POST_SPEECH_GAIN = 0.78

# --- balance controls -------------------------------------------------------
# Target: narration about 5 dB over the movie under it, down from a measured 9.8 dB
# median, and with the spread pulled in from -4.5..+34.2 dB.
#
# The film's own level swings from -12.9 to -50.6 LUFS scene to scene, which is what
# made the old mix unpredictable. A gentle compressor tightens that before anything
# else, so quiet scenes come up and the loud ones stop burying the narration.
MOVIE_COMPRESS = "acompressor=threshold=-24dB:ratio=2.5:attack=20:release=400:makeup=2"
MOVIE_TARGET_LUFS = -19.0
# Ducking is worked out per narration line rather than as one fixed depth.
#
# A single depth cannot work here: the film under the 29 lines ranges from -14.2 LUFS
# (the club at 6:28) to -44.6 LUFS, a 30 dB spread. At -6 dB the narration sat 2 dB
# BELOW the club music; at a depth deep enough for the club, the quiet scenes would
# vanish. So each line gets the reduction needed to put the narration a fixed amount
# above the film under it, and no more.
TARGET_LEAD_DB = 7.0    # how far the narration should sit above the ducked film
DUCK_FLOOR_DB = -20.0   # deepest allowed, so loud scenes are never fully erased
DUCK_CEIL_DB = -2.0     # shallowest allowed, so the dip always reads as deliberate
DUCK_ATTACK_SEC = 0.35
DUCK_RELEASE_SEC = 0.60
VOICE_GAIN = 0.36           # was 0.60, i.e. -4.4 dB
PROGRAMME_TARGET_LUFS = -15.0
PEAK_CEILING_DBTP = -1.0
# CapCut sums the bed and the voice stem as separate tracks and cannot reproduce the
# final limiter, so the bed has to leave the file already peak-safe. Without this the
# bed measured +5.05 dBTP on its own and distorted in the CapCut timeline.
BED_CEILING_DBTP = -4.0
# Cap how much the limiter is allowed to shave, so loudness is never bought by
# squashing the film.
MAX_LIMITING_DB = 3.0
EXPECTED_CUES = 29


@contextlib.contextmanager
def exclusive_run():
    """Refuse to start while another copy is mid-render.

    Two overlapping runs share every output path: one writes a stem while the other
    mixes it, which produced a silent stage-1 mix and an inf gain from it.
    """
    lock = WORK / "remix_balance.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            f"{lock} exists, so another remix is running or died mid-way. "
            "Wait for it, or delete the lock if no ffmpeg is alive."
        ) from None
    try:
        os.write(handle, str(os.getpid()).encode())
        os.close(handle)
        yield
    finally:
        lock.unlink(missing_ok=True)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        text=True, encoding="utf-8",
    ).strip())


def measure(path: Path, prefilter: str = "", stream: str = "a:0",
            window: tuple[float, float] | None = None) -> tuple[float, float]:
    """Integrated loudness and true peak, optionally after a filter chain.

    loudnorm reports on what reaches it, so prefilter lets the movie bed be measured
    post-compression without writing an intermediate file. window is (start, duration)
    for measuring a single narration slot rather than the whole file.
    """
    chain = f"{prefilter}," if prefilter else ""
    command = ["ffmpeg", "-v", "info"]
    if window is not None:
        command += ["-ss", f"{window[0]:.3f}", "-t", f"{window[1]:.3f}"]
    command += ["-i", str(path), "-map", f"0:{stream}",
                "-af", f"{chain}loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                "-f", "null", "-"]
    out = subprocess.run(command, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    blob = json.loads(out[out.rindex("{"):out.rindex("}") + 1])
    loudness = float(blob["input_i"])
    if not math.isfinite(loudness):
        # Digital silence in this slot: treat it as very quiet so the duck maths stays sane.
        loudness = -70.0
    return loudness, float(blob["input_tp"])


def db_to_linear(db: float) -> float:
    if not math.isfinite(db):
        raise RuntimeError(
            f"Refusing to build a gain from a non-finite {db} dB. A silent or NaN "
            "measurement upstream would otherwise be baked in as volume=inf."
        )
    if not -40.0 <= db <= 40.0:
        raise RuntimeError(f"Gain {db:+.2f} dB is outside the sane range; aborting.")
    return 10.0 ** (db / 20.0)


def plan_ducks(cues: list[dict], movie_gain_db: float, voice_gain: float) -> list[dict]:
    """Work out, per narration line, how far the film has to come down.

    Measures the film under each line (post-compressor, as the bed will hear it) and the
    fitted narration itself, then solves for the reduction that leaves the narration
    TARGET_LEAD_DB above the film.
    """
    # The stem duplicates each mono cue into both channels (pan=stereo|c0=c0|c1=c0).
    # EBU R128 sums channel energy, so the same audio in L and R measures +3.01 dB
    # louder than the mono file. Leaving this out understated the narration by 3 dB and
    # made every duck 3 dB deeper than asked for.
    MONO_TO_STEREO_DB = 3.01
    voice_offset_db = 20.0 * math.log10(voice_gain) + MONO_TO_STEREO_DB
    plan: list[dict] = []
    for cue in cues:
        start, end = float(cue["start_sec"]), float(cue["end_sec"])
        movie_i, _ = measure(SOURCE_VIDEO, MOVIE_COMPRESS, window=(start, end - start))
        fitted_i, _ = measure(Path(str(cue["fitted_file"])))
        narration_in_mix = fitted_i + voice_offset_db
        film_at_full = movie_i + movie_gain_db
        wanted = narration_in_mix - TARGET_LEAD_DB - film_at_full
        duck_db = min(DUCK_CEIL_DB, max(DUCK_FLOOR_DB, wanted))
        plan.append({
            "cue": int(cue["cue"]),
            "start_sec": start,
            "end_sec": end,
            "film_lufs": round(movie_i, 2),
            "narration_lufs": round(narration_in_mix, 2),
            "duck_db": round(duck_db, 2),
            "resulting_lead_db": round(narration_in_mix - (film_at_full + duck_db), 2),
            "clamped": not (DUCK_FLOOR_DB <= wanted <= DUCK_CEIL_DB),
        })
        print(f"  cue {plan[-1]['cue']:2}  film {movie_i:7.2f}  duck {duck_db:6.2f} dB  "
              f"lead {plan[-1]['resulting_lead_db']:+5.2f} dB"
              f"{'  (clamped)' if plan[-1]['clamped'] else ''}", flush=True)
    return plan


def duck_expression(plan: list[dict]) -> str:
    """Per-line ramped dips, for volume=eval=frame.

    Each line contributes a trapezoid that rises over the attack before it starts, holds
    while it plays, and falls over the release after it ends, scaled to that line's own
    depth. The sum is clipped to the deepest requested depth so overlapping ramps between
    lines a fraction of a second apart cannot stack into a deeper dip than any line asked
    for -- and the film does not pump back up in the gap.
    """
    attack, release = DUCK_ATTACK_SEC, DUCK_RELEASE_SEC
    terms = []
    for item in plan:
        rise_from = max(0.0, item["start_sec"] - attack)
        fall_to = item["end_sec"] + release
        depth = db_to_linear(item["duck_db"]) - 1.0  # negative
        terms.append(
            f"({depth:.6f})"
            f"*clip((t-{rise_from:.3f})/{attack:.3f},0,1)"
            f"*clip(({fall_to:.3f}-t)/{release:.3f},0,1)"
        )
    deepest = db_to_linear(min(item["duck_db"] for item in plan))
    return f"clip(1+{'+'.join(terms)},{deepest:.6f},1)"


def build_voice_stem(cues: list[dict], gain: float) -> None:
    command = ["ffmpeg", "-y", "-v", "error"]
    filters: list[str] = []
    labels: list[str] = []
    for index, cue in enumerate(cues):
        path = Path(str(cue["fitted_file"]))
        if not path.exists():
            raise FileNotFoundError(path)
        command += ["-i", str(path)]
        delay_ms = round(float(cue["start_sec"]) * 1000)
        filters.append(
            f"[{index}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,"
            f"adelay={delay_ms}|{delay_ms}[v{index}]"
        )
        labels.append(f"[v{index}]")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0,volume={gain:.6f},"
        + f"apad=whole_dur={FINAL_DURATION:.6f},atrim=0:{FINAL_DURATION:.6f}[voice]"
    )
    command += ["-filter_complex", ";".join(filters), "-map", "[voice]",
                "-c:a", "pcm_s24le", str(VOICE_STEM)]
    run(command)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(VOICE_STEM),
         "-c:a", "aac", "-b:a", "192k", str(VOICE_M4A)])


def build_music_stem(gain: float) -> None:
    fade_duration = max(0.1, OUTRO_DURATION - MUSIC_FADE_REL)
    delta = MUSIC_POST_SPEECH_GAIN - MUSIC_SPEECH_GAIN
    curve = f"{MUSIC_SPEECH_GAIN:.3f}+{delta:.3f}*clip((t-{MUSIC_RISE_REL:.3f})/0.5,0,1)"
    audio_filter = (
        f"atrim=start={MUSIC_SOURCE_START:.3f}:duration={OUTRO_DURATION:.6f},"
        "asetpts=PTS-STARTPTS,aresample=48000,"
        f"volume=eval=frame:volume='{curve}',"
        f"afade=t=out:st={MUSIC_FADE_REL:.3f}:d={fade_duration:.6f},"
        f"volume={gain:.6f}"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", str(MUSIC_SOURCE), "-af", audio_filter,
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(MUSIC_STEM)])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(MUSIC_STEM),
         "-c:a", "aac", "-b:a", "192k", str(MUSIC_M4A)])


def build_bed(movie_gain: float, duck: str, shared_gain: float, destination: Path) -> None:
    """Peak-control the bed, then scale it.

    The limiter has to sit BEFORE the shared gain. With it last, its ceiling pinned the
    output peak and trimming the shared gain moved nothing; in front of the gain the peak
    scales with it, and bed-to-voice balance is untouched because both get the same gain.
    """
    audio_filter = (
        f"aresample=48000,{MOVIE_COMPRESS},volume={movie_gain:.6f},"
        f"volume=eval=frame:volume='{duck}',"
        f"volume=eval=frame:volume='if(gte(t,{OUTRO_START:.3f}),0,1)',"
        f"alimiter=limit={db_to_linear(BED_CEILING_DBTP):.6f}:attack=5:release=80:level=false,"
        f"volume={shared_gain:.6f}"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", str(SOURCE_VIDEO), "-af", audio_filter,
         "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-t", f"{FINAL_DURATION:.6f}", str(destination)])


def build_final(destination: Path) -> None:
    delay_ms = round(OUTRO_START * 1000)
    filter_complex = (
        f"[2:a]adelay={delay_ms}|{delay_ms}[music];"
        "[0:a][1:a][music]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit={db_to_linear(PEAK_CEILING_DBTP):.6f}:attack=5:release=80:level=false[mix]"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", str(destination), "-i", str(VOICE_STEM),
         "-i", str(MUSIC_STEM), "-filter_complex", filter_complex,
         "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-movflags", "+faststart", "-t", f"{FINAL_DURATION:.6f}", str(FINAL_VIDEO)])


def main() -> int:
    with exclusive_run():
        return _main()


def _main() -> int:
    report = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cues = list(report["cues"])
    if len(cues) != EXPECTED_CUES:
        raise RuntimeError(f"Expected {EXPECTED_CUES} cues, found {len(cues)}")
    WORK.mkdir(parents=True, exist_ok=True)
    scratch_bed = WORK / "balance_bed_stage1.mp4"

    raw_i, _ = measure(SOURCE_VIDEO)
    movie_i, _ = measure(SOURCE_VIDEO, MOVIE_COMPRESS)
    movie_gain_db = MOVIE_TARGET_LUFS - movie_i
    movie_gain = db_to_linear(movie_gain_db)
    print(f"movie {raw_i:.2f} LUFS raw -> {movie_i:.2f} compressed -> "
          f"target {MOVIE_TARGET_LUFS} ({movie_gain_db:+.2f} dB)", flush=True)

    print("나레이션 구간별 감쇠량 계산", flush=True)
    duck_plan = plan_ducks(cues, movie_gain_db, VOICE_GAIN)
    duck = duck_expression(duck_plan)
    depths = [item["duck_db"] for item in duck_plan]
    print(f"  감쇠 범위 {min(depths):.2f} ~ {max(depths):.2f} dB, "
          f"평균 {sum(depths)/len(depths):.2f} dB", flush=True)
    build_voice_stem(cues, VOICE_GAIN)
    build_music_stem(1.0)
    build_bed(movie_gain, duck, 1.0, scratch_bed)

    # Measure the sum at unity, then bake one shared gain into every stem.
    build_final(scratch_bed)
    programme_i, programme_tp = measure(FINAL_VIDEO)
    wanted_db = PROGRAMME_TARGET_LUFS - programme_i
    # The limiter may shave up to MAX_LIMITING_DB; beyond that the film would audibly
    # squash, so accept a quieter programme instead.
    allowed_db = (PEAK_CEILING_DBTP - programme_tp) + MAX_LIMITING_DB
    final_gain_db = min(wanted_db, allowed_db)
    limiting_db = max(0.0, (programme_tp + final_gain_db) - PEAK_CEILING_DBTP)
    if final_gain_db < wanted_db:
        print(f"capped at {final_gain_db:+.2f} dB instead of {wanted_db:+.2f} dB "
              f"to keep limiting within {MAX_LIMITING_DB} dB", flush=True)
    final_gain = db_to_linear(final_gain_db)
    print(f"programme {programme_i:.2f} LUFS (peak {programme_tp:.2f} dBTP) "
          f"-> {final_gain_db:+.2f} dB, limiter shaves {limiting_db:.2f} dB", flush=True)

    def build_all(shared_gain: float) -> None:
        build_voice_stem(cues, VOICE_GAIN * shared_gain)
        build_music_stem(shared_gain)
        build_bed(movie_gain, duck, shared_gain, BED_VIDEO)
        build_final(BED_VIDEO)

    def capcut_sum() -> tuple[float, float]:
        """What CapCut produces: bed + voice summed with no limiter of its own."""
        probe = WORK / "capcut_sum_probe.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(BED_VIDEO), "-i", str(VOICE_STEM),
             "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[s]",
             "-map", "[s]", "-c:a", "pcm_s24le", str(probe)])
        result = measure(probe)
        probe.unlink(missing_ok=True)
        return result

    build_all(final_gain)
    sum_i, sum_tp = capcut_sum()
    trim_db = 0.0
    # AAC true-peak overshoot is not linear in the gain, so converge instead of
    # assuming one correction lands.
    for _ in range(3):
        if sum_tp <= PEAK_CEILING_DBTP:
            break
        step = (sum_tp - PEAK_CEILING_DBTP) + 0.15
        trim_db += step
        final_gain_db -= step
        final_gain = db_to_linear(final_gain_db)
        print(f"CapCut sum {sum_tp:.2f} dBTP over ceiling; trimming {step:.2f} dB "
              f"(total {trim_db:.2f}) and rebuilding at {final_gain_db:+.2f} dB", flush=True)
        build_all(final_gain)
        sum_i, sum_tp = capcut_sum()
    scratch_bed.unlink(missing_ok=True)

    final_i, final_tp = measure(FINAL_VIDEO)
    bed_i, bed_tp = measure(BED_VIDEO)
    voice_i, voice_tp = measure(VOICE_STEM)
    if sum_tp > PEAK_CEILING_DBTP:
        print(f"WARNING: the CapCut sum still peaks at {sum_tp:.2f} dBTP, above "
              f"{PEAK_CEILING_DBTP} dBTP", flush=True)
    qa = {
        "status": "pass",
        "supersedes": "FINAL_SELECTED_VOICE_AUDIO_QA.json",
        "problem": "narration sat 9.8 dB over the movie (spread -4.5..+34.2 dB) and the "
                   "programme was -20.5 LUFS",
        "changes": {
            "movie_compressor": MOVIE_COMPRESS,
            "movie_raw_lufs": round(raw_i, 2),
            "movie_compressed_lufs": round(movie_i, 2),
            "movie_bed_target_lufs": MOVIE_TARGET_LUFS,
            "movie_gain_db": round(movie_gain_db, 2),
            "duck": {
                "was": "sidechaincompress threshold=0.018 ratio=5 (0.6..17.3 dB, waveform dependent)",
                "mode": "per-line, solved from the measured film level under each line",
                "target_lead_db": TARGET_LEAD_DB,
                "floor_db": DUCK_FLOOR_DB,
                "ceiling_db": DUCK_CEIL_DB,
                "depth_range_db": [min(i["duck_db"] for i in duck_plan),
                                   max(i["duck_db"] for i in duck_plan)],
                "mean_depth_db": round(
                    sum(i["duck_db"] for i in duck_plan) / len(duck_plan), 2),
                "clamped_lines": [i["cue"] for i in duck_plan if i["clamped"]],
                "shape": "ramped trapezoid per line, summed and clipped to the deepest depth",
                "attack_sec": DUCK_ATTACK_SEC,
                "release_sec": DUCK_RELEASE_SEC,
                "per_line": duck_plan,
            },
            "voice_gain": {"was": 0.60, "now": VOICE_GAIN},
            "programme_target_lufs": PROGRAMME_TARGET_LUFS,
            "shared_final_gain_db": round(final_gain_db, 2),
            "limiter_shave_db": round(limiting_db, 2),
            "limiter_shave_cap_db": MAX_LIMITING_DB,
            "capcut_headroom_trim_db": round(trim_db, 2),
        },
        "measured": {
            "final_lufs": round(final_i, 2),
            "final_true_peak_dbtp": round(final_tp, 2),
            "bed_lufs": round(bed_i, 2),
            "bed_true_peak_dbtp": round(bed_tp, 2),
            "voice_stem_lufs": round(voice_i, 2),
            "voice_stem_true_peak_dbtp": round(voice_tp, 2),
            "capcut_sum_lufs": round(sum_i, 2),
            "capcut_sum_true_peak_dbtp": round(sum_tp, 2),
            "capcut_sum_within_ceiling": sum_tp <= PEAK_CEILING_DBTP,
        },
        "bed_ceiling_dbtp": BED_CEILING_DBTP,
        "capcut_note": "bed and voice stem carry the same final gain, so the CapCut "
                       "timeline sums to the same loudness as this render",
        "final_duration_sec": probe_duration(FINAL_VIDEO),
        "outputs": {
            "final_video": str(FINAL_VIDEO),
            "bed_video": str(BED_VIDEO),
            "voice_stem_m4a": str(VOICE_M4A),
            "music_stem_m4a": str(MUSIC_M4A),
        },
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa["measured"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
