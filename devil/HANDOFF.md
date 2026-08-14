# The Devil All The Time — 인계

갱신 2026-08-14. **타임코드 문제는 해결됐다.** 다음은 대본 작성부터 시작하면 된다.

## 상태

| 산출물 | 상태 |
|---|---|
| `devil/config.json` | 1080p / CRF 19 / 24fps / 5.1 센터 강조 다운믹스 / 영어 |
| `devil/story_map.v1.json` | 13구간 33사건, **`story map valid` (렌더 준비 통과)** |
| `devil/output/edit_plan.json` | 133세그먼트 18.0분, **편집표 검증 통과** |
| `work/references/learning_registry.json` | 승인 규칙 11개 |
| `The.Devil.All.The.Time.2020.2160p/devil_english.srt` | mkv 내장 영어 자막 1,620개 |
| `The.Devil.All.The.Time.2020.2160p/probe_devil.mp4` | 저작권 프로브 — 검토 통과 |

측정값: 총 18.0분(규칙 17~19분), 해설 점유율 41.5%(참고 영상 41.9%),
해설 주기 16.6초(참고 영상 17.8초), 스포일러 차단선 7570초(126:10).

## 다음 순서

1. `MOVIE_REVIEW_ROOT=devil python narration_pass.py generate` — `codex` CLI 필요
2. `pipeline.py render` → 음성 → 믹스 → 자막 → `scripts/delivery_gates.py`

## 타임코드는 어떻게 고쳤나

33개 중 12개가 틀리고 11개가 미확인이었다. 전부 프레임으로 확인해 **24개를 재조정**했다.
가장 크게 어긋난 것은 `carl_method`로 68분에 잡혀 있었지만 실제로는 **43분**이었다.

원인은 **자막이 누가 말하는지만 알려주고 화면 내용은 알려주지 않는다**는 것이다.
이 영화는 핵심 장면이 대사 없이 지나간다. 거미 설교는 자막상 11분에 끝나지만
로이가 항아리를 머리에 붓는 것은 **14분 30초**다. 헬렌이 죽는 장면도 자막에
"Resur--"가 나오는 39분 43초보다 **2분 앞선 37분 40초**에 이미 끝나 있다.

절차: 영어 자막에서 앵커 대사를 찾아 대략적인 위치를 잡고, 그 주변을 15~30초 간격으로
프레임 추출해 눈으로 확정한다. 함정 두 가지 — `drawtext` 레이블에 콜론을 쓰면 필터가
깨지므로 `3m20s` 형식을 쓴다. 여러 장을 붙일 때는 `concat` 후 `tile`이다.

## 프레임 검증 도구 사용법 (중요)

`devil/verify_intervals.py`는 세 가지로 쓴다.

```
python devil/verify_intervals.py                      # 33개 전부, 시트 4장 — 최초 1회만
python devil/verify_intervals.py jack_sacrifice ...   # 바뀐 것만, 시트 1장 — 수정 후
python devil/verify_intervals.py 28:40 29:15 29:40    # 위치 탐색용 스캔
```

**하나 고칠 때마다 전체를 다시 뽑지 말 것.** 이번 작업에서 그렇게 하다가 토큰을
크게 낭비했다. 33장을 다시 뽑고 시트 4장을 다시 읽는 비용은 수정 자체의 여덟 배쯤 되고,
나머지 32장은 직전에 본 것과 똑같다. 두 번째 형태가 그래서 있다.

## 구조상 반드시 알아야 할 것 — 약속 구간과 장면 범위는 다르다

`source_start`/`source_end`는 **편집기가 잘라 쓸 수 있는 장면 범위**다.
`selected_intervals`는 **반드시 화면에 나온다는 약속**이고, `validate_story_coverage`가
이 구간의 85% 이상이 실제 편집표에 남았는지 검사한다.

둘을 같게 놓으면 반드시 실패한다. 18분짜리 리뷰가 40분치 원본을 다 담을 수 없기 때문이다.
그래서 `ev()`가 약속 구간을 장면 앞부분 **12~18초**로 자동 산출한다. 상한이 14초인 것은
측정 결과다 — 18초로 두니 가장 얇은 두 사건(`teagardin_arrives`, `carl_method`)이
약속의 81%밖에 채우지 못했다.

