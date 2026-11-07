"""Fail-closed validation for PAPER research task evidence. No network or trading."""
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
STATES = {"TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE"}
REQUIRED = ("task_id", "state", "owner", "branch", "input_sha", "protocol_sha")
DONE_REQUIRED = ("output_sha", "artifact_paths", "test_command", "test_exit_code", "reviewer", "review_note")


def validate(task):
    errors = []
    if not isinstance(task, dict):
        return ["task must be a JSON object"]
    for key in REQUIRED:
        if not isinstance(task.get(key), str) or not task[key].strip():
            errors.append(f"missing or invalid {key}")
    if task.get("state") not in STATES:
        errors.append("invalid state")
    for key in ("input_sha", "protocol_sha"):
        if key in task and not SHA.fullmatch(str(task[key])):
            errors.append(f"invalid {key}")
    if task.get("state") == "DONE":
        for key in DONE_REQUIRED:
            if key not in task or task[key] is None or task[key] == "":
                errors.append(f"missing {key} for DONE")
        if not SHA.fullmatch(str(task.get("output_sha", ""))):
            errors.append("invalid output_sha")
        if not isinstance(task.get("artifact_paths"), list) or not task["artifact_paths"] or not all(isinstance(p, str) and p.strip() and not p.startswith("/") and ".." not in Path(p).parts for p in task["artifact_paths"]):
            errors.append("invalid artifact_paths")
        if task.get("test_exit_code") != 0 or type(task.get("test_exit_code")) is not int:
            errors.append("DONE requires test_exit_code 0")
        if task.get("reviewer") == task.get("owner"):
            errors.append("DONE requires different reviewer")
        if task.get("blockers"):
            errors.append("DONE cannot have blockers")
        if task.get("reproduced") is True and not task.get("reproduction_evidence"):
            errors.append("reproduced requires reproduction_evidence")
    return errors


def idempotency_key(task):
    errors = validate(task)
    if errors:
        raise ValueError("; ".join(errors))
    return ":".join((task["task_id"], task["input_sha"], task["protocol_sha"]))


def main():
    if len(sys.argv) != 2:
        print("usage: python automation/task_evidence.py task.json", file=sys.stderr)
        return 2
    try:
        task = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"cannot read task: {exc}", file=sys.stderr)
        return 2
    errors = validate(task)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("VALID", idempotency_key(task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
