# COLONY 영화 리뷰 프로젝트 상태

최종 갱신: 2026-08-13

## 사용자 프리롤 효과음 라이브러리 (2026-08-13)

- 원본 효과음 5개는 저장소 루트에 그대로 보존했다.
- 낮게 보정한 48kHz WAV 편집본은 `assets/sfx/narration_preroll/`에 저장했다.
- 편집본 피크는 약 `-15.6~-15.0 dBFS`이며 베이스는 파일명 의도대로 첫 0.7초만 사용한다.
- 용도: 선택된 오프닝·몰입 브리지에서 나레이션 시작 0.20~0.85초 전 프리롤.
- 대본 심사 JSON에 `sfx_preroll`, `sfx_lead_seconds`, `sfx_rationale`를 기록하고 편집표에는 `narration_sfx_*` 필드로 전달한다.
- 렌더러는 효과음 뒤에 나레이션 음성을 지연 배치하고, CapCut 인계본에는 별도 `sfx_timeline.csv`와 사용 자산을 패키징한다.
- 전체 최대 8회, 동일 효과음 최소 90초 간격, 모든 효과음 최소 25초 간격을 기본으로 한다.
- 강한 대사, 죽음, 슬픔, 고백, 발견·반전·공포 결산, 전투 장면은 보호 구간이다.
- 자동 게이트는 SRT 대사 충돌, 보호 상태, 0.10~0.30초 꼬리 겹침, 전체/개별 사용 제한과 간격을 검사한다.
- 자동 인계는 전체 길이 `sfx_preroll_stem.m4a`, 상세 CSV, 실제 피크·길이를 측정한 `SFX_PREROLL_QA.json`을 만든다.

## 승인 기반 지속 학습 워크플로 (2026-08-13)

- 참고 영상 원문은 분석 자료로만 보관하고 생성 프롬프트에는 넣지 않는다.
- 승인 규칙의 단일 원본: `work/references/learning_registry.json`
- 현재 승인 규칙 4개, 근거 참고 영상 2개이며 `scripts/validate_reference_learning.py` 검증을 통과한다.
- 대본 생성기는 승인 규칙만 읽고 각 지표 파일·영상 ID·측정 한계·근거 참조를 다시 검사한다.
- 새 규칙 승격 순서: 관찰 → 수치화 → 후보 → 미리보기 → 사용자 승인 → 승격 → 회귀검사.
- 나레이션 3개 연속은 편집표 검증에서 차단한다.
- `pipeline.py preflight`를 추가해 영화·SRT·스토리맵·편집표·학습 규칙·보이스 프로필을 렌더 전에 한 번에 검사하고 `WORKFLOW_PREFLIGHT_QA.json`을 남긴다.
- Constantine 현행 51개 세그먼트는 새 preflight를 실제 통과했다.
- SFX 충돌/꼬리/보호 장면과 연속 나레이션 회귀 테스트 5개가 통과했다.
- 전역 스킬과 저장소 번들 스킬은 스토리맵·3패스·학습·음성·아웃트로·자막·검증 스크립트와 자산까지 동일하게 동기화했다.

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
- CapCut 프로젝트 `CONSTANTINE_STORY_REVIEW_V5` 교체 완료 (2026-08-13 18:46)
  - 교체 스크립트: `swap_constantine_capcut_voice.py`
  - 음성 에셋: `constantine_nayva_voice_stem.m4a` → `constantine_selected_voice_stem.m4a`
  - 영상 에셋: `..._ducked_bed_v2.mp4` → `..._selected_voice_bed.mp4`
    (더킹은 나레이션을 사이드체인으로 받으므로, Nayva 베드를 두면 짧아진 새 대사 뒤에도 영화 음량이 눌린 채 남는다)
  - 신·구 에셋 길이가 동일해 CapCut이 기록한 `duration`과 모든 `timerange`는 손대지 않았다
  - 보존 확인: 프로젝트 길이 1501041666 us, 텍스트 소재 316개, 영화 자막 287개, 나레이션 29개, 트랙 구성 모두 그대로
  - 미러 4개 파일 해시 일치, 참조 에셋 3개 전부 실제 존재
  - 백업: `backups/capcut_selected_voice/20260813_184656` (프로젝트 문서만, assets 제외)
  - 프로젝트 `assets/`의 미참조 영상 3개(488MB)를 제거했다

## Constantine 1080p 복구 (해결)

- 상류 컷부터 다시 조립해 현재 선택 보이스 최종본과 SFX 최종본은 **1920×1080**이다.
- SFX 최종본: `Constantine/story_review_v5/output/constantine_story_review_v5_selected_voice_sfx_final.mp4`
- SFX 합성 단계는 H.264 영상 스트림을 비트 단위로 복사했으며 원본·출력 영상 스트림 SHA-256이 일치한다.

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

## Constantine narration pre-roll SFX V1 (2026-08-13)

- New final: `Constantine/story_review_v5/output/constantine_story_review_v5_selected_voice_sfx_final.mp4`
- Five low-level custom SFX were placed before narration cues 3, 11, 14, 20, and 28 after checking the picture and preceding movie captions.
- Uses: danger knife, bass omen, curiosity sting, neutral transition, and short whoosh; each asset is used once.
- No movie-dialogue overlap; effect tails overlap narration by only 0.155-0.279 seconds.
- SFX stem peak: -16.4 dBFS. Final audio peak: -1.4 dBFS. Duration remains 1501.021321 seconds.
- The H.264 video stream was copied bit-for-bit; source and output video-stream SHA-256 hashes match.
- CapCut handoff: `Constantine/story_review_v5/output/capcut_import/sfx_preroll_v1/`
- QA: `Constantine/story_review_v5/output/SFX_PREROLL_V1_QA.json`
- Existing final and CapCut project JSON were not modified.
