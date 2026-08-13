# COLONY 영화 리뷰 프로젝트 상태

최종 갱신: 2026-08-13

## 확정된 방향

- 최종 리뷰 길이: 19~25분
- 흐름: 강한 전조 → 설정 → 사건 → 중반 전환 → 위기 상승 → 결말 직전 종료
- 결말 원칙: 최종 해결, 생존 결과, 마지막 반전과 후일담을 공개하지 않는다.
- 영화 대사 자막: 제공된 `COLONY.2026.1080p.FHD.H264.AAC-iMBC.srt`를 재사용한다.
- 나레이션: 길게 줄거리를 읽지 않고 흥미를 높이는 짧은 브리지로 제한한다.
- 현재 COLONY TTS 음성: 사용자 선택 Voice Library 보이스 (`Vuo6zmtjWmlDbzqgIDos`), `eleven_v3`, 보이스 원본 기본 설정
- 승인 음성 프로필: `voice_profiles/colony_original_normal.json`; 승인 샘플과 동일한 후처리 및 캐시 검증을 강제한다.
- 최종 수정: CapCut에서 영상, 분리 음원, SRT를 가져와 마무리한다.

## 현재 본편

- 최신 렌더: `output/rough_cut_v5_approved_voice_cinema_captions.mp4` (승인 프로필 음성 교체본, 2026-08-13)
- 직전 렌더: `output/rough_cut_v5_selected_voice_cinema_captions.mp4`
- 길이: 1196.533초(19분 56.533초)
- 최신 나레이션 심사본: `output/narration_script_v5.json` 및 `.md`
- V5 편집표를 현재 `output/edit_plan.json`에 적용했으며, 적용 전 파일은 `backups/colony_before_voice_caption_v2_20260812/`에 보존했다.
- V5에서 승인된 영어 나레이션 17개는 선택 보이스로 생성 완료: `output/capcut_import/narration_audio/`
- 음성 길이 검증: 17개 전부 각 대사의 `max_seconds` 이내, 초과 0개

## 자막 버그 방지

- 각 컷의 원본 시작점과 출력 시작점으로 모든 영화 자막 시간을 다시 계산한다.
- 나레이션 구간과 겹치는 영화 자막만 숨긴다.
- 나레이션이 끝난 뒤 다음 영화 대사와 자막은 반드시 이어져야 한다.
- 본편 처음, 중간, 후반을 실제 렌더 화면에서 표본 확인한다.

## CapCut 자막 디자인 적용

- 적용 프로젝트: `0811 (5)`
- 적용일: 2026-08-11
- 기존 상태: 동일한 통합 자막 341개가 두 트랙에 중복되고 두 번째 트랙이 약 4.33초 밀려 있었음
- 수정 결과: 중복 682개 제거 후 영화 대사 304개와 나레이션 37개를 별도 트랙으로 재구성
- 영화 대사 트랙: `MOVIE_DIALOGUE`, Noto Sans KR, `#F7F7F5`, 크기 5.0, `y=-0.80`
- 나레이션 트랙: `REVIEW_NARRATION`, Noto Sans KR, `#FFF0C2`, 크기 6.0, `y=-0.64`
- 두 트랙 모두 검정 외곽선과 부드러운 그림자 적용
- 검증: SRT 304+37개와 프로젝트 341개 일치, CapCut 타임라인 미러 불일치 없음, lint 오류 0개
- 최종 적용 직전 백업: `backups/capcut/0811 (5)-20260811-170630`
- 25초 디자인 미리보기: `output/capcut_caption_style_preview.mp4`
- 재적용 스크립트: `scripts/apply_capcut_caption_styles.ps1`

## 확정 아웃트로 V5

- 완성 영상: `output/outro_v5/colony_outro_v5.mp4`
- CapCut 인계본: `output/capcut_import/outro_v5/`
- 길이: 16.6초, 1920×1080, H.264/AAC
- 영화 원본 구간: `01:20:00.000–01:20:16.600`
- 영화 원음: 완전 음소거
- 음성: Nayva 영어 나레이션
- 음악: `The Final Resolve.mp3`의 15초 지점부터 사용
- 마지막 약 3초: 어두운 화면 위 `COLONY / LIKE + SUBSCRIBE / NEXT REVIEW SOON`
- 아웃트로는 독립 파일이며 본편 V4와 하나의 MP4로 합치지는 않았다. CapCut에서 본편 마지막에 붙인다.
- 선택 보이스 교체본: `output/outro_v5/colony_outro_v5_selected_voice.mp4`
- 선택 보이스 분리 음원: `output/outro_v5/outro_selected_voice_en.mp3`
- 기존 Nayva 아웃트로는 비교 및 복구용으로 보존한다.

## Constantine story_review_v5 음성 교체 (2026-08-13)

