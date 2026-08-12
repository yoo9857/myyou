from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("MOVIE_REVIEW_ROOT", CODE_ROOT)).resolve()
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"


def duration(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(path),
            ],
            text=True,
            encoding="utf-8",
        ).strip()
    )


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate matching files.")
    parser.add_argument("--only-order", type=int, help="Generate one pilot line only.")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    profile_path = ROOT / str(config["elevenlabs_voice_profile"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile_hash = hashlib.sha256(
        json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    voice_id = str(profile["voice_id"])
    model_id = str(profile["model_id"])
    language_code = str(profile.get("language_code", "en"))
    postprocess_filter = str(profile["postprocess"]["ffmpeg_filter"])
    approved_assets = {
        str(item["text"]): ROOT / str(item["file"])
        for item in profile.get("approved_text_assets", [])
    }

    plan = json.loads((OUTPUT / "edit_plan.json").read_text(encoding="utf-8"))
    narration_items = [
        {
            "order": int(segment["order"]),
            "text": str(segment.get("narration_tts_en", "")).strip(),
            "caption_ko": str(segment.get("narration", "")).strip(),
            "max_seconds": segment.get("narration_max_seconds"),
        }
        for segment in plan["segments"]
        if str(segment.get("narration_tts_en", "")).strip()
    ]
    if args.only_order is not None:
        narration_items = [item for item in narration_items if item["order"] == args.only_order]
        if not narration_items:
            raise RuntimeError(f"Narration order {args.only_order} was not found.")

    target = CAPCUT / "narration_audio"
    raw_target = target / "raw"
    target.mkdir(parents=True, exist_ok=True)
    raw_target.mkdir(parents=True, exist_ok=True)
    manifest_path = target / "manifest.json"
    old_manifest = []
    if manifest_path.exists():
        old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_by_order = {int(item["order"]): item for item in old_manifest}
    manifest: list[dict[str, object]] = [] if args.only_order is None else old_manifest.copy()

    for item in narration_items:
        text = str(item["text"])
        order = int(item["order"])
        output = target / f"clip_{order:03d}.mp3"
        raw_output = raw_target / f"clip_{order:03d}.raw.mp3"
        previous = old_by_order.get(order, {})
        reusable = (
            not args.force
            and output.exists()
            and output.stat().st_size > 1000
            and previous.get("tts_en") == text
            and previous.get("profile_sha256") == profile_hash
        )
        source_type = str(previous.get("source_type", "profile-matched cache"))

        if not reusable:
            approved = approved_assets.get(text)
            if approved is not None:
                if not approved.exists():
                    raise FileNotFoundError(f"Approved voice reference is missing: {approved}")
                shutil.copy2(approved, output)
                source_type = "approved reference copied verbatim"
            else:
                query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
                payload = json.dumps(
                    {
                        "text": text,
                        "model_id": model_id,
                        "language_code": language_code,
                        "apply_text_normalization": "auto",
                    }
                ).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "xi-api-key": key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                )
                try:
                    with urllib.request.urlopen(request, timeout=120) as response:
                        audio = response.read()
                except urllib.error.HTTPError as exc:
                    raise RuntimeError(
                        f"ElevenLabs request failed for clip {order}: HTTP {exc.code}"
                    ) from None
                if len(audio) < 1000:
                    raise RuntimeError(f"ElevenLabs returned an invalid payload for clip {order}.")
                raw_output.write_bytes(audio)
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-v", "error", "-i", str(raw_output),
                        "-af", postprocess_filter,
                        "-ar", "48000", "-ac", "1", "-c:a", "libmp3lame",
                        "-b:a", "192k", str(output),
                    ],
                    check=True,
                )
                source_type = "generated and approved-profile postprocessed"

        audio_duration = duration(output)
        max_seconds = item["max_seconds"]
        if max_seconds is not None and audio_duration > float(max_seconds) + 0.1:
            raise RuntimeError(
                f"Clip {order} is {audio_duration:.3f}s, over its {float(max_seconds):.3f}s limit."
            )
        record = {
            "order": order,
            "file": output.name,
            "tts_en": text,
            "caption_ko": item["caption_ko"],
            "max_seconds": max_seconds,
            "duration_sec": round(audio_duration, 3),
            "voice_id": voice_id,
            "model": model_id,
            "voice_settings": "voice defaults (no request override)",
            "profile_id": profile["profile_id"],
            "profile_sha256": profile_hash,
            "postprocess_filter": postprocess_filter,
            "source_type": source_type,
        }
        if args.only_order is None:
            manifest.append(record)
        else:
            manifest = [entry for entry in manifest if int(entry["order"]) != order]
            manifest.append(record)
            manifest.sort(key=lambda entry: int(entry["order"]))
        print(f"Narration audio ready: clip {order:03d} ({source_type})")

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Voice profile locked: {profile['profile_id']} ({len(narration_items)} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
