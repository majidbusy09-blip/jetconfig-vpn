"""Revalidate open agent PRs whenever their linked task Issue changes.

This trusted-main, read-only bridge closes the stale-event gap in the PR guard:
task edits, assignment/label changes, and closure trigger a fresh validation
against the current Issue, lease, pinned base, and changed-file state.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .github_issue_intake import TASK_LABEL
from .github_task_pr_guard import (
    GuardError,
    api_get,
    parse_pr_envelope,
    validate_agent_pr,
)
from .github_task_protocol import GitHubTaskError, validate_issue_body

ISSUE_ACTIONS = {
    "edited", "closed", "reopened", "labeled", "unlabeled",
    "assigned", "unassigned",
}


class RevalidationError(ValueError):
    """The task Issue event or one of its linked agent PRs is invalid."""


def _open_pull_requests(repository: str, token: str) -> list[dict]:
    results: list[dict] = []
    for page in range(1, 11):
        batch = api_get(
            repository,
            "/pulls?state=open&per_page=100&page=" + str(page),
            token,
        )
        if not isinstance(batch, list):
            raise RevalidationError("Open PR listing response is malformed.")
        results.extend(batch)
        if len(results) > 1000:
            raise RevalidationError("Open PR scan exceeded the 1000-PR safety limit.")
        if len(batch) < 100:
            return results
    raise RevalidationError("Open PR pagination exceeded the safety limit.")


def revalidate_issue_event(event: dict, *, token: str, repository: str) -> dict:
    if not isinstance(event, dict) or event.get("action") not in ISSUE_ACTIONS:
        raise RevalidationError("Unsupported Issue event action.")
    if not isinstance(event.get("repository"), dict) or event["repository"].get("full_name") != repository:
        raise RevalidationError("Event repository mismatch.")
    issue = event.get("issue")
    if not isinstance(issue, dict) or issue.get("pull_request") is not None:
        raise RevalidationError("Expected a GitHub Issue event.")
    number = issue.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise RevalidationError("Issue number is invalid.")

    labels = issue.get("labels")
    has_task_label = isinstance(labels, list) and any(
        isinstance(item, dict) and item.get("name") == TASK_LABEL for item in labels
    )
    removed_task_label = (
        event.get("action") == "unlabeled"
        and isinstance(event.get("label"), dict)
        and event["label"].get("name") == TASK_LABEL
    )
    # GitHub's unlabeled event carries the removed label separately. Continue
    # revalidation even though the Issue's current labels no longer include it.
    if not has_task_label and not removed_task_label:
        return {"status": "not-agent-task", "issue_number": number, "checked_prs": 0}
    try:
        task = validate_issue_body(issue.get("body"))
    except GitHubTaskError as exc:
        raise RevalidationError("Changed task Issue payload is invalid.") from exc

    matches: list[dict] = []
    for pr in _open_pull_requests(repository, token):
        if not isinstance(pr, dict):
            raise RevalidationError("Open PR entry is malformed.")
        envelope = parse_pr_envelope(pr.get("body"))
        if envelope is not None and envelope["task_issue"] == number:
            matches.append(pr)

    checked = []
    for pr in matches:
        synthetic_event = {
            "action": "opened",
            "repository": {"full_name": repository},
            "pull_request": pr,
        }
        try:
            checked.append(validate_agent_pr(
                synthetic_event, token=token, repository=repository
            ))
        except GuardError as exc:
            raise RevalidationError(
                "Linked agent PR #" + str(pr.get("number")) +
                " is no longer valid after task Issue #" + str(number) +
                " changed: " + str(exc)
            ) from exc

    return {
        "status": "revalidated",
        "issue_number": number,
        "task_id": task["task_id"],
        "checked_prs": len(checked),
        "pull_requests": checked,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    args = parser.parse_args(argv)
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        result = revalidate_issue_event(event, token=token, repository=repository)
    except (OSError, UnicodeError, json.JSONDecodeError, RevalidationError, GuardError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(
            "## Agent PR task-change revalidation\n\n" +
            "- Issue: #" + str(result["issue_number"]) + "\n" +
            "- Status: " + result["status"] + "\n" +
            "- Linked PRs revalidated: " + str(result["checked_prs"]) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