- COLONY와 **같은 승인 프로필**로 교체했다: `colony-vuo-original-normal-v1`, 해시 `95c8237…0715e`
- 최종 영상: `Constantine/story_review_v5/output/constantine_story_review_v5_selected_voice_final.mp4`
- 나레이션 29개 큐 전부 생성, max atempo 0.96, 슬롯 초과 0개
- 길이 1501.021321초로 Nayva 세대와 동일
- 믹스 상수(게인 0.60, 더킹, 리미터, 아웃트로 음악)를 그대로 유지해 목소리만 바뀌었다
- 검증: 29/29 검출(평균 상관도 0.967), 이전 Nayva 렌더에서는 0/29(0.067)
- QA 기록: `Constantine/story_review_v5/output/FINAL_SELECTED_VOICE_AUDIO_QA.json`
- **미완료**: CapCut 프로젝트 `CONSTANTINE_STORY_REVIEW_V5`는 아직 Nayva 스템을 참조한다.
  CapCut을 종료한 뒤 `assets/audio/`의 사본을 `constantine_selected_voice_stem.m4a`로 교체해야 한다.

## 레거시 정리 (2026-08-13)

- 폐기 미디어 약 4.24GB 삭제: 구 rough cut 3개, selected_voice 렌더 2개, Nayva 세대 스템·베드·최종본, 구 백업 2개, Nayva 나레이션 음원 2세트
- 폐기 스크립트 20개 삭제. 루트 스크립트가 33개에서 13개로 줄었다.
- 지우면 안 되는 파일과 실행 순서는 `docs/PIPELINE.md`에 고정했다.
- `edit_plan.json`을 덮어쓰던 구세대 변환기(`create_spoiler_safe_v3.py` 등)를 지웠다. 실수 실행으로 V5 편집표가 깨질 위험을 없앴다.
- 이미 푸시된 LFS 용량은 히스토리에 남아 회수되지 않는다. 로컬 캐시 정리는 하지 않았다.

## 재사용 장치

- 전역 Codex 스킬: `%USERPROFILE%\.codex\skills\edit-movie-review`
- 호출 예: `$edit-movie-review 이 영화와 SRT로 기존 방식의 리뷰를 만들어줘.`
- 상세 과정: `docs/WORKFLOW.md`
- 나레이션 기준: `docs/NARRATION_STYLE_GUIDE.md`

## 선택 보이스·시네마 자막 V5 완성본 (2026-08-12)

- 최종 영상: `output/rough_cut_v5_selected_voice_cinema_captions.mp4`
- 편집용 음성 교체본: `output/rough_cut_v5_selected_voice.mp4`
- 보이스: `Vuo6zmtjWmlDbzqgIDos`, `eleven_v3`, 공급자 기본 설정
- 길이: 1196.533초 (19분 56.533초), 1920×1080, H.264/AAC 48 kHz stereo
- 영화 대사 자막: 320개, 하단 흰색, 검은 외곽선, 배경 박스 없음
- 리뷰 나레이션 자막: 17개, 한 단 위 아이보리색, 배경 박스 없음
- 영화/나레이션 자막 시간 겹침: 0개
- QA 기록: `output/COLONY_SELECTED_VOICE_VIDEO_QA.json`
- CapCut 인계 안내: `output/capcut_import/IMPORT_README.txt`
- 기존 본편·기존 보이스·기존 아웃트로는 복구 및 비교용으로 보존한다.

## 승인 프로필 음성 교체 완성본 (2026-08-13)

- 최종 영상: `output/rough_cut_v5_approved_voice_cinema_captions.mp4`
- 음성 교체본(자막 없음 계열): `output/rough_cut_v5_approved_voice_clean_audio.mp4`
- 재생성 스크립트: `rebuild_colony_approved_voice.py`
- 보이스 프로필: `colony-vuo-original-normal-v1`, 해시 `95c8237230996ee8f2886670fdabc21fbc218c7e995080b83469faf9fd90715e`, 17개 전부 동일
- 나레이션 17개 길이: 전부 각 대사 `max_seconds` 이내, 초과 0개
- 길이: 1196.533초, 1920×1080, H.264/AAC 48 kHz stereo 192 kbps
- 영화 원음 처리: 나레이션 구간 0.20, 그 외 0.96, 최종 `alimiter=limit=0.891251`
- 이전 나레이션 구간 37개를 원본 영화 음원으로 되돌린 뒤 승인 음성 17개를 다시 얹었다.
- 자막은 직전 렌더에서 스트림 복사했으므로 영화 320개, 나레이션 17개, 겹침 0개가 그대로 유지된다.
- 측정: 나레이션 구간 음량이 직전 렌더보다 약 2 dB 낮다. 더 크게 원하면 스크립트의 나레이션 `volume=1.0`을 올린다.
- QA 기록: `output/COLONY_APPROVED_VOICE_VIDEO_QA.json`
- 주의: ffmpeg 9.0에서 `-filter_complex_script`가 제거되어 `-/filter_complex <파일>`을 쓴다. 2026-08-12 렌더 실패 원인이었다.
