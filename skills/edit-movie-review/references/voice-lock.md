# Approved narration voice lock

- Treat a project voice-profile JSON as the source of truth for voice ID, model, language, request overrides, post-processing, and approved reference assets.
- For COLONY load `voice_profiles/colony_original_normal.json`.
- Use Voice ID `Vuo6zmtjWmlDbzqgIDos`, model `eleven_v3`, English language, and provider-default voice settings. Do not send style, stability, similarity, speaker-boost, or speed overrides.
- Send `apply_text_normalization: auto`.
- Apply the profile's exact silence trim and loudness filter, then encode 48 kHz mono MP3 at 192 kbps.
- If narration text exactly matches an approved asset, copy that asset verbatim instead of regenerating it.
- Store a profile SHA-256, text, duration, and source type in the narration manifest. Reuse a cached clip only when its text and profile hash match.
- Generate a single pilot with `python generate_narration_audio.py --only-order N --force` when approval is needed. Do not batch-render until the user approves it.
- Never layer a new voice over a render that may already contain reviewer narration. Use a clean movie-audio bed or replace every prior narration interval first.
- Before updating CapCut, confirm it is closed, back up the draft, then verify that its media points to the new audio/video and that obsolete narration tracks are absent.
