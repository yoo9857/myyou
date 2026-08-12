COLONY V5 - APPROVED VOICE PROFILE / CINEMA CAPTIONS

1. Final rendered video
   output/rough_cut_v5_approved_voice_cinema_captions.mp4

2. Editable CapCut handoff
   - Video/audio base: output/rough_cut_v5_approved_voice_clean_audio.mp4
   - Movie dialogue: output/capcut_import/movie_captions.srt
   - Reviewer narration: output/capcut_import/narration.srt
   - Separate narration voice files: output/capcut_import/narration_audio/

3. Apply the two subtitle tracks separately.
   - MOVIE_DIALOGUE: styles/capcut/dialogue-cinema-v2.json
   - REVIEW_NARRATION: styles/capcut/narration-cinema-v2.json

4. Current cue counts
   - Movie dialogue: 320
   - Reviewer narration: 17

5. Do not import captions_combined.srt together with the two separate tracks;
   doing so would duplicate every subtitle.

6. The source-movie captions are suppressed only while reviewer narration is
   audible, then resume from the remapped source SRT.

7. Narration voice: voice profile colony-vuo-original-normal-v1
   (Vuo6zmtjWmlDbzqgIDos / eleven_v3 / voice defaults). All 17 clips share the
   same profile hash. See output/COLONY_APPROVED_VOICE_VIDEO_QA.json.

8. The previous render (output/rough_cut_v5_selected_voice_cinema_captions.mp4
   and output/rough_cut_v5_selected_voice.mp4) is kept for comparison.
