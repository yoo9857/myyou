---
name: edit-movie-review
description: Design, build, or improve reusable 19–25 minute YouTube movie reviews from a movie file and subtitle file, including causal story mapping, omission and future-leak detection, three-pass human reviewer narration, reference-driven mobile subtitle typography and motion, dry comic relief, spoiler-safe outros, scene selection, subtitle retiming, voiceover, FFmpeg assembly, and CapCut handoff. Use for requests to analyze, structure, cut, narrate, preprocess, review, style subtitles, add an outro, repair, validate, or package any movie-review video or improve the shared movie-review algorithm.
---

# Edit Movie Review

Read `references/cost-order.md` first, before any other file, and follow the phase order it sets. The narration script and the voice are the only steps that cost money per run, and everything that decides whether they will be worth paying for is free and repeatable. Run `scripts/run_workflow.py <project>/config.json run`, which stops before the paid phases until a person has watched the structure preview and approved it; approval is bound to a fingerprint of the edit plan, so changing the plan withdraws it.

Read `references/workflow.md` before planning or rendering and `references/quality-gates.md` before subtitle, audio, or CapCut work.
Read `references/preprocessing-workflow.md` before writing, expanding, voicing, or applying reviewer narration.
Read `references/learning-loop.md` before extracting or promoting rules from a reference video.
Read `references/outro-workflow.md` before selecting, writing, rendering, or applying an outro.
Read `references/subtitle-visual-workflow.md` before designing, importing, restyling, animating, or validating subtitles in CapCut. Treat supplied reference images as authoritative; do not replace their visual language with an unsolicited generic trend treatment.

1. Locate the movie, supplied SRT, configuration, prior outputs, and selected music. Preserve originals.
2. Read `references/story-engine.md` and build a versioned causal story map before selecting clips.
3. When the user requests premium or SSS-style storytelling, read `references/reviewer-patterns.md` and select a profile without copying wording.
4. Use the supplied SRT; do not transcribe again unless it is missing or unusable.
5. Build an audio-first dialogue/silence map, then visually inspect every required causal event.
6. Design and approve one story section at a time. Do not render while any section is draft or any required event is missing.
7. Plan a 19–25 minute arc through the pre-resolution climax. Hide the final solution, survivor state, final reveal, and denouement.
8. Build narration in three versioned passes: causal bridges, human connective review, then sparse dry comic relief. Merge them into one review track and reject future-result narration.
9. Run `scripts/validate_story_map.py STORY_MAP --require-render-ready` before creating an edit plan or rendering.
10. Rebuild captions from exact source/output offsets. Suppress only cues overlapping narration and resume movie captions afterward.
11. Keep movie dialogue and narration in separate CapCut tracks with separate JSON style presets. Never import the combined SRT as a third duplicate track.
12. Back up the CapCut project and close CapCut before modifying JSON.
13. Package editable media, SRTs, timeline/edit plan, validation reports, and import instructions under `output/capcut_import/`.
14. Run `scripts/validate_narration_track.py` on the final movie-dialogue and review SRTs before CapCut or TTS.
15. Build the outro as a separate versioned plan, validate it with `scripts/validate_outro_plan.py`, then append its review cues to the single narration track.
16. Apply subtitle styling from `assets/subtitle-style/user-reference-mobile-v5.json`, adapting only for language support and safe-area fit. Preview one representative cue per role before a full-project rewrite when visual approval is not already established.
17. For selected narration prerolls, require a dialogue-free source window, a 0.10–0.30 second quiet tail under speech, protected-scene clearance, spacing/usage limits, and one separate full-length CapCut SFX stem with QA.
18. Never place narration without consulting the subtitle track: blocks slide into the quietest window they can reach, and clip boundaries never cut across a spoken line.
19. Verify every event by frame before trusting its timecode. A subtitle says who speaks, not what is on screen, and silent beats land minutes from where their dialogue does.
20. Check the measuring tool before believing a surprising measurement. `-filter:a` and `-af` are the same option, so passing a chain as one and a meter as the other silently drops the chain.
21. Keep the preview honest. If it does not duck, suppress captions and time from encoded clip lengths the way the deliverable does, it will show faults the review does not have and hide the ones it does.
22. Generate the handoff text from what the render actually produced. Telling an editor to lay narration on a track doubles it when the master already carries the voice.

Inspect the latest state before rerunning expensive work. Change only the requested line, voice, subtitle, or outro element when possible. Never print or commit API keys or copyrighted source media.
