# Quality gates

- Duration is 19–25 minutes or the deviation is explained.
- Opening narration matches the visible scene.
- The full resolution and aftermath are absent.
- Strong dialogue/action has no narration collision.
- The user-approved pilot, batch manifest, and active voice profile have the same voice ID, model, request settings, and post-processing chain.
- Every reused TTS clip has matching text and profile SHA-256; exact-text approved assets are copied verbatim.
- No previous reviewer voice remains underneath or between replacement narration lines.
- Movie audio and captions resume after each narration interval.
- Every cue is recomputed from exact cut offsets and stays inside its owning clip.
- Exactly one movie-dialogue track and one narration track exist in CapCut.
- SRT cue counts equal CapCut text-segment counts.
- CapCut timeline mirrors are synchronized and lint has no errors.
- Source media remains unchanged and secrets are absent from deliverables.
