1. 상위 output 폴더의 devil_review_v1.mp4를 CapCut으로 가져옵니다.
2. movie_captions.srt와 narration.srt만 각각 별도 자막 트랙으로 가져옵니다. captions_combined.srt는 QA용이며 가져오지 않습니다.
3. narration_audio 폴더의 승인 음성을 REVIEW_NARRATION 오디오 트랙에 배치합니다. CapCut 임의 TTS로 대체하지 않습니다.
4. 나레이션이 끝나면 같은 클립 안에서 원음과 영화 자막이 자동으로 복귀합니다.
5. 프리롤 효과음이 선택된 경우 sfx_preroll/sfx_preroll_stem.m4a를 타임라인 0초에 SFX_PREROLL 별도 트랙으로 한 번만 가져옵니다.
6. render_bake_sfx_preroll=true로 렌더한 러프컷에는 효과음이 이미 포함되므로 별도 트랙을 중복 추가하지 않습니다.
7. 개별 WAV를 직접 배치할 때만 sfx_timeline.csv를 사용하며 스템과 동시에 쓰지 않습니다.
8. 필요하면 clips 폴더의 개별 원본 클립과 timeline.csv로 컷을 교체합니다.
