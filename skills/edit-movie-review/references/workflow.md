# Reusable workflow

- Treat the story map as the source of truth; the edit plan and narration are derived artifacts.
- Treat `work/references/learning_registry.json` as the only source of approved transferable reference rules. Raw reference captions and unapproved observations never enter generation prompts.
- Work section by section: map events → inspect frames/dialogue → validate causality → request/record approval → continue.
- Never rerender merely to test wording. Regenerate text tracks only when timing and video clips are unchanged.
- Use the immersive-analytic default profile: short reviewer bridges, preserved movie dialogue, and selective interpretation.
- Build reviewer text with the versioned three-pass process in `preprocessing-workflow.md`; never improvise all narration in one batch.

- Target 19–25 minutes, normally 22 minutes.
- Structure: cold open → setup → incident → escalation → midpoint → rising danger → pre-resolution climax.
- End before the decisive solution, final reveal, survivor result, and aftermath.
- Parse the supplied SRT into dialogue events and remap each cue with `output_time = output_cut_start + source_caption_time - source_cut_start`.
- Keep most narration 2–5 seconds, 5–14 English words, and 12–32 Korean characters.
- Prefer declarative foreshadowing; avoid repeating the next movie line.
- Leave about 0.12 seconds before original dialogue resumes, then tune by playback.
- Produce separate movie, narration, and combined SRT files.
- Preserve `narration_v1/v2/v3` artifacts and merge the approved pass into one CapCut review track.
- For selected prerolls, generate one full-length `sfx_preroll_stem.m4a` at timeline zero plus an exact placement CSV and QA. Never import the stem and individual effects together.
- In CapCut, import only movie and narration SRTs as separate tracks. Use white lower captions for dialogue and larger warm-ivory captions slightly above for narration.
- Build the outro with the separate plan and gates in `outro-workflow.md`: 14–18 seconds, spoiler-safe visual, movie audio muted, short wrap-up, one CTA, music rise after speech, and synchronized fade-out.
