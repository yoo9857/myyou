"""Run a review end to end in the order that does not waste money.

Everything expensive in this pipeline is expensive per run: the narration script costs a
codex pass, the voice costs ElevenLabs characters. Everything that decides whether those
runs will be any good - the story map, the beat order, where narration sits, whether clips
cut across a spoken line - is free and can be repeated all day.

The Devil All The Time was built in the wrong order. The script was generated four times and
the voice several, because each structural fault was found after the paid work rather than
before: beats out of order, the ending playing at 10:38, narration written on top of the
film's dialogue, clips cutting words in half. None of those needed a single API call to find.

So the paid phases sit behind a gate. The free phases run first, the structure preview is
built for a person to watch, and nothing bills until that person says the structure is
settled. Approval is recorded against a fingerprint of the plan: change the plan and the
approval lapses, because an approval of something else is not an approval.

    python scripts/run_workflow.py devil/config.json status
    python scripts/run_workflow.py devil/config.json run
    python scripts/run_workflow.py devil/config.json approve structure
    python scripts/run_workflow.py devil/config.json run --force-paid    # skips the gate

State lives in <project>/work/workflow_state.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

FREE, CODEX, VOICE = "free", "codex", "voice"
COST_LABEL = {FREE: "무료", CODEX: "codex 호출", VOICE: "ElevenLabs 호출"}


class Phase:
    def __init__(self, key, title, cost, command, produces=None, note=""):
        self.key, self.title, self.cost = key, title, cost
        self.command, self.produces, self.note = command, produces, note


def phases(root: Path, config_path: Path, music: Path | None) -> list[Phase]:
    py = [sys.executable]
    scripts = CODE_ROOT / "scripts"
    plan = root / "output" / "edit_plan.json"
    staged = root / "output" / "edit_plan_pre_narration.json"
    return [
        Phase("story_map", "스토리맵 생성", FREE,
              py + [str(root / "build_story_map.py")],
              root / "story_map.v1.json"),
        Phase("story_valid", "스토리맵 검증", FREE,
              py + [str(Path.home() / ".codex/skills/edit-movie-review/scripts/validate_story_map.py"),
                    str(root / "story_map.v1.json"), "--require-render-ready"]),
        Phase("frames", "사건 프레임 확인", FREE,
              py + [str(root / "verify_intervals.py")],
              note="시트를 눈으로 보고 사건이 맞는 장면인지 확인한다. 이 단계를 건너뛰면 "
                   "화면에 없는 장면을 설명하는 대본이 나온다."),
        Phase("edit_plan", "편집표 생성", FREE,
              py + [str(root / "build_edit_plan.py")], plan),
        Phase("audit_plan", "편집표 감사", FREE,
              py + [str(scripts / "audit_project.py"), str(config_path)],
              note="순서, 대사 경계, 차단선, 약속 구간 커버리지."),
        Phase("preview", "구조 미리보기", FREE,
              py + [str(scripts / "build_structure_preview.py"), str(config_path)],
              root / "output" / "structure_preview.mp4",
              note="사람이 보고 순서를 확정하는 단계. 여기까지가 전부 무료다."),
        Phase("script", "나레이션 대본", CODEX,
              py + [str(CODE_ROOT / "narration_pass.py"), "generate",
                    "--source", "output/edit_plan_pre_narration.json"],
              root / "output" / "narration_script_v5.json"),
        Phase("apply", "대본 적용", FREE,
              py + [str(CODE_ROOT / "narration_pass.py"), "apply",
                    "--source", "output/edit_plan_pre_narration.json", "--make-current"]),
        Phase("voice", "나레이션 음성", VOICE,
              py + [str(CODE_ROOT / "generate_narration_audio.py")],
              note="order+문장이 같은 파일은 재사용된다. 편집표 구조가 바뀌면 전량 재생성된다."),
        Phase("duck", "구간별 더킹 산출", FREE,
              py + [str(scripts / "solve_duck.py"), str(config_path)]),
        Phase("render", "렌더", FREE,
              py + [str(CODE_ROOT / "pipeline.py"), "render"]),
        Phase("outro", "마무리 음악", FREE,
              py + [str(scripts / "add_outro_music.py"), str(config_path), str(music)]
              if music else None),
        Phase("captions", "자막 디자인", FREE,
              py + [str(scripts / "build_caption_design.py"), str(config_path)]),
        Phase("balance", "밸런스 측정", FREE,
              py + [str(scripts / "measure_balance.py"), str(config_path)]),
        Phase("gates", "납품 게이트", FREE,
              py + [str(scripts / "delivery_gates.py"), str(root / "delivery_gates.json")]),
        Phase("audit_final", "최종 감사", FREE,
              py + [str(scripts / "audit_project.py"), str(config_path)]),
        Phase("capcut", "CapCut 프로젝트", FREE,
              py + [str(scripts / "build_capcut_project.py"), str(config_path)]),
    ]


def plan_fingerprint(root: Path) -> str:
    """What an approval is an approval of: the beats, their order and their timings."""
    path = root / "output" / "edit_plan.json"
    if not path.exists():
        return ""
    plan = json.loads(path.read_text(encoding="utf-8"))
    shape = [(s["order"], s["kind"], s["story_event_id"],
              round(float(s["source_start"]), 2), round(float(s["source_end"]), 2))
             for s in plan["segments"]]
    return hashlib.sha256(json.dumps(shape).encode("utf-8")).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("action", choices=("status", "run", "approve"))
    parser.add_argument("what", nargs="?", default="structure")
    parser.add_argument("--music", type=Path, default=None)
    parser.add_argument("--from", dest="start_key", default=None)
    parser.add_argument("--force-paid", action="store_true")
    args = parser.parse_args()

    config_path = args.config.resolve()
    root = config_path.parent
    state_path = root / "work" / "workflow_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    order = phases(root, config_path, args.music)

    if args.action == "approve":
        fingerprint = plan_fingerprint(root)
        if not fingerprint:
            raise SystemExit("편집표가 없습니다. 먼저 run으로 미리보기까지 만드십시오.")
        state["approved_structure"] = fingerprint
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  구조 승인 기록: {fingerprint}")
        print("  이제 run이 대본과 음성 단계로 넘어갑니다.")
        return 0

    if args.action == "status":
        approved = state.get("approved_structure")
        current = plan_fingerprint(root)
        print(f"  편집표 지문: {current or '(없음)'}")
        print(f"  승인된 지문: {approved or '(없음)'}")
        if approved and current and approved != current:
            print("  승인 이후 편집표가 바뀌었습니다. 다시 승인해야 유료 단계가 열립니다.")
        for phase in order:
            if phase.command is None:
                continue
            done = phase.produces.exists() if phase.produces else state.get(phase.key)
            print(f"  {'v' if done else ' '} {phase.key:12} {phase.title:16} [{COST_LABEL[phase.cost]}]")
        return 0

    started = args.start_key is None
    for phase in order:
        if phase.key == args.start_key:
            started = True
        if not started or phase.command is None:
            continue
        if phase.cost != FREE and not args.force_paid:
            approved = state.get("approved_structure")
            current = plan_fingerprint(root)
            if approved != current or not current:
                print(f"\n  멈춤: '{phase.title}'은 {COST_LABEL[phase.cost]}가 발생합니다.")
                print(f"  {root / 'output' / 'structure_preview.mp4'} 를 보고 순서를 확정한 뒤")
                print(f"  python {Path(__file__).name} {args.config} approve structure")
                print("  로 승인하면 이어서 진행합니다.")
                if approved and current and approved != current:
                    print(f"  (승인 {approved} != 현재 {current} — 편집표가 바뀌었습니다)")
                return 2
        print(f"\n[{phase.key}] {phase.title}  ({COST_LABEL[phase.cost]})")
        if phase.note:
            print(f"  {phase.note}")
        # The staged copy the narration pass reads has to match what was just planned, or the
        # script is written against one plan and applied to another.
        if phase.key == "script":
            staged = root / "output" / "edit_plan_pre_narration.json"
            staged.write_bytes((root / "output" / "edit_plan.json").read_bytes())
        env = {"MOVIE_REVIEW_ROOT": str(root)}
        result = subprocess.run(phase.command, cwd=CODE_ROOT,
                                env={**dict(__import__("os").environ), **env})
        if result.returncode != 0:
            print(f"  실패 (exit {result.returncode}) — 여기서 멈춥니다.")
            return result.returncode
        state[phase.key] = True
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n  전체 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
