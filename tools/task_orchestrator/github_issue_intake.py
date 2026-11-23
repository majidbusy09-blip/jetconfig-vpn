"""Convert a GitHub Issues event into a validated, provider-neutral task artifact.

This is an intake bridge only: it never claims a lease, invokes a model, runs
commands, edits repository files, or dispatches an implementation agent.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .github_task_protocol import GitHubTaskError, validate_issue_body
except ImportError:
    from github_task_protocol import GitHubTaskError, validate_issue_body

INTAKE_SCHEMA = 1
TASK_LABEL = "agent-task"


class IntakeError(ValueError):
    """An Issues event is not eligible for task intake."""


def build_intake(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise IntakeError("GitHub event must be a JSON object.")
    action = event.get("action")
    if action not in {"opened", "labeled", "edited"}:
        raise IntakeError("Only opened, labeled, or edited Issues events are accepted.")
    issue = event.get("issue")
    if not isinstance(issue, dict) or issue.get("pull_request") is not None:
        raise IntakeError("Event must reference a GitHub Issue, not a pull request.")
    if issue.get("state") != "open":
        raise IntakeError("Closed Issues cannot enter the task inbox.")
    labels = issue.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(label, dict) and label.get("name") == TASK_LABEL for label in labels
    ):
        raise IntakeError("Issue must carry the agent-task label.")
    number = issue.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise IntakeError("Issue number is invalid.")
    title = issue.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise IntakeError("Issue title is invalid.")
    body = issue.get("body")
    if not isinstance(body, str):
        raise IntakeError("Issue body is missing.")
    try:
        payload = validate_issue_body(body)
    except GitHubTaskError as exc:
        raise IntakeError(f"Task payload rejected: {exc}") from exc
    repository = event.get("repository")
    if not isinstance(repository, dict):
        raise IntakeError("Repository metadata is missing.")
    full_name = repository.get("full_name")
    if not isinstance(full_name, str) or "/" not in full_name or len(full_name) > 200:
        raise IntakeError("Repository identity is invalid.")
    html_url = issue.get("html_url")
    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        raise IntakeError("Issue URL is invalid.")
    return {
        "intake_schema": INTAKE_SCHEMA,
        "source": "github-issue",
        "repository": full_name,
        "issue_number": number,
        "issue_url": html_url,
        "issue_title": title.strip(),
        "issue_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "task": payload,
        "execution": {
            "status": "validated-awaiting-claim",
            "lease_claimed": False,
            "agent_dispatched": False,
            "model_called": False,
            "source_uploaded": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        result = build_intake(event)
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != encoded:
            raise IntakeError("Refusing to overwrite a different intake artifact.")
        target.write_text(encoded, encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, IntakeError) as exc:
        parser.error(str(exc))
    print(f"Validated Issue #{result['issue_number']} as task {result['task']['task_id']}.")
    print("No lease claimed; no model or implementation agent was invoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
