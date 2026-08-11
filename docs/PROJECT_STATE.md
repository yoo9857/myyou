# COLONY 영화 리뷰 프로젝트 상태

최종 갱신: 2026-08-11

## 확정된 방향

- 최종 리뷰 길이: 19~25분
- 흐름: 강한 전조 → 설정 → 사건 → 중반 전환 → 위기 상승 → 결말 직전 종료
- 결말 원칙: 최종 해결, 생존 결과, 마지막 반전과 후일담을 공개하지 않는다.
- 영화 대사 자막: 제공된 `COLONY.2026.1080p.FHD.H264.AAC-iMBC.srt`를 재사용한다.
- 나레이션: 길게 줄거리를 읽지 않고 흥미를 높이는 짧은 브리지로 제한한다.
- TTS 기본 음성: ElevenLabs Nayva (`cfc7wVYq4gw4OpcEEAom`), `eleven_v3`, 영어 여성 음성
- 최종 수정: CapCut에서 영상, 분리 음원, SRT를 가져와 마무리한다.

## 현재 본편

- 최신 렌더: `output/rough_cut_v4_curiosity_hook.mp4`
- 길이: 약 1196.54초(19분 56.54초)
- 최신 나레이션 심사본: `output/narration_script_v5.json` 및 `.md`
- V5 적용 후보 편집표: `output/edit_plan_v5_narration.json`
- 주의: V5 후보 편집표는 현재 `output/edit_plan.json`과 다르며 아직 현재 편집표로 적용되지 않았다.
- V5 적용 전에는 `python narration_pass.py apply --make-current`의 실제 지원 여부와 결과를 확인하고, 원본 편집표를 보존한다.

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

## 재사용 장치

- 전역 Codex 스킬: `%USERPROFILE%\.codex\skills\edit-movie-review`
- 호출 예: `$edit-movie-review 이 영화와 SRT로 기존 방식의 리뷰를 만들어줘.`
- 상세 과정: `docs/WORKFLOW.md`
- 나레이션 기준: `docs/NARRATION_STYLE_GUIDE.md`
