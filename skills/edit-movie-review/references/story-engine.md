# Causal story engine

## Core model

Model each film as ordered sections containing event nodes. Each node records:

- `id`, `source_start`, `source_end`, and `summary`
- `cause_ids`: earlier events required to understand it
- `characters`, `visible_action`, and `emotional_stake`
- `question_opened` and `question_answered`
- `reveal_time`: earliest source time when narration may state the result
- `must_show`: true when narration cannot replace the scene
- `narration_role`: `none`, `orient`, `causal_bridge`, `rule_clarify`, `character_subtext`, `stakes`, or `reflection`
- `narration_start_time` and `narration_evidence_time`: when narration starts and the latest source fact it depends on

## Narration rules

Use a two-layer sentence only when both layers are already supported:

1. Describe the visible action or completed cause.
2. Add its already-established meaning for character, rules, or stakes.

Require `narration_start_time >= narration_evidence_time`. Never state a later action, discovery, death, identity, decision, or outcome before `reveal_time`, even when it occurs later in the same clip. Do not repeat the next movie line. Preserve strong discoveries, grief, confrontations, jokes, and reversals as original movie audio.

## Section algorithm

For each section:

1. Identify the audience question entering the section.
2. List the minimum events needed to answer it.
3. Identify the character emotion that makes the events matter.
4. Mark each event as `must_show` or compressible.
5. Select chronological source intervals for every `must_show` event.
6. Add narration only where time, place, causality, rules, or subtext remain unclear.
7. End on an answer that opens the next, larger question.
8. Validate the section, then mark it `approved` before designing the next section.

## Default editorial profile

Use an immersive-analytic hybrid unless the user selects another profile:

- Let original scenes carry emotion and surprise.
- Use short narration clusters at transitions, not scattered commentary over every shot.
- Interpret motives and themes only after the supporting action or dialogue appears.
- Vary shot length by dramatic function; never sample the movie at fixed intervals.
- Treat reference-channel metrics as diagnostics, not targets to copy.

## Exceptions

- Missing or unusable subtitles: stop story timing, report `SUBTITLE_UNUSABLE`, and request a replacement or explicit transcription approval.
- Ambiguous visual event: mark `needs_visual_review`; do not infer a result from subtitles alone.
- Nonlinear film: preserve audience reveal order rather than fictional chronology and record `timeline_mode: audience_reveal`.
- Montage or dream: group shots under one event and label the reality level.
- Mystery or twist: set `reveal_time` and `spoiler_class`; block narration until permitted.
- Musical or dialogue-free sequence: use visual and audio landmarks; do not force narration.
- Conflicting runtime target: keep required causal events and report the minimum viable duration instead of deleting causes.
- CapCut or render drift: stop export, preserve the project, and rebuild timing from encoded clip durations.

## Maintenance

- Version story maps with `schema_version`.
- Keep genre profiles and channel observations in references, separate from core rules.
- Add a regression fixture whenever a real failure is found: missing cause, future leak, dialogue cut, or spoiler leak.
- Require validator success before render and compare SRT cue counts with CapCut track counts afterward.
