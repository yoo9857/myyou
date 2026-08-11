# Constantine YouTube Review - CapCut Handoff

## Main deliverable

- `../constantine_review_rough_cut.mp4` - 22:02.821, 1920x1080 H.264/AAC
- `edit_plan.json` - 61 source clips and exact source ranges
- `timeline.csv` - encoded clip timeline and source/output offsets
- `clips/` - 61 individually editable rendered clips
- `narration_audio/` - 5 ElevenLabs Nayva narration assets

## Subtitle tracks

Import exactly these two SRT files as separate text tracks:

1. `movie_captions.srt` -> track name `MOVIE_DIALOGUE`
   - warm white `#F7F7F5`
   - font size 5.0
   - position y=-0.80
2. `narration.srt` -> track name `REVIEW_NARRATION`
   - warm ivory `#FFF0C2`
   - font size 6.0
   - position y=-0.64

Do not import `captions_combined.srt` into the same project. It is a viewing/reference export only and would duplicate both subtitle tracks.

## Verified counts

- Movie dialogue cues: 166
- Narration cues: 5
- Combined reference cues: 171
- Caption/narration collisions: 0
- Cues outside their owning clip: 0

The cut ends before the decisive solution, final reveal, survivor outcome, and aftermath.