여기서 따라오는 규칙: **약속 구간은 장면이 눈에 보이는 지점에서 시작해야 한다.**
`jack_sacrifice`, `lenora_dies`, `closing_cast_hook`은 처음에 어두운 도입부에 걸려
약속한 14초가 사실상 검은 화면이었다. 세 개 모두 뒤로 밀었다.

## 편집표 예산 관련

`build_edit_plan.py`의 `TARGET`은 1145초(19:05)지만 결과는 18.0분이다. 타일링은
항상 예산 아래로 떨어지기 때문이다 — 사건의 장면 범위가 먼저 끝나거나, 마지막 해설
블록 뒤에 영상 구간을 넣을 자리가 없으면 그 그룹이 멈춘다. 18:00을 목표로 두면
17:00이 나온다. 6% 여유를 두고 잡는다.

## 마무리 블록 주의

`closing_theme`과 `closing_cast_hook`은 다른 사건이 쓰는 구간과 겹치면 안 된다.
편집표는 같은 원본 구간을 두 번 쓸 수 없다(`중복된 소스 구간`). 처음에 마무리 주제가
`arvin_returns_home` 안에 들어가 있어서 걸렸다. 지금은 30:18(빈 집 앞 트럭)과
116:12(사무실의 보데커)를 쓴다.

## 결말을 가리는 선

차단선 7570초는 프레임으로 확인했다. **126:05에는 보데커가 아직 나무 뒤에 살아 있고,
126:20에 결과가 화면에 보인다.** 10초 여유다. `standoff` 구간은 126:09에서 끝난다.
이 값을 건드릴 때는 반드시 126:05~126:25를 다시 프레임으로 확인할 것.

## 참고 영상에서 배운 것 (승인 규칙 11개)

`work/references/learning_registry.json`에 근거·측정값·롤백 조건과 함께 있다.
수치는 같은 영화를 다룬 참고 영상 `rd5pF9Qj_C8`(서울극장, 18.1분)에서 나왔다.

| 규칙 | 요구 |
|---|---|
| `shorter_total_runtime` | 17~19분 |
| `reviewer_share_floor` | 해설 40% + 원음 10% |
| `narration_cycle_not_block_length` | 블록 6~7초, 주기 18초 |
| `phase_density_curve_confirmed` | 51.8 → 40.5 → 27.6 → 50.9% |
| `save_dialogue_for_confrontations` | 원음은 대결에 10블록·각 10초 |
| `ending_cut_at_the_draw` | 대면을 다 보여주고 결과 직전에 끊는다 |
| `closing_block_theme_then_cast` | 마지막 통짜 블록: 주제 → 해석 → 캐스팅 → 권유 |

참고 영상 측정에서 한 번 틀렸다가 고친 것: 자동 자막이 한국어 해설과 영화 영어 대사를
함께 전사하므로 처음 읽은 54.2%는 해설 점유율이 아니었다. 분리하니 해설 41.9% +
원음 10.2%였다. `scripts/analyze_reference.py`가 이제 자동으로 분리한다.

## 이 프로젝트에서 고친 파이프라인 결함

- `pipeline.py`에 19분 하한이 하드코딩돼 있었다. 템플릿에 이미 있던
  `min_duration_sec`/`max_duration_sec`를 존중하도록 고쳤다. 미설정 프로젝트는 기존 동작 유지.
- `pipeline.py`에 `source_audio_downmix`를 추가했다. 기본 5.1→스테레오 다운믹스가
  센터(대사)를 3dB 줄여 실측 4.2dB 손실이 났다. 비워두면 기존 동작 그대로다.
- `verify_intervals.py`가 작업 폴더의 하위 디렉터리를 지우려다 실패했다. `*.jpg`만 지운다.

## 콘스탄틴 (직전 프로젝트)

**전 세계 차단됨.** Warner Bros.가 `Constantine (2005) ASSET Full Movie Master`를
차단으로 설정했고 클레임이 0:00~24:47 전체를 덮는다. 이의 제기는 권하지 않는다 —
공정 이용 4요소 중 3개가 불리하고, 기각 시 저작권 경고로 이어진다.

작업물은 `samples/`에 8초 발췌로만 남아 있고 렌더는 로컬에만 있다.
`Constantine/story_review_v5/delivery_gates.json`으로 23/23 통과 상태.
