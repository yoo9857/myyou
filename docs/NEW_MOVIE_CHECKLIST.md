# 새 영화 시작 체크리스트

영화마다 새로 쓰는 것은 **두 개뿐**이다. 나머지는 전부 공용이다.

| 새로 쓰는 것 | 하는 일 |
|---|---|
| `<project>/build_story_map.py` | 사건, 인과, 구간, 결말 차단선 |
| `<project>/build_edit_plan.py` | 그룹 배분, 예산, 타일링 |

`verify_intervals.py`는 복사해서 쓰고, `config.json`은 값만 바꾼다.

## 순서

```
python scripts/copyright_probe.py <project>/config.json      # 차단 여부 먼저
python scripts/analyze_reference.py <video_id>               # 참고 영상이 있으면
python scripts/run_workflow.py <project>/config.json run     # 미리보기까지 무료
#   -> structure_preview.mp4 를 보고 순서를 확정
python scripts/run_workflow.py <project>/config.json approve structure
python scripts/run_workflow.py <project>/config.json run     # 대본·음성부터 끝까지
```

`run`은 유료 단계 앞에서 멈춘다. 승인은 편집표 지문에 묶여 있어 편집표가 바뀌면 자동으로
무효가 된다. 자세한 이유와 각 규칙의 근거는
`skills/edit-movie-review/references/cost-order.md`에 있다.

## config.json에서 반드시 확인할 값

| 키 | 이유 |
|---|---|
| `render_width` / `render_height` / `render_crf` / `render_preset` | 납품 게이트가 검사한다 |
| `source_audio_downmix` | 기본 5.1 다운믹스는 대사를 4.2dB 잃는다 |
| `min_duration_sec` / `max_duration_sec` | 없으면 19분 하한이 적용된다 |
| `narration_voice_gain` | 없으면 1.0으로 들어가 해설이 5dB 앞선다 |
| `narration_pass_directives` | 언어와 해설 밀도. 없으면 공용 프롬프트가 한국어로 덜어낸다 |
| `master_loudness_lufs` / `master_true_peak_dbtp` | 없으면 마스터링 자체를 건너뛴다 |
| `render_bake_sfx_preroll` | false면 효과음이 mp4에 안 들어간다 |
| `review_language` | 자막 길이 검사가 글자/단어 중 무엇으로 잴지 결정한다 |

## 검증 도구

| 명령 | 검사 내용 |
|---|---|
| `scripts/audit_project.py` | 사건 순서, 대사 경계, 음성 대응, 자막 범위, 차단선 — 24항목 |
| `scripts/delivery_gates.py` | 해상도, CRF, 라우드니스, 트루피크, 더킹 우위 |
| `scripts/measure_balance.py` | 구간별 해설 우위. 게이트가 이 결과를 읽는다 |
| `scripts/solve_duck.py` | 구간별 더킹을 실측으로 산출 |
| `<project>/verify_intervals.py` | 사건이 맞는 장면인지 프레임으로 확인 |

## 최종 산출물

| 파일 | 용도 |
|---|---|
| `output/<name>.mp4` | 마스터. 해설·효과음·음악 포함, 자막 없음 |
| `output/<name>_captioned.mp4` | 자막 구움. 그대로 업로드 가능 |
| `output/structure_preview.mp4` | 순서 확인용 저해상도 |
| `output/capcut_import/` | SRT 2종, 스타일 ASS, 타임라인, 개별 클립 |
| CapCut 초안 | `scripts/build_capcut_project.py`가 생성·등록 |
