"""Idempotent, read-only ingestion of validated GitHub Issue task artifacts.

This module consumes an artifact already retrieved from a trusted GitHub Actions
run. It does not fetch remote artifacts, claim leases, invoke agents, or execute
task code. The caller is responsible for authenticating the artifact's workflow
run before passing its bytes here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .github_issue_intake import IntakeError, load_project_configuration, validate_task_project_binding
    from .github_task_protocol import GitHubTaskError, validate_task_payload
    from .project_registry import ProjectRegistryError, loads_unique_json
    from .safe_local_files import SafeLocalFileError, atomic_write_bytes, ensure_directory, read_bytes
except ImportError:
    from github_issue_intake import IntakeError, load_project_configuration, validate_task_project_binding
    from github_task_protocol import GitHubTaskError, validate_task_payload
    from project_registry import ProjectRegistryError, loads_unique_json
    from safe_local_files import SafeLocalFileError, atomic_write_bytes, ensure_directory, read_bytes

MAX_ARTIFACT_BYTES = 256_000
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
REPOSITORY_ID_RE = re.compile(r"^[0-9]{1,20}$")


class InboxError(ValueError):
    """A task artifact is invalid, conflicting, or unsafe to persist."""


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise InboxError("Intake artifact cannot be represented as canonical JSON.") from exc


def _validate_artifact(artifact: Any, *, repository_metadata: dict[str, Any],
                       project_schema: dict[str, Any],
                       project_manifests: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], str]:
    required_fields = {
        "intake_schema", "source", "repository", "issue_number", "issue_url",
        "issue_title", "issue_body_sha256", "task", "execution",
        "project_binding", "project_lifecycle", "implementation_eligible",
    }
    if not isinstance(artifact, dict) or set(artifact) != required_fields or artifact.get("intake_schema") != 2:
        raise InboxError("Only complete, exact-schema v2 GitHub Issue intake artifacts are accepted.")
    if artifact.get("source") != "github-issue":
        raise InboxError("Artifact source must be a validated GitHub Issue.");
    repository, number = artifact.get("repository"), artifact.get("issue_number")
    title, issue_url, body_digest = artifact.get("issue_title"), artifact.get("issue_url"), artifact.get("issue_body_sha256")
    if repository != repository_metadata.get("full_name"):
        raise InboxError("Artifact repository does not match trusted GitHub repository metadata.")
    raw_repo_id = repository_metadata.get("id")
    if isinstance(raw_repo_id, bool) or not isinstance(raw_repo_id, (str, int)):
        raise InboxError("Trusted repository metadata has no immutable numeric ID.")
    repository_id = str(raw_repo_id)
    if not REPOSITORY_ID_RE.fullmatch(repository_id):
        raise InboxError("Trusted immutable repository ID is malformed.")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise InboxError("Artifact Issue number is invalid.")
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise InboxError("Artifact Issue title is invalid.")
    if issue_url != f"https://github.com/{repository}/issues/{number}":
        raise InboxError("Artifact Issue URL is not canonical for its repository and number.")
    if not isinstance(body_digest, str) or not DIGEST_RE.fullmatch(body_digest):
        raise InboxError("Artifact Issue body fingerprint is malformed.")

    task_raw = artifact.get("task")
    try:
        task = validate_task_payload(task_raw, repository_metadata=repository_metadata)
    except GitHubTaskError as exc:
        raise InboxError("Embedded task payload failed protocol validation.") from exc
    if task.get("schema_version") != 2 or task != task_raw:
        raise InboxError("Embedded task payload must be canonical, explicitly project-bound v2.")
    try:
        binding = validate_task_project_binding(
            task, repository_metadata, schema=project_schema,
            project_manifests=project_manifests, require_active=False,
        )
    except IntakeError as exc:
        raise InboxError("Embedded project binding failed trusted manifest validation.") from exc
    if artifact.get("project_binding") != binding:
        raise InboxError("Top-level project binding differs from the validated task binding.")
    manifest = next(item for item in project_manifests if item.get("project_id") == binding["project_id"])
    lifecycle = manifest.get("lifecycle")
    eligible = lifecycle == "active"
    if artifact.get("project_lifecycle") != lifecycle or artifact.get("implementation_eligible") is not eligible:
        raise InboxError("Artifact lifecycle or implementation eligibility differs from the trusted manifest.")
    execution = artifact.get("execution")
    expected_status = "validated-awaiting-claim" if eligible else "validated-awaiting-activation"
    if not isinstance(execution, dict) or execution.get("status") != expected_status:
        raise InboxError("Artifact execution state is inconsistent with project lifecycle.")
    for flag in ("lease_claimed", "agent_dispatched", "model_called", "source_uploaded"):
        if execution.get(flag) is not False:
            raise InboxError(f"Read-only intake artifact has unsafe execution flag: {flag}.")
    return task, binding, repository_id


def ingest_artifact_bytes(raw: bytes, *, root: Path, repository_metadata: dict[str, Any],
                          project_schema: dict[str, Any],
                          project_manifests: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate and create one durable central inbox record; repeated imports are no-ops."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ARTIFACT_BYTES:
        raise InboxError("Artifact must be non-empty bytes within the configured size limit.")
    try:
        artifact = loads_unique_json(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, ProjectRegistryError) as exc:
        raise InboxError("Artifact is not valid unique-key UTF-8 JSON.") from exc
    task, binding, repository_id = _validate_artifact(
        artifact, repository_metadata=repository_metadata,
        project_schema=project_schema, project_manifests=project_manifests,
    )
    issue_number, task_id = artifact["issue_number"], task["task_id"]
    queue_key = f"{repository_id}:{issue_number}:{task_id}"
    artifact_sha256 = hashlib.sha256(_canonical(artifact)).hexdigest()
    relative_directory = f".agent/inbox/{repository_id}"
    relative_path = f"{relative_directory}/{issue_number}.json"
    record = {
        "schema_version": 1, "queue_key": queue_key,
        "repository_id": repository_id, "repository": binding["repository_full_name"],
        "project_id": binding["project_id"], "issue_number": issue_number,
        "task_id": task_id, "manifest_sha256": binding["manifest_sha256"],
        "artifact_sha256": artifact_sha256,
        "queue_status": "awaiting_claim" if artifact["implementation_eligible"] else "awaiting_activation",
        "intake_artifact": artifact,
    }
    encoded = _canonical(record)
    try:
        ensure_directory(root, relative_directory)
        try:
            existing = read_bytes(root, relative_path, max_bytes=MAX_ARTIFACT_BYTES * 2)
        except SafeLocalFileError:
            existing = None
        # A task ID is unique within an immutable repository identity, even if
        # someone attempts to submit it through a second Issue number.
        inbox_dir = root / relative_directory
        with os.scandir(inbox_dir) as entries:
            for entry in entries:
                if entry.name == f"{issue_number}.json" or not entry.name.endswith(".json"):
                    continue
                if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                    raise InboxError("Central inbox contains an unsafe non-regular entry.")
                other_path = f"{relative_directory}/{entry.name}"
                try:
                    other = loads_unique_json(read_bytes(root, other_path, max_bytes=MAX_ARTIFACT_BYTES * 2).decode("utf-8"))
                except (SafeLocalFileError, UnicodeDecodeError, ProjectRegistryError) as exc:
                    raise InboxError("A neighboring inbox record is unreadable; refusing duplicate checks.") from exc
                if other.get("task_id") == task_id:
                    raise InboxError("This task_id is already registered for another Issue in the same repository.")
        if existing is not None:
            try:
                old = loads_unique_json(existing.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, ProjectRegistryError) as exc:
                raise InboxError("Existing inbox record is corrupt; refusing to overwrite it.") from exc
            if old.get("queue_key") != queue_key:
                raise InboxError("This repository/Issue already has a different task identity.")
            if old.get("artifact_sha256") == artifact_sha256 and existing == encoded:
                return {"status": "already_ingested", "path": relative_path, "queue_key": queue_key}
            raise InboxError("A different artifact already occupies this repository/Issue key; manual reconciliation is required.")
        atomic_write_bytes(root, relative_path, encoded, replace=False, create_parents=True)
    except SafeLocalFileError as exc:
        raise InboxError("Central inbox record could not be persisted safely.") from exc
    return {"status": "ingested", "path": relative_path, "queue_key": queue_key}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, help="Path to a downloaded task.json artifact.")
    parser.add_argument("--repository-metadata", required=True, help="Path to trusted GitHub repository metadata JSON.")
    args = parser.parse_args(argv)
    root = Path.cwd()
    try:
        artifact_bytes = Path(args.artifact).read_bytes()
        metadata = loads_unique_json(Path(args.repository_metadata).read_text(encoding="utf-8"))
        schema, manifests = load_project_configuration(root)
        if not isinstance(metadata, dict):
            raise InboxError("Trusted repository metadata must be a JSON object.")
        result = ingest_artifact_bytes(
            artifact_bytes, root=root, repository_metadata=metadata,
            project_schema=schema, project_manifests=manifests,
        )
    except (OSError, UnicodeError, ProjectRegistryError, IntakeError, InboxError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("No lease claimed; no model or implementation agent was invoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
