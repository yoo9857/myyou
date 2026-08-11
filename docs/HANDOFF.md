# 다음 작업자 인계서

최종 인계일: 2026-08-11

## 먼저 할 일

```powershell
git clone https://github.com/yoo9857/myyou.git
cd myyou
powershell -ExecutionPolicy Bypass -File .\scripts\setup_tools.ps1
```

그다음 아래 문서를 순서대로 읽는다.

1. `docs/PROJECT_STATE.md`
2. `docs/WORKFLOW.md`
3. `docs/NARRATION_STYLE_GUIDE.md`
4. `docs/CAPCUT_SUBTITLE_DESIGN.md`

## Git에 포함된 것

- 영상 분석·편집·자막 재매핑 Python 코드
- 나레이션 심사 프롬프트와 JSON 스키마
- 영화 대사/나레이션 CapCut 스타일 JSON
- CapCut 자막 스타일 자동 적용 스크립트
- 재사용 가능한 Codex `edit-movie-review` 스킬
- CapCut CLI `0.18.0` 고정 버전에 적용할 로컬 패치
- 현재 프로젝트 상태와 품질 검증 규칙

## Git에 포함되지 않은 로컬 자산

이 저장소는 공개 저장소이므로 다음 파일은 별도로 안전하게 전달해야 한다.

- 사용 권한이 있는 영화 원본 MP4
- 원본 영화 SRT
- `The Final Resolve.mp3` 및 기타 라이선스 음원
- `output/`, `work/`, `backups/` 전체
- CapCut 프로젝트 `0811 (5)` 폴더
- ElevenLabs/OpenAI/GitHub API 키

COLONY 작업을 정확히 이어가려면 기존 PC에서 다음을 복사한다.

```text
C:\cineyoutube\COLONY.2026.1080p.FHD.H264.AAC-iMBC.mp4
C:\cineyoutube\COLONY.2026.1080p.FHD.H264.AAC-iMBC.srt
C:\cineyoutube\The Final Resolve.mp3
C:\cineyoutube\output\
C:\Users\<USER>\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0811 (5)\
```

새 영화로 시작한다면 영화 MP4와 해당 SRT만 준비하고 `config.json`의 파일명·스포일러 경계를 바꾼다.

## 현재 완료 상태

- 본편 V4: 약 19분 56.54초
- 결말·최종 해결 비공개 구조
- 영화 대사와 나레이션 자막 재매핑 완료
- CapCut `0811 (5)` 자막 중복/4.33초 밀림 수정 완료
- 영화 대사 304개와 나레이션 37개를 별도 트랙으로 구성
- 현대적 Noto Sans KR 자막 프리셋 적용
- 16.6초 Nayva + `The Final Resolve` 엔딩 아웃트로 제작
- V5 나레이션 후보 편집표는 생성됐지만 현재 본편 편집표로 확정 적용하지 않음

정확한 상태는 `docs/PROJECT_STATE.md`를 기준으로 판단한다.

## 환경

- Windows 10/11
- Python 3.11 권장(파이프라인은 표준 라이브러리 사용)
- FFmpeg/ffprobe
- Node.js 18 이상
- Codex CLI 로그인
- CapCut Desktop
- 선택: `ELEVENLABS_API_KEY` 사용자 환경 변수

## 보안

- 키를 채팅, JSON, 코드, 로그에 붙이지 않는다.
- `set_elevenlabs_key.ps1`로 사용자 환경 변수에만 저장한다.
- 공개 GitHub 이슈에 CapCut 프로젝트를 그대로 첨부하지 않는다.
- 영화 파일과 전체 자막은 Git LFS에도 올리지 않는다.
