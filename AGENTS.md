# Project instructions

Read `docs/HANDOFF.md`, `docs/PROJECT_STATE.md`, and `docs/WORKFLOW.md` before changing the pipeline.

## One-line trigger

Treat `유튜브 영화 리뷰, [영화 파일명] 이걸로 만들어줘` and equivalent short requests as authorization to run the complete bundled workflow with its defaults. Do not ask the user to restate the established editing rules unless a required movie or subtitle file is missing.

Use the bundled `edit-movie-review` skill under `skills/edit-movie-review/` for movie-review work. Preserve these fixed rules:

- Target 19–25 minutes, normally about 22 minutes.
- Build through rising danger and pre-resolution climax; hide the final solution, survivor state, last reveal, and denouement.
- Reuse the supplied SRT and remap every cue from exact source/output cut offsets.
- Keep movie dialogue and reviewer narration in separate CapCut tracks and style presets.
- Ensure movie captions resume after every narration interval.
- Use short anticipation-building narration; do not recite the plot.
- For COLONY and future reviews using the approved house voice, load `voice_profiles/colony_original_normal.json`: Voice ID `Vuo6zmtjWmlDbzqgIDos`, `eleven_v3`, provider defaults, and the recorded post-processing chain. Never substitute Nayva or reuse an unverified cached MP3.
- Never print, commit, or embed API keys.
- Never commit API keys or the separately transferred source movie. Existing subtitles, generated media, analysis data, approved music, and CapCut handoff drafts are intentional project deliverables.

Preserve user media and existing outputs. Back up a CapCut project and close CapCut before modifying its JSON.
