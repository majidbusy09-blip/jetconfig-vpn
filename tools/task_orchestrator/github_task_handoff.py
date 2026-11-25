"""Build a bounded execution handoff from a verified task lease.

The handoff is data-only: it does not wake a model, execute source code, or
transfer repository source. It binds the validated Issue payload to the exact
lease result produced by the trusted lease-command workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_issue_lease_command import (
    IssueLeaseCommandError,
    build_issue_lease_request,
)
from .github_issue_intake import load_project_configuration, validate_task_project_binding
from .github_lease import LeaseError, lock_branch
from .github_task_protocol import GitHubTaskError, validate_issue_body

SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class TaskHandoffError(ValueError):
    """A task handoff does not match a verified active lease."""


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TaskHandoffError(name + " must be a positive integer.")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise TaskHandoffError(name + " must be timezone-aware ISO-8601 text.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TaskHandoffError(name + " is not valid ISO-8601 text.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TaskHandoffError(name + " must include a timezone.")
    return parsed.astimezone(timezone.utc)


def build_task_handoff(
    event: Any,
    lease_result: Any,
    *,
    run_id: int,
    run_attempt: int,
    now: str | None = None,
) -> dict[str, Any]:
    """Validate and bind the Issue payload to the exact active lease result."""
    try:
        request = build_issue_lease_request(event)
    except IssueLeaseCommandError as exc:
        raise TaskHandoffError("Issue event is not an eligible lease command.") from exc

    command = request["command"]
    operation = command["operation"]
    if operation not in {"claim", "renew"}:
        raise TaskHandoffError("Only claim and renew operations create handoffs.")
    if not isinstance(lease_result, dict) or set(lease_result) != {
        "operation", "task_id", "issue_number", "issue_url", "result"
    }:
        raise TaskHandoffError("Lease result envelope has unexpected or missing fields.")
    if (
        lease_result["operation"] != operation
        or lease_result["task_id"] != request["task_id"]
        or lease_result["issue_number"] != request["issue_number"]
        or lease_result["issue_url"] != request["issue_url"]
    ):
        raise TaskHandoffError("Lease result does not match the requested task and operation.")

    result = lease_result["result"]
    expected_result_fields = {
        "task_id", "owner", "claim_id", "status", "base_sha", "expires_at",
        "lock_branch", "lock_commit", "verified",
    }
    if not isinstance(result, dict) or set(result) != expected_result_fields:
        raise TaskHandoffError("Verified lease record has unexpected or missing fields.")
    if result["verified"] is not True or result["status"] != "active":
        raise TaskHandoffError("Handoff requires a remotely verified active lease.")
    if (
        result["task_id"] != request["task_id"]
        or result["owner"] != command["owner"]
        or result["claim_id"] != command["claim_id"]
    ):
        raise TaskHandoffError("Lease owner, task ID, or claim ID does not match the Issue command.")
    try:
        expected_branch = lock_branch(request["task_id"])
    except LeaseError as exc:
        raise TaskHandoffError("Task ID cannot be used for a lease branch.") from exc
    if result["lock_branch"] != expected_branch:
        raise TaskHandoffError("Lease branch does not match the task ID.")
    if not isinstance(result["base_sha"], str) or not SHA_RE.fullmatch(result["base_sha"]):
        raise TaskHandoffError("Lease pinned base SHA is invalid.")
    if not isinstance(result["lock_commit"], str) or not SHA_RE.fullmatch(result["lock_commit"]):
        raise TaskHandoffError("Lease lock commit SHA is invalid.")

    moment = _timestamp(now or datetime.now(timezone.utc).isoformat(), "now")
    expires = _timestamp(result["expires_at"], "lease expires_at")
    if expires <= moment:
        raise TaskHandoffError("Lease is expired; no execution handoff can be created.")
    run_id = _positive_int(run_id, "run_id")
    run_attempt = _positive_int(run_attempt, "run_attempt")

    issue = event["issue"]
    body = issue.get("body")
    try:
        task = validate_issue_body(
            body, repository_metadata=event.get("repository"), allow_legacy_jet_vpn=True
        )
    except GitHubTaskError as exc:
        raise TaskHandoffError("Task Issue payload is invalid.") from exc
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    project_binding = None
    if task["schema_version"] == 2:
        schema, manifests = load_project_configuration(Path(__file__).resolve().parents[2])
        project_binding = validate_task_project_binding(
            task, event["repository"], schema=schema, project_manifests=manifests
        )

    handoff = {
        "handoff_schema": 2,
        "handoff_id": (
            "issue-" + str(request["issue_number"]) +
            "-run-" + str(run_id) + "-attempt-" + str(run_attempt)
        ),
        "source": "github-issue",
        "repository": request["repository"],
        "issue": {
            "number": request["issue_number"],
            "url": request["issue_url"],
            "body_sha256": body_digest,
        },
        "task": task,
        "lease": {
            "operation": operation,
            "previous_claim_id": command.get("previous_claim_id"),
            "owner": result["owner"],
            "claim_id": result["claim_id"],
            "status": result["status"],
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "base_sha": result["base_sha"],
            "lock_branch": result["lock_branch"],
            "lock_commit": result["lock_commit"],
            "verified": True,
        },
        "workflow": {"run_id": run_id, "run_attempt": run_attempt},
        "execution": {
            "status": "ready-for-agent",
            "agent_dispatched": False,
            "model_called": False,
            "source_uploaded": False,
            "patch_applied": False,
        },
    }
    if project_binding is not None:
        handoff["handoff_schema"] = 3
        handoff["project_binding"] = project_binding
    return handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--lease-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        lease_result = json.loads(Path(args.lease_result).read_text(encoding="utf-8"))
        handoff = build_task_handoff(
            event, lease_result, run_id=args.run_id, run_attempt=args.run_attempt
        )
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (
        OSError, UnicodeError, json.JSONDecodeError, TaskHandoffError,
        IssueLeaseCommandError, GitHubTaskError,
    ) as exc:
        parser.error(str(exc))
    print("Created lease-verified handoff " + handoff["handoff_id"] + ".")
    print("No model was invoked and no source files were transferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
