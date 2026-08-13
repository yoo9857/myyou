# 현재 파이프라인

최종 갱신: 2026-08-13

이 문서는 **지금 살아 있는 스크립트와 산출물만** 적는다. 폐기된 세대는 적지 않는다.
새 세대를 만들면 이 문서를 먼저 고치고, 대체된 스크립트와 산출물을 같은 커밋에서 지운다.

## 공용

| 파일 | 역할 |
|---|---|
| `pipeline.py` | SRT 파싱, 컷 렌더, 자막 재매핑, SFX 대사 충돌 검사, CapCut SFX 스템·QA 생성. |
| `narration_pass.py` | 3패스 대본 심사 결과를 생성·검증하고 승인 편집표에 적용한다. |
| `scripts/validate_reference_learning.py` | 참고 영상 학습 레지스트리의 근거·한계·승인·롤백 조건을 검사한다. |
| `work/references/learning_registry.json` | 대본 생성에 실제 투입되는 승인 참고 규칙의 단일 원본. |
| `voice_profiles/colony_original_normal.json` | 승인 보이스 프로필. COLONY와 Constantine이 **공유**한다. |
| `config.json` | `elevenlabs_voice_id`, `elevenlabs_voice_profile` 등 현행 설정. |

승인 보이스는 `Vuo6zmtjWmlDbzqgIDos` / `eleven_v3` / 공급자 기본 설정이며,
후처리는 `silenceremove` 두 번 + `loudnorm=I=-16.5:TP=-1.5:LRA=7`이다.
프로필 해시는 **정규화된 JSON**을 SHA256 한 값(`95c8237…0715e`)이고,
두 프로젝트의 매니페스트가 같은 값을 기록해야 한다.

새 대본 생성 전 `python scripts/validate_reference_learning.py work/references/learning_registry.json`을 통과해야 한다.
새 편집표는 나레이션 3개 연속, SFX와 영화 대사 충돌, 보호 장면 SFX, 0.10~0.30초를 벗어난 SFX 꼬리를 자동 거부한다.
렌더 직전 `python pipeline.py preflight`를 실행한다. `pipeline.py render`도 같은 사전 검증을 자동 실행하며 결과는 `output/WORKFLOW_PREFLIGHT_QA.json`에 남는다.

## COLONY

실행 순서:

1. `generate_narration_audio.py` — 승인 프로필로 나레이션 음원 생성 → `output/capcut_import/narration_audio/`
2. `build_colony_selected_voice_video.py` — 시네마 자막을 구워 넣는다 → `output/rough_cut_v5_selected_voice_cinema_captions.mp4`
3. `rebuild_colony_approved_voice.py` — 2번 결과의 영상 트랙을 그대로 복사하고 음성만 승인 프로필로 교체한다

**2번은 3번의 전제 조건이다.** 3번은 2번 산출물의 자막이 구워진 영상 트랙을 스트림 복사한다.
2번 산출물은 용량이 커서 보관하지 않으므로, 다시 만들려면 2번부터 실행한다.
파일이 없으면 3번이 안내 메시지와 함께 중단된다.

| 산출물 | 설명 |
|---|---|
| `output/rough_cut_v5_approved_voice_cinema_captions.mp4` | **최종본** |
| `output/rough_cut_v5_approved_voice_clean_audio.mp4` | CapCut 편집 베이스 |
| `output/rough_cut_v4_curiosity_hook.mp4` | 3번의 베이스 영상. 지우면 안 된다. |
| `backups/colony_before_voice_caption_v2_20260812/` | 3번이 이전 타임라인·SRT를 읽는다. 지우면 안 된다. |
| `output/COLONY_APPROVED_VOICE_VIDEO_QA.json` | 검증 기록 |

아웃트로는 `generate_colony_outro_selected_voice.py`가 만든다.
**주의**: 이 스크립트는 승인 프로필의 후처리를 적용하지 않아, 본편보다 음성이 1~3 dB 크다.
본편과 톤을 맞추려면 후처리를 붙여야 한다.

