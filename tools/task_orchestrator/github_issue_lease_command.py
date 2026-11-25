"""Validate and execute explicit GitHub Issue comment lease commands.

Only fixed claim/renew/release operations are accepted. Issue and comment
content is parsed as data; it is never interpolated into a shell command.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_issue_intake import TASK_LABEL
from .github_lease_git import LeaseGitError, claim_or_renew, release
from .github_task_protocol import GitHubTaskError, validate_issue_body

TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
AGENTS = {"chatgpt", "grok"}
CLAIM_RE = re.compile(r"^[a-f0-9]{16,64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$")


class IssueLeaseCommandError(ValueError):
    """An Issue comment is not an authorized lease command."""


def _minutes(value: str | None) -> int:
    if value is None:
        return 60
    if not re.fullmatch(r"[0-9]{1,3}", value):
        raise IssueLeaseCommandError("Lease duration must be an integer from 1 to 240.")
    result = int(value)
    if not 1 <= result <= 240:
        raise IssueLeaseCommandError("Lease duration must be between 1 and 240 minutes.")
    return result


def parse_lease_comment(body: Any) -> dict[str, Any]:
    if not isinstance(body, str) or len(body) > 512:
        raise IssueLeaseCommandError("Comment command is missing or too large.")
    parts = body.strip().split()
    if len(parts) < 3 or parts[0] != "/jet-agent":
        raise IssueLeaseCommandError("Expected a /jet-agent lease command.")
    operation = parts[1]
    owner = parts[2]
    if owner not in AGENTS:
        raise IssueLeaseCommandError("Owner must be chatgpt or grok.")

    if operation == "claim" and len(parts) in {4, 5}:
        claim_id = parts[3]
        if not CLAIM_RE.fullmatch(claim_id):
            raise IssueLeaseCommandError("Claim ID must be 16-64 lowercase hexadecimal characters.")
        return {"operation": "claim", "owner": owner, "claim_id": claim_id,
                "duration_minutes": _minutes(parts[4] if len(parts) == 5 else None)}

    if operation == "renew" and len(parts) in {5, 6}:
        previous_claim_id, claim_id = parts[3], parts[4]
        if not CLAIM_RE.fullmatch(previous_claim_id) or not CLAIM_RE.fullmatch(claim_id):
            raise IssueLeaseCommandError("Both claim IDs must be 16-64 lowercase hexadecimal characters.")
        if previous_claim_id == claim_id:
            raise IssueLeaseCommandError("Renewal must use a fresh claim ID.")
        return {"operation": "renew", "owner": owner, "previous_claim_id": previous_claim_id,
                "claim_id": claim_id,
                "duration_minutes": _minutes(parts[5] if len(parts) == 6 else None)}

    if operation == "release" and len(parts) == 4:
        claim_id = parts[3]
        if not CLAIM_RE.fullmatch(claim_id):
            raise IssueLeaseCommandError("Claim ID must be 16-64 lowercase hexadecimal characters.")
        return {"operation": "release", "owner": owner, "claim_id": claim_id}

    raise IssueLeaseCommandError("Supported commands: claim, renew, release.")


def build_issue_lease_request(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("action") != "created":
        raise IssueLeaseCommandError("Only newly created Issue comments are accepted.")
    issue = event.get("issue")
    comment = event.get("comment")
    repository = event.get("repository")
    if not isinstance(issue, dict) or issue.get("pull_request") is not None:
        raise IssueLeaseCommandError("Lease commands are only accepted on Issues, not pull requests.")
    if issue.get("state") != "open":
        raise IssueLeaseCommandError("Closed Issues cannot acquire or change leases.")
    labels = issue.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(label, dict) and label.get("name") == TASK_LABEL for label in labels
    ):
        raise IssueLeaseCommandError("Issue must carry the agent-task label.")
    if not isinstance(comment, dict) or comment.get("author_association") not in TRUSTED_ASSOCIATIONS:
        raise IssueLeaseCommandError("Only repository owners, members, or collaborators may operate leases.")
    if not isinstance(repository, dict) or not isinstance(repository.get("full_name"), str):
        raise IssueLeaseCommandError("Repository identity is missing.")
    full_name = repository["full_name"]
    if not REPOSITORY_RE.fullmatch(full_name):
        raise IssueLeaseCommandError("Repository identity is invalid.")
    issue_number = issue.get("number")
    if isinstance(issue_number, bool) or not isinstance(issue_number, int) or issue_number < 1:
        raise IssueLeaseCommandError("Issue number is invalid.")
    issue_url = issue.get("html_url")
    if not isinstance(issue_url, str) or not issue_url.startswith("https://github.com/"):
        raise IssueLeaseCommandError("Issue URL is invalid.")
    try:
        task = validate_issue_body(issue.get("body"), repository_metadata=repository, allow_legacy_jet_vpn=True)
    except GitHubTaskError as exc:
        raise IssueLeaseCommandError("Issue task payload is invalid.") from exc
    command = parse_lease_comment(comment.get("body"))
    assigned = task["assigned_agent"]
    if assigned != "any" and assigned != command["owner"]:
        raise IssueLeaseCommandError("The task is assigned to a different agent.")
    return {
        "repository": full_name,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "task_id": task["task_id"],
        "assigned_agent": assigned,
        "command": command,
    }


def _current_head() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "--verify", "HEAD^{commit}"],
                                text=True, capture_output=True, check=False)
    except OSError as exc:
        raise IssueLeaseCommandError("Git executable could not be started.") from exc
    sha = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha):
        raise IssueLeaseCommandError("Could not resolve the checked-out default-branch commit.")
    return sha


def execute_issue_lease_command(request: dict[str, Any], *, token: str,
                                base_sha: str | None = None, now: str | None = None) -> dict[str, Any]:
    command = request["command"]
    operation = command["operation"]
    moment = now or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    common = {
        "task_id": request["task_id"],
        "owner": command["owner"],
        "claim_id": command["claim_id"],
        "now": moment,
        "repository": request["repository"],
        "token": token,
    }
    if operation == "claim":
        if base_sha is None:
            raise IssueLeaseCommandError("A pinned default-branch SHA is required for a new claim.")
        result = claim_or_renew(
            operation="claim", base_sha=base_sha,
            duration_minutes=command["duration_minutes"], **common,
        )
    elif operation == "renew":
        result = claim_or_renew(
            operation="renew", base_sha=None,
            duration_minutes=command["duration_minutes"],
            previous_claim_id=command["previous_claim_id"], **common,
        )
    else:
        result = release(**common)
    return {
        "operation": operation,
        "task_id": request["task_id"],
        "issue_number": request["issue_number"],
        "issue_url": request["issue_url"],
        "result": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        request = build_issue_lease_request(event)
        command = request["command"]
        base_sha = _current_head() if command["operation"] == "claim" else None
        result = execute_issue_lease_command(request, token=token, base_sha=base_sha)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError,
            IssueLeaseCommandError, LeaseGitError) as exc:
        parser.error(str(exc))
    print("Verified " + result["operation"] + " lease for task " + result["task_id"] + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
