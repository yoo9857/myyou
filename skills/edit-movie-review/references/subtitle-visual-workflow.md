# Reference-driven mobile subtitle workflow

Use `assets/subtitle-style/user-reference-mobile-v5.json` as the default visual contract unless the user explicitly replaces it.

## Procedure

1. Preserve source media, SRT files, edit plans, and existing outputs.
2. Close CapCut and back up the root and nested live timeline JSON files with a timestamp.
3. Keep exactly two text tracks: `MOVIE_DIALOGUE` and `REVIEW_NARRATION`.
4. Use the requested supplied or embedded subtitle language. Strip markup, remap through exact clip offsets, suppress only narration collisions, and resume dialogue afterward.
5. Classify every review cue by narrative function, never by hard-coded cue number:
   - `main`: hook, punchline, dry comparison, or decisive summary.
   - `name`: character introduction, destination, reveal, or named-subject emphasis.
   - `situation`: causal bridge, mood, rule, discovery, danger, or reflective context.
6. Apply one profile to a preview cue from dialogue and each review role when the visual treatment is not already approved.
7. Apply the approved profile without changing narration wording, timing, video, or audio.
8. Synchronize every live CapCut timeline mirror, validate, and only then reopen CapCut.

## Approved mobile V5 visual system

- Dialogue: Pretendard Medium, off-white, soft separation, lower safe area, 4.25–5.15 size, no animation.
- Main review: Archivo Black, large white display text, compact tracking, strong black separation, 5.5–6.7 size.
- Name review: Roboto Condensed Bold Italic, pale-pink base, exact named span in red, up to 7.0 size.
- Situation review: Cormorant Garamond Medium, white editorial serif, exact phrase span in pale yellow, 5.0–6.0 size.
- Reference images are authoritative. Preserve their three visual roles; do not flatten all narration into one font family.
- Explicitly set top-level `font_name`, `font_path`, `font_size`, `bold`, `italic`, `underline`, and `has_border` on every material. Also write matching rich-text styles for every full range. This prevents only the accent span from receiving the intended style.
- Prefer installed static TTF files. If only a variable font exists, instantiate the required weight before CapCut import and retain its license.

## Rich text, lines, and safe area

- Write CapCut rich-text ranges as direct character indices for the installed CapCut schema. Do not convert them to UTF-16 byte offsets.
- Highlight only the matched token or phrase and confirm the base style resumes at its exact end index.
- Normalize whitespace and use balanced grammatical line breaks. Avoid orphaned articles, prepositions, names, and punctuation.
- Keep dialogue width at or below 0.78 and review width between 0.71 and 0.74.
- Disable fixed width and height, enable canvas adaptation, and use adaptive size for long cues.
- Treat mobile legibility as the default. Do not reduce the V5 size scale unless playback shows a safe-area failure.

## Motion contract

- Movie dialogue stays static.
- Review cues use only a 150–190 ms fade-in, a 0.012-position micro-rise settling within 220 ms, and a 150 ms fade-out. The final cue may fade out over 240 ms.
- Do not use glitch, typewriter, pop-up, bounce, blur, wipe, or karaoke effects unless explicitly requested.

## Validation gates

- CapCut lint: zero errors and zero warnings.
- Narration validator: zero collisions.
- SRT cue counts equal the two CapCut track segment counts.
- No unwanted language remnants or markup.
- No missing font file, oversized material, or movie-dialogue animation reference.
- Every review material has explicit top-level bold and italic boolean flags.
- All live timeline mirror hashes match.
- Manually inspect at least one cue from each role, including an exact-span name highlight.

Store the profile, reference images, fonts, licenses, QA report, final audit, and rollback backup with the handoff.
