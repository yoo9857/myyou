# The Devil All The Time — 인계

작성 2026-08-14. 다음 세션은 이 문서부터 읽고 **"막힌 지점"** 으로 바로 가면 된다.

## 한 줄 요약

스토리맵과 편집표는 완성·검증됐지만, **사건 33개 중 12개의 영화 타임코드가 틀렸다.**
시각 검증에서 드러났고, 고치기 전에는 대본 작성으로 넘어갈 수 없다.

## 완료된 것

| 산출물 | 상태 |
|---|---|
| `devil/config.json` | 1080p / CRF 19 / 24fps / 5.1 센터 강조 다운믹스 / 영어 |
| `devil/story_map.v1.json` | 13구간 33사건, `story map valid` |
| `devil/output/edit_plan.json` | 121세그먼트 17.3분, `편집표 검증 통과` |
| `work/references/learning_registry.json` | 승인 규칙 11개, `approved_rules: 11` |
| `The.Devil.All.The.Time.2020.2160p/devil_english.srt` | mkv 내장 영어 자막 1,620개 추출 |
| `The.Devil.All.The.Time.2020.2160p/probe_devil.mp4` | 저작권 프로브 57.1초 — **검토 통과함** |

지표: 해설 점유율 38.4%, 해설 주기 18.2초, 원본 사용률 12.5%, 스포일러 차단선 7570초(126:10).

## 막힌 지점 — 사건 타임코드 검증

`devil/verify_intervals.py`가 사건마다 프레임을 뽑아 콘택트 시트 4장을 만든다.
결과 이미지는 `devil/work/interval_check/`에 있다.

### 확인 결과

**정확 (9개)** — 그대로 두면 된다.
`arvin_bullied` `lenora_groomed` `arvin_confronts_preacher` `preacher_dies`
`arvin_rides_with_carl` `woods_shootout` `arvin_understands_father`
`bodecker_calls_him_out` `standoff`

**틀림 (12개)** — 반드시 고쳐야 한다.

| 사건 | 현재 값 | 그 지점의 실제 화면 |
|---|---|---|
| `prayer_log_present` | 22.4~23.2분 | 차 안의 소년 |
| `crucified_soldier` | 4.0~5.0분 | 대낮의 거리 |
| `meets_charlotte` | 8.6~9.6분 | 어두운 실내의 얼굴 |
| `emma_matchmaking` | 10.0~10.8분 | 모자 쓴 여성 (샬롯일 가능성) |
| `charlotte_illness` | 27.6~28.6분 | 술집 카운터 |
| `jack_sacrifice` | 29.0~30.2분 | 어둠 속 소년 |
| `roy_meets_carl` | 45.4~46.8분 | 할머니와 아이들 |
| `lenora_and_arvin` | 42.4~43.4분 | 숲속의 남자 |
| `earskell_gives_pistol` | 48.4~49.6분 | 학교 앞 싸움 |
| `suicide_burial_refused` | 91.6~92.4분 | 아빈과 보안관 대면 |
| `closing_theme` | 31.2~32.6분 | 칼과 샌디의 차 안 |
| `closing_cast_hook` | 101.2~102.6분 | 바닥의 시신 |

**미확인 (11개)** — 그럴듯해 보이지만 확정 안 됨.
`roy_spider_sermon` `helen_chooses_roy` `willard_teaches_revenge` `roy_kills_helen`
`teagardin_arrives` `teagardin_sermon` `carl_method` `bodecker_corruption`
`lenora_pregnant` `lenora_dies` `bodecker_learns` `arvin_returns_home`

### 왜 틀렸나

자막은 **누가 말하는지**만 알려주고 **화면에 무엇이 있는지**는 알려주지 않는다.
이 영화의 핵심 장면 다수가 대사 없는 행동이다 — 개를 안고 언덕을 오르는 장면,
부엌에 쓰러진 사람, 십자가 앞의 기도. 대사 없는 구간은 자막으로 위치를 잡을 수 없다.

### 고치는 방법 (검증된 절차)

1. 영어 자막에서 그 장면 근처의 결정적 대사를 찾아 앵커를 잡는다.
   예) `"Destroy this cancer inside her, Lord."` → 1581.9초
2. 앵커 앞뒤를 20~30초 간격으로 프레임 추출해 실제 장면을 확인한다.
   `ffmpeg -ss <초> -i <mkv> -frames:v 1 -vf scale=480:-2 out.jpg`
   **레이블에 콜론을 쓰지 말 것.** `drawtext`의 옵션 구분자와 충돌해 필터가 깨진다.
   `3m20s` 형식을 쓴다.
