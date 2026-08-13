from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROLES = {"none", "orient", "causal_bridge", "rule_clarify", "character_subtext", "stakes", "reflection"}
TRANSITIONS = {"opening", "continuous", "cut", "bridge", "montage", "parallel_thread"}


def fail(errors: list[str], code: str, message: str) -> None:
    errors.append(f"{code}: {message}")


def validate(data: dict, require_render_ready: bool) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        fail(errors, "SCHEMA_VERSION", "schema_version must be 1")
    timeline_mode = data.get("timeline_mode", "chronological")
    if timeline_mode not in {"chronological", "audience_reveal"}:
        fail(errors, "TIMELINE_MODE", f"unsupported timeline_mode {timeline_mode!r}")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        fail(errors, "SECTIONS_MISSING", "at least one section is required")
        return errors

    seen: dict[str, dict] = {}
    last_start = -1.0
    spoiler_cutoff = data.get("spoiler_cutoff_source_sec")
    for section_index, section in enumerate(sections, 1):
        status = section.get("status")
        if status not in {"draft", "approved"}:
            fail(errors, "SECTION_STATUS", f"section {section_index} has invalid status")
        if require_render_ready and status != "approved":
            fail(errors, "SECTION_NOT_APPROVED", f"section {section_index} is {status!r}")
        if not section.get("audience_question"):
            fail(errors, "QUESTION_MISSING", f"section {section_index} needs an audience_question")
        if require_render_ready and (not section.get("exit_answer") or not section.get("next_question")):
            fail(errors, "SECTION_ARC_INCOMPLETE", f"section {section_index} needs exit_answer and next_question")
        events = section.get("events", [])
        if not events:
            fail(errors, "EVENTS_MISSING", f"section {section_index} has no events")
        for event in events:
            event_id = event.get("id")
            if not event_id or event_id in seen:
                fail(errors, "EVENT_ID", f"invalid or duplicate event id {event_id!r}")
                continue
            try:
                start = float(event["source_start"])
                end = float(event["source_end"])
                reveal = float(event["reveal_time"])
            except (KeyError, TypeError, ValueError):
                fail(errors, "EVENT_TIME", f"event {event_id} has invalid times")
                continue
            if not 0 <= start < end:
                fail(errors, "EVENT_RANGE", f"event {event_id} has invalid source range")
            if not start <= reveal <= end:
                fail(errors, "REVEAL_RANGE", f"event {event_id} reveal_time is outside its source range")
            if timeline_mode == "chronological" and start < last_start:
                fail(errors, "TIME_REVERSAL", f"event {event_id} starts before the previous event")
            last_start = start
            for field in ("summary", "visible_action", "emotional_stake", "question_opened"):
                if not event.get(field):
                    fail(errors, "EVENT_FIELD", f"event {event_id} needs {field}")
            role = event.get("narration_role", "none")
            if role not in ROLES:
                fail(errors, "NARRATION_ROLE", f"event {event_id} has invalid role {role!r}")
            narration_start = event.get("narration_start_time")
            narration_evidence = event.get("narration_evidence_time")
            if (narration_start is None) != (narration_evidence is None):
                fail(errors, "NARRATION_TIME", f"event {event_id} needs both narration timing fields")
            elif narration_start is not None and float(narration_start) < float(narration_evidence):
                fail(errors, "FUTURE_LEAK", f"event {event_id} narration starts before its evidence exists")
            if role == "none" and narration_start is not None:
                fail(errors, "NARRATION_ROLE", f"event {event_id} has narration timing but role none")
            if role != "none" and narration_start is None:
                fail(errors, "NARRATION_TIME", f"event {event_id} role {role} needs narration timing")
            intervals = event.get("selected_intervals", [])
            if event.get("must_show") and not intervals:
                fail(errors, "REQUIRED_EVENT_MISSING", f"event {event_id} has no selected interval")
            for interval in intervals:
                if not isinstance(interval, list) or len(interval) != 2:
                    fail(errors, "INTERVAL_FORMAT", f"event {event_id} has malformed selected interval")
                    continue
                interval_start, interval_end = map(float, interval)
                if not start <= interval_start < interval_end <= end:
                    fail(errors, "INTERVAL_RANGE", f"event {event_id} selected interval is outside its event")
                if require_render_ready and spoiler_cutoff is not None and interval_end > float(spoiler_cutoff):
                    fail(errors, "SPOILER_CUTOFF", f"event {event_id} crosses the spoiler cutoff")
            if require_render_ready and event.get("needs_visual_review"):
                fail(errors, "VISUAL_REVIEW_PENDING", f"event {event_id} still needs visual review")
            transition = event.get("transition_in")
            if transition is not None and transition not in TRANSITIONS:
                fail(errors, "TRANSITION_TYPE", f"event {event_id} has invalid transition {transition!r}")
            if require_render_ready and transition is None:
                fail(errors, "TRANSITION_MISSING", f"event {event_id} needs transition_in")
            cause_ids = event.get("cause_ids", [])
            if not cause_ids and not event.get("entry_point", False):
                fail(errors, "CAUSE_MISSING", f"event {event_id} has no cause and is not an entry point")
            for cause_id in cause_ids:
                if cause_id not in seen:
                    fail(errors, "CAUSE_MISSING", f"event {event_id} depends on unavailable cause {cause_id}")
            seen[event_id] = event
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a causal movie-review story map")
    parser.add_argument("story_map", type=Path)
    parser.add_argument("--require-render-ready", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.story_map.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"STORY_MAP_UNREADABLE: {exc}", file=sys.stderr)
        return 2
    errors = validate(data, args.require_render_ready)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("story map valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
