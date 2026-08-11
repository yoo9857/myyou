# Movie Review Auto Pipeline

Current approved narration and audio-mix rules: `docs/NARRATION_AUDIO_WORKFLOW.md`.

영화 원본, SRT, FFmpeg, 로그인된 Codex CLI를 이용해 19~25분 한국어 영화 리뷰의 분석 자료, 편집표, 러프컷, CapCut 가져오기 묶음을 생성합니다. 영화 원본과 API 키만 별도로 전달하며, SRT·음원·렌더·분석 자료·CapCut 인계본은 Git LFS를 포함한 이 저장소에서 받습니다.

현재 진행 상태와 확정된 편집 결정을 이어서 작업하려면 `docs/PROJECT_STATE.md`를 먼저 확인합니다. 다른 영화에 같은 방식을 적용할 때는 전역 Codex 스킬 `$edit-movie-review`를 사용합니다.

가장 간단한 실행 요청은 `유튜브 영화 리뷰, [영화 파일명] 이걸로 만들어줘`입니다. `AGENTS.md`가 나머지 기본 규칙을 자동 적용합니다.

새 PC에서는 먼저 다음을 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_tools.ps1
```

상세 인계 절차는 `docs/HANDOFF.md`를 확인합니다.

```powershell
python pipeline.py analyze
python pipeline.py plan
python narration_pass.py generate
python narration_pass.py apply --make-current
python pipeline.py render
# 이미 렌더된 컷에 기존 영화 SRT를 재매핑
python pipeline.py captions
# 또는
python pipeline.py all
```

주요 결과물:

- `work/analysis/`: 영상 정보, 스토리 패킷, 나레이션 가능 구간
- `work/contact_sheets/`: Codex가 확인할 대표 화면
- `output/edit_plan.json`: 구조화 편집표
- `output/narration_script_v5.json`: 컷을 건드리지 않는 나레이션 전용 심사·재작성 결과
- `output/narration_script_v5.md`: 한국어 자막과 Nayva 영어 TTS를 함께 검토하는 대본표
- `output/rough_cut.mp4`: 원음/음량 조절까지 적용한 자동 편집본
- 기존 `COLONY...srt`: 영화 이해와 원음 대사 타임코드 선택에만 사용
- `output/narration.srt`: CapCut TTS용 나레이션 문장과 배치 시간만 포함
- `output/narration.txt`: 나레이션 대본만 모은 텍스트
- `output/movie_captions.srt`: 기존 영화 SRT를 원음 컷의 새 타임라인으로 재매핑
- `output/captions_combined.srt`: 영화 대사와 나레이션을 합친 CapCut 표시용 자막
- `output/capcut_import/`: 개별 클립과 가져오기 안내

영화 전체 자막은 새로 만들지 않습니다. 기존 SRT를 선택된 원음 컷에 맞춰 재매핑합니다. 나레이션은 별도 V5 패스에서 짧게 다듬고, ElevenLabs Nayva 음성용 영어 TTS 문장도 함께 생성합니다. 전체 작업 기준은 `docs/WORKFLOW.md`를 참고합니다.
