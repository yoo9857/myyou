from __future__ import annotations

import json
import os
from pathlib import Path


OLD = "모두를 살릴 유일한 남자. 그런데 왜 감염자들은 그를 공격하지 않았을까요?"
NEW = "여기, 모두를 살릴 유일한 남자가 있습니다."
PROJECT = (
    Path(os.environ["LOCALAPPDATA"])
    / "CapCut"
    / "User Data"
    / "Projects"
    / "com.lveditor.draft"
    / "0811 (5)"
)


def replace(value):
    if isinstance(value, str):
        return value.replace(OLD, NEW), value.count(OLD)
    if isinstance(value, list):
        total = 0
        out = []
        for item in value:
            changed, count = replace(item)
            out.append(changed)
            total += count
        return out, total
    if isinstance(value, dict):
        total = 0
        out = {}
        for key, item in value.items():
            changed, count = replace(item)
            out[key] = changed
            total += count
        return out, total
    return value, 0


def main() -> None:
    changed_files = []
    for path in PROJECT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".tmp"}:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        updated, count = replace(data)
        if count:
            path.write_text(
                json.dumps(updated, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            changed_files.append((str(path.relative_to(PROJECT)), count))
    if not changed_files:
        raise RuntimeError("CapCut 프로젝트에서 기존 첫 자막을 찾지 못했습니다.")
    for path, count in changed_files:
        print(path, count)


if __name__ == "__main__":
    main()
