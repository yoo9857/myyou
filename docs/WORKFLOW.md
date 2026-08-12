# COLONY 영화 리뷰 자동 제작 과정

## 목표

- 최종 길이: 19~25분, 기본 목표 22분
- 구성: 강한 전조 → 설정 → 사건 → 상승 → 중반 전환 → 후반 위기 → 클라이맥스 직전 종료
- 결말 정책: 최종 정체, 제거 결과, 생존 결과는 공개하지 않는다.
- 편집 리듬: 짧은 나레이션과 영화 원음 대사를 교차한다.
- 최종 편집: 자동 러프컷과 SRT를 만든 뒤 CapCut에서 마무리한다.

## 입력

- 영화 원본 MP4
- 영화에 포함된 기존 SRT
- `config.json`
- 로그인된 Codex CLI
- ElevenLabs Starter API 키(Windows 사용자 환경 변수 `ELEVENLABS_API_KEY`)

비밀키는 문서, 코드, JSON, 채팅에 기록하지 않는다. ElevenLabs 키는 실제 Secret Key인 `sk_...` 형식만 사용한다.

## 전체 흐름

1. `python pipeline.py analyze`
   - 영상 길이와 스트림 정보를 확인한다.
   - 기존 SRT를 3분 단위 사건 패킷으로 나눈다.
   - 나레이션을 넣을 수 있는 대사 공백과 대표 화면을 만든다.
2. `python pipeline.py plan`
   - 이야기 지도와 19~25분 편집표를 만든다.
   - 이 단계에서는 컷, 원음 보존 여부, 스토리 비트만 우선 결정한다.
3. `python narration_pass.py generate`
   - 기존 편집표의 컷을 변경하지 않고 나레이션만 별도로 심사한다.
   - 필요 없는 해설은 삭제하고, 필요한 문장은 2~5초 길이로 다시 쓴다.
   - 한국어 표시 문장과 Nayva용 영어 TTS 문장을 함께 생성한다.
4. `python narration_pass.py apply`
   - 검증된 나레이션을 `output/edit_plan.json`에 적용한다.
5. `python pipeline.py render`
   - FFmpeg로 클립, 러프컷, 원음 덕킹, 타임라인을 만든다.
6. ElevenLabs TTS
   - 모델: `eleven_v3`
   - 승인 프로필: `voice_profiles/colony_original_normal.json`
   - Voice ID: `Vuo6zmtjWmlDbzqgIDos`
   - 보이스 설정: 공급자 기본값(별도 안정성·스타일·속도 지시 금지)
   - 출력: 승인 샘플과 같은 무음 제거·음량 보정 후 48kHz mono 192kbps MP3
   - 전체 생성 전 한 줄을 먼저 승인받고, 문장이 같은 승인 샘플은 재생성하지 않고 그대로 복사한다.
   - manifest의 문장과 음성 프로필 SHA-256이 일치하지 않는 기존 MP3는 재사용하지 않는다.
7. CapCut
   - 러프컷, 영화 자막, 나레이션 오디오/자막을 가져온다.
   - 효과, 음악, 자막 디자인, 미세 컷 조정을 마무리한다.
   - 영화 대사는 `dialogue-modern.json`, 나레이션은 `narration-modern.json`을 사용해 별도 트랙으로 가져온다.
   - 통합 SRT는 검토용으로만 유지하고 CapCut에 중복으로 가져오지 않는다.
8. 엔딩 아웃트로
   - 스포일러 컷이 아닌 통쾌한 액션 장면을 16.6초 사용한다.
   - 영화 원음은 완전히 음소거하고 Nayva 나레이션과 크레딧 음악만 사용한다.
   - 크레딧 음악은 `The Final Resolve.mp3`의 15초 지점부터 사용한다.
   - 마지막 약 3초는 화면을 어둡게 하고 `LIKE + SUBSCRIBE` 카드를 표시한다.
   - CapCut에서는 `output/capcut_import/outro_v5/colony_outro_v5.mp4`를 본편 끝에 배치하고 한국어 SRT를 가져온다.

## 나레이션 품질 기준

- 첫 문장은 화면과 즉시 연결되는 전조 한 줄만 사용한다.
- 설명보다 `상황 규정 → 다음 위험 암시 → 원음 대사` 순서를 우선한다.
- 한 번에 한 가지 정보만 전달한다.
- 같은 사건을 영화 대사가 곧 말한다면 나레이션에서 먼저 설명하지 않는다.
- 질문은 영상 전체에서 최대 두 번만 사용한다.
- `결국`, `마침내`처럼 결과를 미리 확정하는 표현은 바로 화면에 나타날 때만 쓴다.
- 나레이션 뒤 0.12초 후 기존 영화 자막과 원음이 복귀한다.
- 강한 액션, 감정 대사, 반전 공개 장면은 나레이션 없이 둔다.

## 생성물

- `work/analysis/`: 이야기 지도와 분석 데이터
- `output/edit_plan.json`: 현재 적용 편집표
- `output/narration_script_v5.json`: 구조화된 나레이션 심사 결과
- `output/narration_script_v5.md`: 사람이 검토하기 쉬운 대본표
- `output/edit_plan_v5_narration.json`: 개선 나레이션이 적용된 편집표
- `output/rough_cut_*.mp4`: 자동 편집본
- `output/capcut_import/`: CapCut 인계 묶음
- `output/capcut_import/outro_v5/`: 최종 엔딩 영상, 한국어 자막, Nayva 음성, 대본

## 다른 영화에 재사용

- 사용자 전역 Codex 스킬: `%USERPROFILE%\.codex\skills\edit-movie-review`
- 새 영화 리뷰 요청 시 `$edit-movie-review`를 사용하면 이 프로젝트에서 확정한 전체 흐름과 품질 기준을 다시 불러온다.
- 영화별로 바꾸는 값은 원본 파일, SRT, 스포일러 경계, 장면 선택, 대본, 제목뿐이다.
- 19~25분 구성, 결말 보호, 승인 프로필 기반의 짧은 나레이션, 정확한 자막 재매핑, CapCut 인계, 짧은 엔딩 구조는 기본값으로 유지한다.

## 보안 및 운영

- API 키를 출력하거나 파일에 하드코딩하지 않는다.
- Voice Library 음성은 계정의 My Voices에 저장한다.
- 공개 라이브러리 음성은 제공자가 제거할 수 있으므로 notice period를 확인한다.
- 외부 참고 영상은 문장을 복제하지 않고 편집 리듬과 구조만 추출한다.
