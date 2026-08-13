# Samples

The renders themselves are not in this repository. They run to several gigabytes per film,
they are rebuilt from the scripts and the source media, and one of them is blocked
worldwide anyway. These four files stand in for them so the pipeline's output can be
judged without carrying it.

| File | What it shows |
|---|---|
| `constantine_final_sample_8s.mp4` | 1080p master, taken from a narration window. Picture area is 1920×804 inside the frame, and the film ducks under the narrator by the amount solved for that line. |
| `constantine_short_sample_8s.mp4` | Vertical 1080×1920 build: film as a 1080 px band, blurred blow-up filling the rest, captions burned in as ASS. |
| `narration_cue_014_sample.mp3` | One raw narration cue from the approved voice profile `colony-vuo-original-normal-v1`, before slot fitting. |
| `constantine_thumbnail_1280x720.jpg` | Thumbnail frame at 1:46:19 of the source, cropped from 2.39:1 to 16:9 with space kept clear on the left for a title. |

Rebuild the full set with `docs/PIPELINE.md`. The mechanical checks are
`scripts/delivery_gates.py`, and the reasons behind each threshold are in
`skills/edit-movie-review/references/publish-gates.md`.

Constantine itself is a dead end for publishing: Warner Bros. set the film's Content ID
asset to block, so the finished review is blocked in every country. It survives here as a
worked example of the pipeline, not as a deliverable.
