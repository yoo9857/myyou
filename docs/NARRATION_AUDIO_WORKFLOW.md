# Narration Audio Workflow

Last updated: 2026-08-12

This is the approved reusable voice and audio-mix workflow for movie-review projects.

## Approved voice profile

- Provider: ElevenLabs
- Voice: Nayva (`cfc7wVYq4gw4OpcEEAom`)
- Model: `eleven_v3`
- Language: neutral American English
- Delivery: restrained, intimate, and close-mic
- Baseline pace: `0.96`
- Default emotion tags: none
- Add an emotion tag only when a separately approved scene requires it. Do not tag every cue.
- Generate each line from the approved narration SRT without changing its wording or timing.
- Trim edge silence, then reject any line that requires more than `1.35x` speed to fit. Shorten the script instead.

The Constantine reference generator is:

```powershell
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable('ELEVENLABS_API_KEY','User')
python .\generate_constantine_nayva_v2_restrained.py
```

Required generation gates:

- cue count matches the review SRT
- `emotion_tags_used = 0` for the approved default profile
- `overrun_count = 0`
- no API key appears in manifests, logs, or Git

## Mix profile

The voice is deliberately quieter than the first Constantine mix:

- voice stem gain: `0.60`
- duck threshold: `0.018`
- duck ratio: `5:1`
- duck attack: `180 ms`
- duck release: `750 ms`

This keeps the film ambience audible and prevents the narrator from sounding oversized merely because the bed was over-ducked.

The approved outro music profile for `The Final Resolve.mp3` is:

- source offset: `15.0 s`
- gain under speech: `0.32`
- gain after the last spoken cue: `0.78`
- rise begins: `12.1 s` relative to the outro
- fade begins: `13.1 s` relative to the outro
- picture and music end together

The Constantine reference mix command is:

```powershell
python .\mix_constantine_nayva_v2_restrained.py
```

## Audio QA gates

- final video contains one video stream and one AAC stereo audio stream
- true peak is at or below `-0.8 dBFS`
- representative active narration is at least `4 dB` above the ducked bed
- target active narration margin is approximately `6-8 dB`
- outro music mean level is at least `-30 dB`
- outro music maximum level is at least `-12 dB`
- exactly one `REVIEW_VOICE` track and one `OUTRO_MUSIC` track exist
- exactly one movie-dialogue text track and one review-narration text track exist
- every CapCut timeline mirror is byte-identical after the update

Run:

```powershell
node .\audit_constantine_final_audio.mjs
```

The audit must report `audio_gate_pass: true`.

## CapCut replacement procedure

1. Close every CapCut process.
2. Back up the root draft, timeline mirrors, current voice/music assets, and current video bed.
3. Replace the voice and music audio assets with the newly mixed M4A stems.
4. Copy the new ducked bed under a versioned filename. Do not overwrite a media file still locked by Windows.
5. Update the root draft and every timeline mirror atomically to the versioned bed path.
6. Run the final audio audit and require identical mirrors.
7. Reopen CapCut only after QA passes.

Never modify or remove the source movie or original subtitle file.
