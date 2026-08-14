"""Check the approved voice on Korean before committing the project to it.

The approved profile was locked on English samples for COLONY and reused for Constantine,
both of which narrated in English. This review narrates in Korean, so the voice has to be
heard reading Korean before 57 lines are generated with it. Same profile, same post-process,
only the language changes — anything else would break the lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = ROOT / "output" / "voice_samples_ko"
PROFILE = REPO / "voice_profiles" / "colony_original_normal.json"

# Real lines from the story map, chosen to cover the three registers the review needs:
# a cold open, a rule being explained, and the standoff it ends on.
LINES = [
    ("01_cold_open",
     "미국 시골 마을의 윌러드는 하루도 빠짐없이 뒷산 십자가 앞에서 기도를 올립니다."),
    ("02_rule_clarify",
     "아버지는 아빈에게 때를 기다려 되갚는 법을 가르쳤습니다."),
    ("03_standoff",
     "두 사람은 서로에게 총을 겨눈 채, 아빈은 주머니 속 사진을 증거로 내밉니다."),
]


def load_profile() -> dict:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["_sha256"] = hashlib.sha256(
        json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return profile


def duration(path: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def speak(key: str, profile: dict, text: str, raw: Path) -> None:
    payload = json.dumps({
        "text": text,
        "model_id": profile["model_id"],
        "language_code": "ko",
        "apply_text_normalization": "auto",
    }).encode("utf-8")
    query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{profile['voice_id']}?{query}",
        data=payload, method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                audio = response.read()
            if len(audio) < 1000:
                raise RuntimeError("빈 오디오 응답")
            raw.write_bytes(audio)
            return
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            if attempt == 3 or exc.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
            time.sleep(attempt * 2)


def main() -> int:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY가 이 프로세스에 없습니다.")
    profile = load_profile()
    OUT.mkdir(parents=True, exist_ok=True)
    trim, _, loudness = profile["postprocess"]["ffmpeg_filter"].rpartition(",")
    if not loudness.startswith("loudnorm=") or "silenceremove" not in trim:
        raise RuntimeError("프로필 필터 형태가 예상과 다릅니다.")

    report = []
    for name, text in LINES:
        raw = OUT / f"{name}.raw.mp3"
        final = OUT / f"{name}.mp3"
        if not raw.exists() or raw.stat().st_size < 1000:
            speak(api_key, profile, text, raw)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(raw),
             "-af", profile["postprocess"]["ffmpeg_filter"],
             "-ar", "48000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "192k", str(final)],
            check=True,
        )
        secs = duration(final)
        chars = len(text)
        report.append({
            "name": name, "text": text, "chars": chars,
            "duration_sec": round(secs, 2),
            "chars_per_sec": round(chars / secs, 2),
            "file": str(final.relative_to(REPO)).replace("\\", "/"),
        })
        print(f"  {name}  {secs:5.2f}초  {chars}자  {chars/secs:4.2f}자/초  {text[:34]}")

    meta = {
        "voice_id": profile["voice_id"],
        "model": profile["model_id"],
        "language_code": "ko",
        "profile_id": profile["profile_id"],
        "profile_sha256": profile["_sha256"],
        "postprocess": profile["postprocess"]["ffmpeg_filter"],
        "note": "Same approved profile and post-process as COLONY and Constantine; only "
                "language_code changes to ko. Listen before the project commits to it.",
        "samples": report,
    }
    (OUT / "manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    rate = sum(r["chars_per_sec"] for r in report) / len(report)
    print(f"\n  평균 {rate:.2f}자/초 (설정된 기준 5.2자/초)")
    print(f"  기록: {(OUT / 'manifest.json').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