3. 여러 장을 붙일 때는 `concat` 후 `tile`. `tile`에 입력을 여러 개 주면
   첫 장만 깔리고 나머지는 검게 남는다.

### 이미 확정된 정확한 위치

```
3m20s   십자가 클로즈업 (영화 자체의 오프닝)
3m35s   "Solomon Islands, SOUTH PACIFIC. 12 years earlier" 자막
3m50s   십자가를 지고 가는 병사
4m05s   불탄 언덕의 십자가          -> crucified_soldier
25m22s  "there's no way we can destroy that cancer"  -> charlotte_illness 앵커
26m40s  숲속의 윌러드와 아빈
27m00s  아들 머리에 손을 얹은 윌러드  -> prayer_log_present
28m40s  "God had a tendency of asking men to make sacrifices" -> jack_sacrifice 앵커
30m00s  묘지의 부자 (장례식)
49m00s  학교 앞 싸움                -> lenora_and_arvin
```

영화 자체가 **십자가 → "12년 전" 자막 → 되감기**로 열린다.
참고 영상의 콜드 오픈은 영화 구조를 그대로 따른 것이었다.

## 타임코드 수정 후 순서

1. `python devil/build_story_map.py` → `validate_story_map.py`로 검증
2. `python devil/build_edit_plan.py` → 편집표 재생성
3. 스토리맵을 렌더 준비 상태로 올린다:
   모든 구간 `status: approved`, `exit_answer`·`next_question` 채우기,
   `needs_visual_review: false`
4. `MOVIE_REVIEW_ROOT=devil python narration_pass.py generate` — `codex` CLI 필요
5. `pipeline.py render` → 음성 → 믹스 → 자막 → `scripts/delivery_gates.py`

## 참고 영상에서 배운 것 (승인 규칙 11개)

`work/references/learning_registry.json`에 근거·측정값·롤백 조건과 함께 있다.
핵심 수치는 같은 영화를 다룬 참고 영상 `rd5pF9Qj_C8`(서울극장, 18.1분)에서 나왔다.

| 규칙 | 요구 |
|---|---|
| `shorter_total_runtime` | 17~19분 |
| `reviewer_share_floor` | 해설 40% + 원음 10% |
| `narration_cycle_not_block_length` | 블록 6~7초, 주기 18초 |
| `phase_density_curve_confirmed` | 51.8 → 40.5 → 27.6 → 50.9% |
| `save_dialogue_for_confrontations` | 원음은 대결에 10블록·각 10초 |
| `ending_cut_at_the_draw` | 대면을 다 보여주고 결과 직전에 끊는다 |
| `closing_block_theme_then_cast` | 마지막 통짜 블록: 주제 → 해석 → 캐스팅 → 권유 |

참고 영상 측정에서 **한 번 틀렸다가 고친 것**: 자동 자막이 한국어 해설과 영화 영어
대사를 함께 전사하므로, 처음 읽은 54.2%는 해설 점유율이 아니었다. 한글/라틴 비율로
분리하니 해설 41.9% + 원음 10.2%였다. `scripts/analyze_reference.py`가 이제 자동으로
분리한다.

## 이 프로젝트에서 고친 파이프라인 결함

- `pipeline.py`에 19분 하한이 하드코딩돼 있었다(`max(1140.0, ...)`). 템플릿에 이미 있던
  `min_duration_sec`/`max_duration_sec`를 존중하도록 고쳤다. 미설정 프로젝트는 기존 동작 유지.
- `pipeline.py`에 `source_audio_downmix` 옵션을 추가했다. 기본 5.1→스테레오 다운믹스가
  센터(대사)를 3dB 줄여 실측 4.2dB 손실이 났다. 비워두면 기존 동작 그대로다.

## 콘스탄틴 (직전 프로젝트)

**전 세계 차단됨.** Warner Bros.가 `Constantine (2005) ASSET Full Movie Master`를
차단으로 설정했고 클레임이 0:00~24:47 전체를 덮는다. 이의 제기는 권하지 않는다 —
공정 이용 4요소 중 3개가 불리하고, 기각 시 저작권 경고로 이어진다.

작업물은 `samples/`에 8초 발췌로만 남아 있고 렌더는 로컬에만 있다.
`Constantine/story_review_v5/delivery_gates.json`으로 23/23 통과 상태.
