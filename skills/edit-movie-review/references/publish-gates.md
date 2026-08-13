# Publish gates

`quality-gates.md` covers whether the review is good. This file covers whether it can be
published at all, and whether the delivered files are technically sound. Both were learned
by shipping a finished 25-minute review that was blocked worldwide.

## Gate zero: does the rights holder allow this film

**Run this before writing a single line of script.**

A completed Constantine review was blocked in every country because Warner Bros. had set
`Constantine (2005) ASSET Full Movie Master` to block, and the claim covered 0:00–24:47 —
every frame that came from the film. No edit fixes that. Content ID matches a few seconds
as readily as an hour, so shortening clips changes nothing once the policy is block.

Rights holders choose **block / monetise / track** per asset. Reviews that stay up are
mostly built on films whose holders chose monetise. That is a property of the film, not of
the edit, and it costs one upload to find out.

```
ffmpeg -ss <any point> -t 60 -i "<source film>" -c:v libx264 -crf 20 -c:a aac probe.mp4
```

Upload `probe.mp4` as **private**, wait a few minutes, then read
Studio → the video → restrictions → claim details.

| Claim details say | Action |
|---|---|
| No claim | Proceed. |
| Claim, policy **monetise** or **track** | Proceed; revenue may go to the holder. |
| Claim, policy **block** | Pick another film. Do not start production. |

Read the **type** too. `저작권 - 시청각` means picture and sound both matched, so muting
will not help either.

Shorts are stricter, not looser. A Short over one minute is blocked by **any** active
claim regardless of policy; a sub-minute Short follows the policy. A blocked asset
therefore rules out Shorts as well.

## Disputing is usually the wrong move

A dispute is weak when the review looks like the one that got blocked: 20.5% of the film
used, the film's own audio running for 87.5% of the runtime, and original narration over
only 11%. Three of the four fair-use factors point the wrong way, and the downside is
asymmetric — a rejected dispute can escalate to a takedown, which is a copyright strike,
and three strikes end the channel. A Content ID claim by itself carries no strike.

If a dispute is still wanted, that is a question for a copyright lawyer, not for this
pipeline.

## Choosing a Short

A Short is not an excerpt. It needs a complete arc inside 60 seconds: a setup, a turn, and
a payoff. A slice lifted from the middle of a long review has none of those and gets
skipped however good the footage looks.

[A 53-second cut built around the strongest narration line still failed. The surrounding
footage was a character walking across a kitchen, so nothing happened and nothing
resolved.]

Pick the window by asking **what changes in it**, not by which line sounds best. If the
answer is "nothing, it is the middle of an explanation", it is not a Short.

Vertical framing: a 2.39:1 picture at full width is only 452 px tall in a 1920 frame, under
a quarter of the screen. `scripts/build_short.py` trades side crop for height via
`band_height`; 1080 px fills 56% of the screen and keeps 42% of the width. Use `crop_bias`
when the subject sits off-centre.

## Delivery gates (mechanical)

```
python scripts/delivery_gates.py <project>/delivery_gates.json
```

22 checks over render config, delivered video, audio balance and the CapCut project. Each
one exists because it was missed by hand at least once; the reasons are in the script's
comments. Exit code is 1 on any failure, so it can gate a publish step.

Notable ones:

- Render config at 1920×1080 or better, CRF ≤ 20, no `ultrafast`-class preset. A project
  shipped at 960×540 / CRF 30 because the preview config was never raised.
- `cropdetect` confirms the picture area, not just the frame size. A 540p picture padded to
  1080p passes a naive resolution check.
- Duration and frame count survive a re-render within 2 ms. Every caption is anchored to
  absolute time.
- Narration sits 0 to +4 dB above the film's own **dialogue**, sampled inside movie caption
  windows that do not overlap narration.
- Each narration line clears the film beneath it by at least 6 dB, with the duck depth
  solved per line. One fixed depth cannot serve a film ranging from −14 to −45 LUFS.
- The **sum** of the stems meets the peak ceiling, because CapCut adds tracks with no
  limiter of its own.
- A caption's declared font matches the file its path resolves to, and two tracks in
  different typefaces are matched on `x-height/em × size`, not on equal numbers.

## Two measurement traps

- A mono cue duplicated into both channels measures **+3.01 dB** louder than the mono file.
  EBU R128 sums channel energy. Leaving this out understated narration by 3 dB.
- Phase-inversion null tests cannot verify a voice replacement: `-ss` fast seek plus mp3
  decoder delay prevent sample-accurate alignment. Use lag-compensated normalised
  cross-correlation over ±600 ms instead — above 0.9 for the new render, below 0.2 for the
  old one. A uniform few-millisecond lag is AAC priming, not drift.
