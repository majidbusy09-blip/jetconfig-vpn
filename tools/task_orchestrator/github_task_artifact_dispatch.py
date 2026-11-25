"""Validate repository_dispatch metadata for cross-repository task artifact transport.

This module validates event and artifact metadata against checked-in project
manifests. It performs no network requests and never grants task execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .github_issue_intake import IntakeError, load_project_configuration
    from .github_task_protocol import GitHubTaskError, validate_issue_body
    from .project_registry import ProjectRegistryError
except ImportError:
    from github_issue_intake import IntakeError, load_project_configuration
    from github_task_protocol import GitHubTaskError, validate_issue_body
    from project_registry import ProjectRegistryError

REPO_ID_RE = re.compile(r"^[0-9]{1,20}$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class DispatchError(ValueError):
    """A cross-repository artifact dispatch failed trusted metadata validation."""


def validate_dispatch_event(event: Any, manifests: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("action") != "jet-ai-task-artifact-ready":
        raise DispatchError("Unexpected repository_dispatch event type.")
    payload = event.get("client_payload")
    required = {
        "target_repository", "target_repository_id", "issue_number",
        "workflow_run_id", "artifact_id", "artifact_name", "source_sha",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise DispatchError("Dispatch payload must contain exactly the documented fields.")
    repository = payload["target_repository"]
    repository_id = str(payload["target_repository_id"])
    if not isinstance(repository, str) or not REPO_ID_RE.fullmatch(repository_id):
        raise DispatchError("Dispatch repository identity is malformed.")
    matches = [
        item for item in manifests
        if isinstance(item.get("repository"), dict)
        and item["repository"].get("repository_id") == repository_id
        and item["repository"].get("full_name") == repository
    ]
    if len(matches) != 1:
        raise DispatchError("Dispatch repository must match exactly one trusted registered manifest.")
    issue = payload["issue_number"]
    run_id = payload["workflow_run_id"]
    artifact_id = payload["artifact_id"]
    for value, name in ((issue, "issue_number"), (run_id, "workflow_run_id"), (artifact_id, "artifact_id")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DispatchError(f"{name} must be a positive integer.")
    expected_name = f"agent-task-{issue}"
    if payload["artifact_name"] != expected_name:
        raise DispatchError("Artifact name does not match the Issue number.")
    if not isinstance(payload["source_sha"], str) or not SHA_RE.fullmatch(payload["source_sha"]):
        raise DispatchError("Source revision must be a full lowercase Git SHA.")
    return {
        "target_repository": repository,
        "target_repository_id": repository_id,
        "issue_number": issue,
        "workflow_run_id": run_id,
        "artifact_id": artifact_id,
        "artifact_name": expected_name,
        "source_sha": payload["source_sha"],
        "project_id": matches[0]["project_id"],
    }


def validate_remote_metadata(
    dispatch: dict[str, Any],
    *,
    artifact_metadata: Any,
    repository_metadata: Any,
) -> dict[str, Any]:
    if not isinstance(artifact_metadata, dict) or not isinstance(repository_metadata, dict):
        raise DispatchError("GitHub artifact and repository metadata must be JSON objects.")
    if repository_metadata.get("id") is None or str(repository_metadata.get("id")) != dispatch["target_repository_id"]:
        raise DispatchError("Remote repository immutable ID differs from the registered project.")
    if repository_metadata.get("full_name") != dispatch["target_repository"]:
        raise DispatchError("Remote canonical repository name differs from the registered project.")
    if repository_metadata.get("html_url") != f"https://github.com/{dispatch['target_repository']}":
        raise DispatchError("Remote repository URL is not canonical.")
    if artifact_metadata.get("id") != dispatch["artifact_id"]:
        raise DispatchError("Downloaded artifact metadata ID differs from the dispatch.")
    if artifact_metadata.get("name") != dispatch["artifact_name"] or artifact_metadata.get("expired") is not False:
        raise DispatchError("Artifact name is unexpected or artifact has expired.")
    size = artifact_metadata.get("size_in_bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size < 1 or size > 512_000:
        raise DispatchError("Artifact size is missing or exceeds the configured limit.")
    workflow = artifact_metadata.get("workflow_run")
    if not isinstance(workflow, dict):
        raise DispatchError("Artifact is not associated with a GitHub Actions workflow run.")
    if workflow.get("id") != dispatch["workflow_run_id"]:
        raise DispatchError("Artifact belongs to a different workflow run.")
    if str(workflow.get("repository_id")) != dispatch["target_repository_id"]:
        raise DispatchError("Artifact workflow repository ID differs from the registered project.")
    if str(workflow.get("head_repository_id")) != dispatch["target_repository_id"]:
        raise DispatchError("Artifact head repository ID differs from the registered project.")
    if workflow.get("head_sha") != dispatch["source_sha"]:
        raise DispatchError("Artifact source SHA differs from the dispatch source revision.")
    return {
        **dispatch,
        "repository_default_branch": repository_metadata.get("default_branch"),
        "artifact_size_in_bytes": artifact_metadata.get("size_in_bytes"),
    }



def validate_issue_snapshot(
    dispatch: dict[str, Any],
    *,
    intake_artifact: Any,
    issue_metadata: Any,
    repository_metadata: dict[str, Any],
) -> None:
    """Reject stale/closed Issues and re-parse the exact current Issue body."""
    if not isinstance(intake_artifact, dict) or not isinstance(issue_metadata, dict):
        raise DispatchError("Intake artifact and live Issue metadata must be JSON objects.")
    number = dispatch["issue_number"]
    expected_url = f"https://github.com/{dispatch['target_repository']}/issues/{number}"
    if issue_metadata.get("number") != number or issue_metadata.get("html_url") != expected_url:
        raise DispatchError("Live Issue identity differs from the dispatched Issue.")
    if issue_metadata.get("state") != "open" or issue_metadata.get("pull_request") is not None:
        raise DispatchError("Only an open GitHub Issue (not a pull request) may enter the inbox.")
    if issue_metadata.get("title") != intake_artifact.get("issue_title"):
        raise DispatchError("Live Issue title changed after the intake artifact was created.")
    labels = issue_metadata.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(item, dict) and item.get("name") == "agent-task" for item in labels
    ):
        raise DispatchError("Live Issue no longer carries the agent-task label.")
    body = issue_metadata.get("body")
    if not isinstance(body, str):
        raise DispatchError("Live Issue body is missing.")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if digest != intake_artifact.get("issue_body_sha256"):
        raise DispatchError("Live Issue body changed after the intake artifact was created.")
    try:
        parsed_task = validate_issue_body(body, repository_metadata=repository_metadata)
    except GitHubTaskError as exc:
        raise DispatchError("Current Issue body no longer passes task protocol validation.") from exc
    if parsed_task != intake_artifact.get("task"):
        raise DispatchError("Current Issue task payload differs from the uploaded intake artifact.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--artifact-metadata-file", required=True)
    parser.add_argument("--repository-metadata-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args(argv)
    try:
        _, manifests = load_project_configuration(Path.cwd())
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        artifact_metadata = json.loads(Path(args.artifact_metadata_file).read_text(encoding="utf-8"))
        repository_metadata = json.loads(Path(args.repository_metadata_file).read_text(encoding="utf-8"))
        dispatch = validate_dispatch_event(event, manifests)
        result = validate_remote_metadata(
            dispatch, artifact_metadata=artifact_metadata,
            repository_metadata=repository_metadata,
        )
        Path(args.output_file).write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, ProjectRegistryError, IntakeError, DispatchError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"Validated artifact {result['artifact_id']} from {result['target_repository']} Issue #{result['issue_number']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
