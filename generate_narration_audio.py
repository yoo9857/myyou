from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("MOVIE_REVIEW_ROOT", CODE_ROOT)).resolve()
OUTPUT = ROOT / "output"
CAPCUT = OUTPUT / "capcut_import"


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not available in this process.")

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    plan_path = OUTPUT / "edit_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    voice_id = str(config.get("elevenlabs_voice_id", "cfc7wVYq4gw4OpcEEAom"))
    model_id = str(config.get("elevenlabs_model", "eleven_v3"))
    target = CAPCUT / "narration_audio"
    target.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []

    for segment in plan["segments"]:
        text = str(segment.get("narration_tts_en", "")).strip()
        if not text:
            continue
        order = int(segment["order"])
        output = target / f"clip_{order:03d}.mp3"
        if not output.exists() or output.stat().st_size == 0:
            query = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
            payload = json.dumps({
                "text": text,
                "model_id": model_id,
                "language_code": "en",
            }).encode("utf-8")
            request = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            )
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    audio = response.read()
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"ElevenLabs request failed for clip {order}: HTTP {exc.code}") from None
            if len(audio) < 1000:
                raise RuntimeError(f"ElevenLabs returned an invalid audio payload for clip {order}.")
            output.write_bytes(audio)
        manifest.append({"order": order, "file": output.name, "tts_en": text})
        print(f"Narration audio ready: clip {order:03d}")

    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} Nayva narration files in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
