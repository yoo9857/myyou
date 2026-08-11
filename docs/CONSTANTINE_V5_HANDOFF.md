# Constantine V5 Handoff

Last updated: 2026-08-12

## Approved deliverable

- Final review: `Constantine/story_review_v5/output/constantine_story_review_v5_nayva_final.mp4`
- CapCut import bundle: `Constantine/story_review_v5/output/capcut_import/`
- Final audio bundle: `Constantine/story_review_v5/output/capcut_import/final_audio_v2_restrained/`
- Final QA: `Constantine/story_review_v5/FINAL_QA.md`
- Audio QA JSON: `Constantine/story_review_v5/output/CAPCUT_FINAL_AUDIO_QA.json`

## Current audio decision

The approved narrator is Nayva using ElevenLabs `eleven_v3`. The production profile matches the approved sample:

- restrained and intimate delivery
- no per-cue emotion tags
- `0.96` baseline pace
- `0.60` final voice gain
- gradual `180 ms` attack / `750 ms` release ducking
- audible `The Final Resolve.mp3` outro music with a post-speech rise

See `docs/NARRATION_AUDIO_WORKFLOW.md` for reusable settings and gates.

## Rebuild commands

```powershell
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable('ELEVENLABS_API_KEY','User')
python .\generate_constantine_nayva_v2_restrained.py
python .\mix_constantine_nayva_v2_restrained.py
node .\apply_constantine_audio_capcut.mjs
node .\audit_constantine_final_audio.mjs
```

Close CapCut and create a backup before running the apply command.

## Verification state

- causal story map: valid and render-ready
- movie captions: `287`
- review narration cues: `29`
- narration collisions: `0`
- timing overruns: `0`
- outro plan: valid
- CapCut timeline mirrors: `3`, identical
- final audio gate: pass
- source movie and source subtitles: unchanged

CapCut was left closed after the final verified update.
