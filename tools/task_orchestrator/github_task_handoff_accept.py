"""Accept a lease-verified GitHub handoff into a local task envelope.

This command rechecks the live Issue and lease through read-only GitHub APIs,
requires a clean dedicated branch at the exact pinned base SHA, then uses the
existing local Task Orchestrator to build its project-memory envelope. It does
not dispatch a model, upload source, or write to GitHub.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import stat
import urllib.parse
import zipfile
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import task_orchestrator as orchestrator
from .envelope_builder import EnvelopeBuildError, _repository_name
from .github_lease import LeaseError, lock_branch, validate_lease
from .github_task_pr_guard import GuardError, api_get
from .github_task_protocol import GitHubTaskError, validate_issue_body
from .github_issue_intake import (
    IntakeError, load_project_configuration, validate_task_project_binding,
)

SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class HandoffAcceptanceError(ValueError):
    """A downloaded handoff is stale, mismatched, or unsafe to accept."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HandoffAcceptanceError("Handoff JSON contains a duplicate key.")
        result[key] = value
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HandoffAcceptanceError(name + " must be a positive integer.")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise HandoffAcceptanceError(name + " must be timezone-aware ISO-8601 text.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandoffAcceptanceError(name + " is not valid ISO-8601 text.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HandoffAcceptanceError(name + " must include a timezone.")
    return parsed.astimezone(timezone.utc)


def validate_handoff_for_acceptance(
    manifest: Any,
    issue_data: Any,
    lease_record: Any,
    lock_commit: str,
    *,
    repository: str,
    repository_metadata: dict[str, Any],
    project_schema: dict[str, Any] | None = None,
    project_manifests: list[dict[str, Any]] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Bind the downloaded manifest to the current Issue and remote lease."""
    top_fields = {
        "handoff_schema", "handoff_id", "source", "repository", "issue",
        "task", "lease", "workflow", "execution",
    }
    if not isinstance(manifest, dict):
        raise HandoffAcceptanceError("Handoff manifest has unexpected or missing fields.")
    handoff_schema = manifest.get("handoff_schema")
    if isinstance(handoff_schema, bool) or handoff_schema not in {2, 3}:
        raise HandoffAcceptanceError("Unsupported handoff schema.")
    expected_fields = top_fields | ({"project_binding"} if handoff_schema == 3 else set())
    if set(manifest) != expected_fields:
        raise HandoffAcceptanceError("Handoff manifest has unexpected or missing fields.")
    if manifest["source"] != "github-issue" or manifest["repository"] != repository:
        raise HandoffAcceptanceError("Handoff source or repository identity does not match.")
    if not isinstance(manifest["task"], dict):
        raise HandoffAcceptanceError("Handoff task payload is malformed.")
    if (handoff_schema == 2 and manifest["task"].get("schema_version") != 1) or (
        handoff_schema == 3 and manifest["task"].get("schema_version") != 2
    ):
        raise HandoffAcceptanceError("Handoff schema and task payload version do not match.")
    task_id = manifest["task"].get("task_id")
    if not isinstance(task_id, str) or not orchestrator.TASK_ID_RE.fullmatch(task_id):
        raise HandoffAcceptanceError("Handoff task ID is invalid.")

    issue = manifest["issue"]
    if not isinstance(issue, dict) or set(issue) != {"number", "url", "body_sha256"}:
        raise HandoffAcceptanceError("Handoff Issue identity is malformed.")
    issue_number = _positive_int(issue["number"], "issue number")
    if not isinstance(issue["url"], str) or not issue["url"].startswith("https://github.com/"):
        raise HandoffAcceptanceError("Handoff Issue URL is invalid.")
    if not isinstance(issue["body_sha256"], str) or not DIGEST_RE.fullmatch(issue["body_sha256"]):
        raise HandoffAcceptanceError("Handoff Issue-body digest is invalid.")
    if not isinstance(issue_data, dict):
        raise HandoffAcceptanceError("Current GitHub Issue response is malformed.")
    if _positive_int(issue_data.get("number"), "current Issue number") != issue_number:
        raise HandoffAcceptanceError("Current GitHub Issue number does not match the handoff.")
    if issue_data.get("state") != "open" or issue_data.get("html_url") != issue["url"]:
        raise HandoffAcceptanceError("The task Issue is no longer open or its URL changed.")
    labels = issue_data.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(label, dict) and label.get("name") == "agent-task" for label in labels
    ):
        raise HandoffAcceptanceError("The current task Issue no longer has the agent-task label.")
    body = issue_data.get("body")
    if not isinstance(body, str) or hashlib.sha256(body.encode("utf-8")).hexdigest() != issue["body_sha256"]:
        raise HandoffAcceptanceError("Current Issue body differs from the handoff snapshot.")
    try:
        task = validate_issue_body(
            body, repository_metadata=repository_metadata, allow_legacy_jet_vpn=True
        )
    except GitHubTaskError as exc:
        raise HandoffAcceptanceError("Current Issue task payload is invalid.") from exc
    if task != manifest["task"]:
        raise HandoffAcceptanceError("Handoff task payload differs from the current Issue body.")
    if handoff_schema == 3:
        if not isinstance(project_schema, dict) or not isinstance(project_manifests, list):
            raise HandoffAcceptanceError("Trusted project manifest configuration is unavailable.")
        try:
            expected_binding = validate_task_project_binding(
                task, repository_metadata, schema=project_schema,
                project_manifests=project_manifests,
            )
        except IntakeError as exc:
            raise HandoffAcceptanceError("Current project binding failed trusted validation.") from exc
        if manifest.get("project_binding") != expected_binding:
            raise HandoffAcceptanceError("Handoff project binding differs from the trusted manifest.")

    workflow = manifest["workflow"]
    if not isinstance(workflow, dict) or set(workflow) != {"run_id", "run_attempt"}:
        raise HandoffAcceptanceError("Handoff workflow identity is malformed.")
    run_id = _positive_int(workflow["run_id"], "workflow run ID")
    run_attempt = _positive_int(workflow["run_attempt"], "workflow run attempt")
    expected_handoff_id = (
        "issue-" + str(issue_number) + "-run-" + str(run_id) +
        "-attempt-" + str(run_attempt)
    )
    if manifest["handoff_id"] != expected_handoff_id:
        raise HandoffAcceptanceError("Handoff ID does not match its Issue and workflow identity.")

    execution = manifest["execution"]
    expected_execution_fields = {
        "status", "agent_dispatched", "model_called", "source_uploaded", "patch_applied"
    }
    if (
        not isinstance(execution, dict)
        or set(execution) != expected_execution_fields
        or execution.get("status") != "ready-for-agent"
        or any(type(execution.get(key)) is not bool or execution[key] is not False
               for key in ("agent_dispatched", "model_called", "source_uploaded", "patch_applied"))
    ):
        raise HandoffAcceptanceError("Handoff execution flags are invalid or indicate prior execution.")

    lease = manifest["lease"]
    lease_fields = {
        "operation", "previous_claim_id", "owner", "claim_id", "status",
        "expires_at", "base_sha", "lock_branch", "lock_commit", "verified",
    }
    if not isinstance(lease, dict) or set(lease) != lease_fields:
        raise HandoffAcceptanceError("Handoff lease record is malformed.")
    try:
        current_lease = validate_lease(lease_record)
        expected_branch = lock_branch(task_id)
    except LeaseError as exc:
        raise HandoffAcceptanceError("Current remote lease record is invalid.") from exc
    if (
        lease["operation"] not in {"claim", "renew"}
        or (lease["operation"] == "claim" and lease["previous_claim_id"] is not None)
        or (lease["operation"] == "renew" and (
            not isinstance(lease["previous_claim_id"], str)
            or not re.fullmatch(r"[a-f0-9]{16,64}", lease["previous_claim_id"])
            or lease["previous_claim_id"] == lease["claim_id"]
        ))
        or lease["verified"] is not True
        or lease["status"] != "active"
        or lease["lock_branch"] != expected_branch
        or lease["lock_commit"] != lock_commit
        or not isinstance(lock_commit, str)
        or not SHA_RE.fullmatch(lock_commit)
    ):
        raise HandoffAcceptanceError("Handoff does not identify the current verified lock ref.")
    if (
        current_lease["task_id"] != task_id
        or current_lease["owner"] != lease["owner"]
        or current_lease["claim_id"] != lease["claim_id"]
        or current_lease["status"] != "active"
        or current_lease["base_sha"] != lease["base_sha"]
        or current_lease["expires_at"] != lease["expires_at"]
    ):
        raise HandoffAcceptanceError("Handoff lease differs from the current remote lease.")
    if task["assigned_agent"] not in {"any", lease["owner"]}:
        raise HandoffAcceptanceError("Task assignment does not match the active lease owner.")
    moment = _timestamp(now or datetime.now(timezone.utc).isoformat(), "now")
    if _timestamp(current_lease["expires_at"], "current lease expiry") <= moment:
        raise HandoffAcceptanceError("Current remote lease has expired.")
    if not isinstance(lease["base_sha"], str) or not SHA_RE.fullmatch(lease["base_sha"]):
        raise HandoffAcceptanceError("Pinned task base SHA is invalid.")
    return task


def _read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise HandoffAcceptanceError("Handoff file must be a regular non-symlink file.")
    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise HandoffAcceptanceError("Handoff file exceeds the 2 MB safety limit.")
    if raw.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                files = [item for item in archive.infolist() if not item.is_dir()]
                if len(files) != 1 or files[0].filename != "task-handoff.json":
                    raise HandoffAcceptanceError("Artifact ZIP must contain exactly one task-handoff.json file.")
                item = files[0]
                mode = (item.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK or item.file_size > 1_000_000:
                    raise HandoffAcceptanceError("Artifact entry is a symlink or exceeds the 1 MB limit.")
                raw = archive.read(item)
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise HandoffAcceptanceError("Artifact ZIP is malformed or cannot be read safely.") from exc
    if len(raw) > 1_000_000:
        raise HandoffAcceptanceError("Handoff JSON exceeds the 1 MB safety limit.")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffAcceptanceError("Handoff file is not valid UTF-8 JSON.") from exc



def _read_current_lease(repository: str, task_id: str, token: str) -> tuple[dict[str, Any], str]:
    """Read lease contents at one observed ref SHA and reject ref movement."""
    branch = lock_branch(task_id)
    ref_path = "/git/ref/heads/" + urllib.parse.quote(branch, safe="/-")
    before = api_get(repository, ref_path, token)
    try:
        lock_commit = before["object"]["sha"]
        lock_type = before["object"]["type"]
    except (TypeError, KeyError) as exc:
        raise HandoffAcceptanceError("Remote task lock ref is malformed.") from exc
    if lock_type != "commit" or not isinstance(lock_commit, str) or not SHA_RE.fullmatch(lock_commit):
        raise HandoffAcceptanceError("Remote task lock ref must point to a full commit SHA.")
    query = urllib.parse.urlencode({"ref": lock_commit})
    item = api_get(repository, "/contents/.agent-locks/lease.json?" + query, token)
    if not isinstance(item, dict) or item.get("encoding") != "base64" or not isinstance(item.get("content"), str):
        raise HandoffAcceptanceError("Remote lease content response is malformed.")
    try:
        raw = base64.b64decode("".join(item["content"].split()), validate=True)
        record = validate_lease(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, LeaseError) as exc:
        raise HandoffAcceptanceError("Remote lease record is invalid.") from exc
    after = api_get(repository, ref_path, token)
    try:
        after_sha = after["object"]["sha"]
    except (TypeError, KeyError) as exc:
        raise HandoffAcceptanceError("Remote task lock ref changed or became malformed.") from exc
    if after_sha != lock_commit:
        raise HandoffAcceptanceError("Remote lease ref moved during acceptance; retry with the newest handoff.")
    return record, lock_commit


def _handoff_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_number": manifest["issue"]["number"],
        "issue_url": manifest["issue"]["url"],
        "issue_body_sha256": manifest["issue"]["body_sha256"],
        "operation": manifest["lease"]["operation"],
        "previous_claim_id": manifest["lease"]["previous_claim_id"],
        "owner": manifest["lease"]["owner"],
        "claim_id": manifest["lease"]["claim_id"],
        "lease_expires_at": manifest["lease"]["expires_at"],
        "base_sha": manifest["lease"]["base_sha"],
        "lock_branch": manifest["lease"]["lock_branch"],
        "lock_commit": manifest["lease"]["lock_commit"],
        "workflow_run_id": manifest["workflow"]["run_id"],
        "workflow_run_attempt": manifest["workflow"]["run_attempt"],
    }


def _refresh_existing_task(
    root: Path,
    task_id: str,
    task: dict[str, Any],
    manifest: dict[str, Any],
    branch_name: str,
) -> Path:
    record, record_path = orchestrator.load_record(root, task_id)
    if record.get("state") not in {"prepared", "implementation", "verification", "review_ready"}:
        raise HandoffAcceptanceError("Only an already prepared task can refresh its lease handoff.")
    orchestrator.require_task_branch(root, record)
    repository_record = record.get("repository")
    scope = record.get("scope")
    old_handoff = record.get("github_handoff")
    if not isinstance(repository_record, dict) or not isinstance(scope, dict) or not isinstance(old_handoff, dict):
        raise HandoffAcceptanceError("Existing task is not linked to a verified GitHub handoff.")
    base_sha = manifest["lease"]["base_sha"]
    if (
        repository_record.get("base_sha") != base_sha
        or repository_record.get("branch") != branch_name
        or record.get("source") != "github-issue"
        or record.get("assigned_agent") != task["assigned_agent"]
        or record.get("goal") != task["goal"]
        or record.get("capability_improved") != task["capability"]
        or record.get("risk") != task["risk"]
        or record.get("planned_checks") != task["verification_profiles"]
        or scope.get("allowed") != sorted(set(task["allow"]))
        or scope.get("excluded") != sorted(set(task["exclude"]))
        or scope.get("reason") != task["scope_reason"]
    ):
        raise HandoffAcceptanceError("Renewed handoff no longer matches the existing local task definition.")
    stable_fields = ("issue_number", "issue_url", "issue_body_sha256", "owner", "base_sha", "lock_branch")
    new_metadata = _handoff_metadata(manifest)
    if manifest["handoff_schema"] == 3:
        expected_binding = {
            **manifest["project_binding"],
            "base_sha": manifest["lease"]["base_sha"],
        }
        if record.get("github_project_binding") != expected_binding:
            raise HandoffAcceptanceError("Project identity changed; explicit project migration is required.")
    elif record.get("github_project_binding") is not None:
        raise HandoffAcceptanceError("A project-aware task cannot be refreshed through a legacy handoff.")
    if new_metadata["operation"] != "renew" or old_handoff.get("claim_id") != new_metadata["previous_claim_id"]:
        raise HandoffAcceptanceError("Lease refresh must renew the exact claim recorded in this local task.")
    if any(old_handoff.get(key) != new_metadata[key] for key in stable_fields):
        raise HandoffAcceptanceError("Renewed handoff belongs to a different Issue, owner, body, or pinned base.")
    output = record_path.parent / "agent_input.json"
    if output.is_symlink() or not output.is_file():
        raise HandoffAcceptanceError("Existing local agent_input.json is missing or unsafe; refusing to refresh lease metadata.")
    record["github_handoff"] = new_metadata
    record["updated_at"] = orchestrator.now_iso()
    orchestrator.save_record(record, record_path)
    print("Refreshed lease handoff metadata on local branch " + branch_name + ".")
    print("Existing source changes and agent_input.json were not modified.")
    return output


def accept_handoff(
    handoff_path: Path,
    *,
    token: str,
    repository: str,
    refresh_existing: bool = False,
    create_branch: bool = False,
) -> Path:
    manifest = _read_json(handoff_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("issue"), dict):
        raise HandoffAcceptanceError("Handoff manifest is missing its Issue identity.")
    issue_number = _positive_int(manifest["issue"].get("number"), "issue number")
    task = manifest.get("task")
    task_id = task.get("task_id") if isinstance(task, dict) else None
    if not isinstance(task_id, str) or not orchestrator.TASK_ID_RE.fullmatch(task_id):
        raise HandoffAcceptanceError("Handoff task ID is invalid.")

    issue_data = api_get(repository, "/issues/" + str(issue_number), token)
    repository_metadata = api_get(repository, "", token)
    try:
        project_schema, project_manifests = load_project_configuration(Path(__file__).resolve().parents[2])
    except IntakeError as exc:
        raise HandoffAcceptanceError("Trusted project manifest configuration is unavailable.") from exc
    lease_record, lock_commit = _read_current_lease(repository, task_id, token)
    task = validate_handoff_for_acceptance(
        manifest, issue_data, lease_record, lock_commit, repository=repository,
        repository_metadata=repository_metadata, project_schema=project_schema,
        project_manifests=project_manifests,
    )

    root = orchestrator.repository_root()
    origin = orchestrator.safe_remote_identity(
        orchestrator.run_git(root, "remote", "get-url", "origin", check=False)
    )
    if _repository_name(origin) != repository:
        raise HandoffAcceptanceError("Local Git origin does not match the handoff repository.")
    base_sha = manifest["lease"]["base_sha"]
    current_branch = orchestrator.run_git(root, "branch", "--show-current")
    if create_branch:
        if refresh_existing:
            raise HandoffAcceptanceError("--create-branch cannot be combined with --refresh-existing.")
        if current_branch in orchestrator.PROTECTED_BRANCHES or not current_branch:
            dirty_before_switch = orchestrator.status_paths(root)
            if dirty_before_switch:
                raise HandoffAcceptanceError(
                    "Worktree must be clean before creating the task branch: " +
                    ", ".join(dirty_before_switch[:12])
                )
            new_branch = "agent/" + task_id
            if orchestrator.run_git(root, "branch", "--list", new_branch):
                raise HandoffAcceptanceError("Local task branch already exists; refusing to reuse it.")
            orchestrator.run_git(root, "switch", "-c", new_branch, base_sha)
    branch_name = orchestrator.current_branch(root)
    task_record_path = orchestrator.task_path(root, task_id)
    if task_record_path.exists() or task_record_path.is_symlink():
        if not refresh_existing:
            raise HandoffAcceptanceError(
                "A local task with this ID already exists; use --refresh-existing only for a verified lease renewal."
            )
        return _refresh_existing_task(root, task_id, task, manifest, branch_name)
    if refresh_existing:
        raise HandoffAcceptanceError("--refresh-existing requires an existing prepared local task.")

    head_sha = orchestrator.run_git(root, "rev-parse", "HEAD")
    if head_sha != base_sha:
        raise HandoffAcceptanceError(
            "Current branch HEAD must equal the handoff's pinned base SHA; create a fresh task branch from that exact commit."
        )
    dirty = orchestrator.status_paths(root)
    if dirty:
        raise HandoffAcceptanceError(
            "Worktree must be clean before accepting a handoff: " + ", ".join(dirty[:12])
        )

    try:
        orchestrator.build_context(
            root=root,
            task_id=task_id,
            source_revision=base_sha,
            required_paths=list(orchestrator.REQUIRED_CONTEXT),
            source_paths=[],
            allowed_patterns=task["allow"],
            excluded_patterns=task["exclude"],
        )
    except orchestrator.ContextBuildError as exc:
        raise HandoffAcceptanceError("Required project context is unavailable at the pinned base.") from exc

    init_args = Namespace(
        task_id=task_id,
        goal=task["goal"],
        capability=task["capability"],
        risk=task["risk"],
        allow=task["allow"],
        exclude=task["exclude"],
        scope_reason=task["scope_reason"],
        check=task["verification_profiles"],
        context=[],
    )
    orchestrator.command_init(init_args)
    orchestrator.command_prepare(Namespace(task_id=task_id))
    record, record_path = orchestrator.load_record(root, task_id)
    record["assigned_agent"] = task["assigned_agent"]
    record["source"] = "github-issue"
    record["github_handoff"] = _handoff_metadata(manifest)
    if manifest["handoff_schema"] == 3:
        record["github_project_binding"] = {
            **manifest["project_binding"],
            "base_sha": manifest["lease"]["base_sha"],
        }
    orchestrator.save_record(record, record_path)
    orchestrator.command_build_envelope(Namespace(task_id=task_id))
    output = record_path.parent / "agent_input.json"
    print("Accepted handoff on local branch " + branch_name + ".")
    print("Created local-only agent envelope: " + output.relative_to(root).as_posix())
    print("No model was invoked, no source was uploaded, and no remote Git ref was modified.")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-file", required=True)
    parser.add_argument("--refresh-existing", action="store_true",
                        help="Refresh only the lease metadata of an already prepared task after renewal.")
    parser.add_argument("--create-branch", action="store_true",
                        help="Create agent/<task-id> locally from the exact pinned base SHA when on the default branch.")
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    try:
        if not token:
            raise HandoffAcceptanceError("A read-only GitHub token is required in GITHUB_TOKEN or GH_TOKEN.")
        output = accept_handoff(
            Path(args.handoff_file), token=token, repository=repository,
            refresh_existing=args.refresh_existing,
            create_branch=args.create_branch,
        )
    except (
        OSError, HandoffAcceptanceError, GuardError, LeaseError,
        GitHubTaskError, orchestrator.TaskError, EnvelopeBuildError,
    ) as exc:
        parser.error(str(exc))
    print("Agent input ready: " + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