## Constantine story_review_v5

실행 순서:

1. `build_constantine_story_v5.py` — 편집표 → `edit_plan.json`, `story_map.v1.json`
2. `build_constantine_english_subtitles.py` — 영어 자막·나레이션 → `narration_v4_outro_en.srt`
3. `apply_constantine_english_capcut.py` — CapCut에 영어 자막 적용
4. `apply_constantine_outro_capcut.py` — 아웃트로 결합 → `constantine_story_review_v5_with_outro.mp4`
5. `generate_constantine_selected_voice.py` — 승인 프로필로 29개 큐 생성 → `narration_audio_selected_voice/`
6. `mix_constantine_selected_voice.py` — 음성 스템 → 더킹 베드 → 최종본
7. `apply_constantine_reference_narration_style.py` — CapCut 나레이션 자막 스타일 적용
8. `swap_constantine_capcut_voice.py` — CapCut 프로젝트의 음성·베드 에셋을 교체한다.
   CapCut이 켜져 있으면 거부하고, 프로젝트 문서만 백업한 뒤, 길이·타임레인지·자막·트랙이
   그대로인지 지문 대조로 확인한다. `--dry-run`은 임시 복사본으로만 돌린다.

| 산출물 | 설명 |
|---|---|
| `constantine_story_review_v5_selected_voice_final.mp4` | **최종본** |
| `constantine_story_review_v5_selected_voice_bed.mp4` | 더킹된 영화 베드 |
| `constantine_selected_voice_stem.wav` / `.m4a` | 나레이션 스템. CapCut 교체용은 `.m4a`. |
| `constantine_story_review_v5_voice_off.mp4` | 4번의 원본. `work/outro_concat.txt`가 참조한다. 지우면 안 된다. |
| `constantine_story_review_v5_with_outro.mp4` | 6번의 소스. 지우면 안 된다. |
| `constantine_outro_music_stem.wav` / `.m4a` | 아웃트로 음악. 목소리와 무관해 재생성하지 않는다. |
| `FINAL_SELECTED_VOICE_AUDIO_QA.json` | 검증 기록 |
| `constantine_story_review_v5_selected_voice_sfx_final.mp4` | 1080p 선택 보이스 + 상황별 프리롤 SFX 최종본 |
| `capcut_import/sfx_preroll_v1/constantine_sfx_preroll_stem.m4a` | CapCut 타임라인 0초용 SFX 단일 스템 |
| `SFX_PREROLL_V1_QA.json` | 5개 배치, 대사 겹침, 음량, 영상 스트림 보존 검증 |

6번의 믹스 상수는 Nayva 세대와 동일하게 유지한다: 음성 게인 0.60,
더킹 threshold 0.018 / ratio 5 / attack 180 ms / release 750 ms, 리미터 0.88,
아웃트로 시작 1487.0초, 전체 길이 1501.021321초.

## CapCut 주의사항

- CapCut은 원본을 참조하지 않고 **프로젝트 폴더 안 `assets/`에 자체 사본**을 만든다.
  `output/` 아래 파일만 새로 만들어도 프로젝트에는 반영되지 않는다. `assets/` 사본을 교체해야 한다.
- 프로젝트 파일을 고치기 전에 **CapCut을 완전히 종료**한다. 실행 중에 고치면 편집 내용이 날아간다.
- `draft_content.json`은 `template-2.tmp`와 `Timelines/<id>/` 하위에 미러가 있다.
  네 파일의 해시가 일치해야 한다.

## 음성 교체 검증 방법

렌더에 새 음성이 실제로 들어갔는지는 위상 반전 널 테스트로 확인할 수 없다.
`-ss` 탐색 오차와 mp3 디코더 지연 때문에 결과가 무의미해진다.
대신 양쪽 렌더를 16 kHz 모노로 디코딩한 뒤, 각 음원을 ±600 ms 범위에서
지연 보정 정규화 상호상관으로 대조한다. 새 렌더는 0.9 이상, 이전 렌더는 0.2 이하가 나와야 한다.
