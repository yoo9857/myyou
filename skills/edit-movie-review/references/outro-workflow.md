# Spoiler-safe outro workflow

Treat the outro as a separate editorial unit after the approved pre-resolution ending. Do not use it to show or explain the omitted resolution.

## Default structure

Target 14–18 seconds:

1. `0–2s` — visual reset; let the selected shot establish itself.
2. `2–8s` — one spoiler-safe closing thought about the experience, character tension, or theme already earned.
3. `8–12s` — optional channel identity or next-review promise.
4. `12–16s` — one short CTA; avoid stacking subscribe, like, comment, and notification requests.
5. Final `0.6–1.2s` — picture and music fade together.

Adjust exact timing to speech, but keep silence before the first line and breathing room after the last.

## Visual selection

- Choose an energetic or atmospheric shot already shown before the spoiler cutoff.
- Reject the decisive solution, final reveal, survivor state, denouement, post-credit scene, and any shot whose meaning depends on them.
- Prefer a clean moving shot, character silhouette, travel shot, prop detail, or pre-climax action fragment.
- Mute the movie dialogue and original movie audio. Do not create a duplicate movie-caption track for the outro.
- Reframe only when needed for CTA-safe negative space; do not cover faces or the main action.

## Writing

- Keep the closing thought consistent with the approved human connective voice; avoid report-style `~입니다/~습니다` cadence.
- Make the line reflective, not conclusive: close the review experience without revealing how the story ends.
- Keep the CTA natural and singular, for example a next-review invitation or a brief subscribe request.
- Do not insert dry comic relief if the selected image carries grief, sacrifice, or unresolved terror.

## Audio

- Keep voice on the existing review-narration audio track.
- Put music on a separate outro-music track with low gain under speech.
- Start the music rise only after the final spoken syllable; do not pump volume between lines.
- Apply gradual voice duck attack/release only when voice audio exists. With voice OFF, do not lower the movie bed merely because a text cue exists.
- Fade music and picture together at the end; prevent clipped reverb or an abrupt AAC tail.

## CapCut and artifacts

- Save `outro_plan.v1.json`, `outro_review.srt`, the chosen visual interval, and `OUTRO_QA.json`.
- Append outro review and CTA cues to the single `REVIEW_NARRATION` text track.
- Keep exactly one movie-dialogue track and one review-narration text track; use a separate music audio track only.
- Close CapCut, back up all draft JSON mirrors, apply atomically, and verify duration, cue counts, material counts, and mirror equality.
- If only wording changes, rebuild the outro text/audio assets; do not rerender the unchanged main review.
