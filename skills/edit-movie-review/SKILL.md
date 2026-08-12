---
name: edit-movie-review
description: Build or improve a 19–25 minute YouTube movie-review edit from a movie file and existing subtitle file, including story mapping, spoiler-safe scene selection, short hook-style narration, exact subtitle retiming, ElevenLabs female English voiceover, FFmpeg assembly, a curiosity-preserving outro, and a CapCut handoff package. Use for requests to analyze, cut, narrate, subtitle, continue, repair sync, or package movie-review videos, especially when the user refers to the established movie-review workflow or asks to process another film the same way.
---

# Edit Movie Review

Read `references/workflow.md` before planning or rendering and `references/quality-gates.md` before subtitle, audio, or CapCut work.

1. Locate the movie, supplied SRT, configuration, prior outputs, and selected music. Preserve originals.
2. Use the supplied SRT; do not transcribe again unless it is missing or unusable.
3. Build an audio-first dialogue/silence map, then visually inspect representative candidate scenes.
4. Plan a 19–25 minute arc through the pre-resolution climax. Hide the final solution, survivor state, final reveal, and denouement.
5. Alternate preserved dialogue with sparse 2–5 second narration. If the project has an approved voice profile, treat it as authoritative. For COLONY use `voice_profiles/colony_original_normal.json`; do not substitute Nayva or an unverified cached take.
6. Rebuild captions from exact source/output offsets. Suppress only cues overlapping narration and resume movie captions afterward.
7. Keep movie dialogue and narration in separate CapCut tracks with separate JSON style presets. Never import the combined SRT as a third duplicate track.
8. Back up the CapCut project and close CapCut before modifying JSON.
9. Create a short spoiler-safe outro with muted movie audio, narration, credit music, and a final CTA.
10. Package editable media, SRTs, timeline/edit plan, and import instructions under `output/capcut_import/`.

For TTS work, read `references/voice-lock.md`. Generate one pilot line before a batch whenever the user has not yet approved the active profile. Copy an approved exact-text asset verbatim, and reject cached audio whose profile hash, text, model, or post-processing record differs.

Inspect the latest state before rerunning expensive work. Change only the requested line, voice, subtitle, or outro element when possible. Never print or commit API keys or copyrighted source media.
