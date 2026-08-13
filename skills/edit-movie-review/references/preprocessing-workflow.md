# Three-pass narration preprocessing

Use this sequence after the causal story map and edit timeline are approved. The passes are editorial roles, not separate CapCut tracks.

## Pass 1 — causal bridge

- Add only time, place, completed cause, current destination, or a demonstrated rule.
- Describe the visible action first; never announce the result of the current clip.
- Preserve discoveries, grief, reversals, jokes, and action payoffs as original movie audio.
- Save as `narration_v1.srt` with a QA report.

## Pass 2 — human reviewer voice

- Fill verified dialogue-free breathing gaps with situation, atmosphere, character subtext, or stakes.
- Keep the viewpoint inside the story. Avoid `관객`, `시청자`, `영화는`, `장면은`, and `연출은` unless the user explicitly requests essay-style meta analysis.
- Avoid a chain of formal `~입니다/~습니다` endings. Prefer connected spoken Korean such as `~했지만`, `~하는데`, `~이어지고`, `~였죠`, and `~인 셈이죠`.
- Make adjacent lines hand off a cause, question, or emotional residue instead of sounding like isolated facts.
- Keep each line speakable inside its verified gap; shorten wording before increasing speech speed.
- Save as `narration_v2.srt`; preserve V1.

## Pass 3 — dry comic relief

- Use only after tension has released and only in long dialogue-free gaps. Default to 2–6 beats in a 19–25 minute review.
- Use dry analogy or understatement rather than a detached joke: `수상할 정도로…`, `쓸모없는 취급받던…`, `~도 아니고…`, or an object/function comparison.
- Derive the joke from something already visible or established. Never foreshadow a reveal merely to land a joke.
- Do not place comedy over death, grief, confession, discovery, reversal, horror payoff, or active combat.
- Keep the joke short enough for natural TTS and let original ambience breathe before and after it.
- Save as `narration_v3.srt`; preserve V1 and V2.

## Final merge and validation

1. Merge all approved passes chronologically into one review SRT.
2. Keep exactly one movie-dialogue track and one `REVIEW_NARRATION` track in CapCut.
3. Require zero overlap between movie captions and review narration, including a 0.12-second resume margin.
4. Require zero time reversal, negative cue, cue past video end, meta-viewpoint leak, and unapproved formal-style hit.
5. Keep voice generation OFF while wording and flow are under review. Do not duck movie audio without a real voice file.
6. When TTS is approved, fit cue timing to measured audio duration and apply gradual duck attack/release.
7. Close CapCut, back up all draft JSON mirrors, atomically replace the single review track, then verify cue counts and mirror equality.

## Required artifacts

- `narration_v1.srt`, `narration_v2.srt`, `narration_v3.srt`
- final combined review SRT and separate movie-dialogue SRT
- per-pass QA JSON with cue counts, collisions, style hits, and protected-scene violations
- CapCut backup path and post-write track/mirror audit

If a later pass is rejected, roll back only the narration track from the preceding SRT; never rerender unchanged video clips.
