# Reusable workflow

- Target 19–25 minutes, normally 22 minutes.
- Structure: cold open → setup → incident → escalation → midpoint → rising danger → pre-resolution climax.
- End before the decisive solution, final reveal, survivor result, and aftermath.
- Parse the supplied SRT into dialogue events and remap each cue with `output_time = output_cut_start + source_caption_time - source_cut_start`.
- Keep most narration 2–5 seconds, 5–14 English words, and 12–32 Korean characters.
- Prefer declarative foreshadowing; avoid repeating the next movie line.
- Load the approved project voice profile before TTS. Generate and approve one pilot, then batch-generate with the same request and post-processing. Never infer voice equivalence from Voice ID alone.
- Copy exact-text approved voice assets verbatim. Reject stale clips whose profile hash or text does not match the manifest.
- Build on a clean movie-audio bed; do not mix a replacement voice over an already narrated render.
- Leave about 0.12 seconds before original dialogue resumes, then tune by playback.
- Produce separate movie, narration, and combined SRT files.
- In CapCut, import only movie and narration SRTs as separate tracks. Use white lower captions for dialogue and larger warm-ivory captions slightly above for narration.
- Outro: 14–18 seconds, energetic spoiler-safe scene, movie audio muted, short wrap-up, music rise after speech, final CTA.
