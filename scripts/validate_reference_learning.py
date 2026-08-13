from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(registry_path: Path, project_root: Path) -> dict[str, int | str]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("reference learning schema_version must be 1")
    policy = str(data.get("copyright_policy", "")).lower()
    if "never copy" not in policy:
        raise ValueError("copyright_policy must explicitly prohibit copying reference wording")

    references = data.get("references", [])
    rules = data.get("rules", [])
    reference_ids = [str(item.get("video_id", "")).strip() for item in references]
    if not reference_ids or any(not item for item in reference_ids):
        raise ValueError("every reference needs a non-empty video_id")
    if len(reference_ids) != len(set(reference_ids)):
        raise ValueError("duplicate reference video_id")
    for item in references:
        metrics_path = Path(str(item.get("metrics_file", "")))
        if not metrics_path.is_absolute():
            metrics_path = project_root / metrics_path
        if not metrics_path.exists():
            raise FileNotFoundError(f"missing metrics file: {metrics_path}")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if str(metrics.get("video_id")) != str(item["video_id"]):
            raise ValueError(f"metrics video_id mismatch: {metrics_path}")
        if not str(item.get("limitations", "")).strip():
            raise ValueError(f"reference {item['video_id']} has no limitations")

    rule_ids = [str(item.get("id", "")).strip() for item in rules]
    if any(not item for item in rule_ids) or len(rule_ids) != len(set(rule_ids)):
        raise ValueError("rule IDs must be non-empty and unique")
    known = set(reference_ids)
    approved = 0
    for rule in rules:
        if rule.get("status") == "approved":
            approved += 1
        evidence = {str(item) for item in rule.get("evidence", [])}
        missing = sorted(evidence - known)
        if missing:
            raise ValueError(f"rule {rule.get('id')} has unknown evidence: {missing}")
        for field in ("instruction", "scope", "rollback_condition"):
            if not str(rule.get(field, "")).strip():
                raise ValueError(f"rule {rule.get('id')} has no {field}")
    if approved == 0:
        raise ValueError("at least one approved rule is required")
    return {"status": "pass", "references": len(references), "rules": len(rules), "approved_rules": approved}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the approved reference-learning registry")
    parser.add_argument("registry", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = validate(args.registry.resolve(), args.project_root.resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
