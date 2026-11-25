"""Fail-closed live authorization gate before agent patches enter human review."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from .github_lease import LeaseError, lock_branch, validate_lease
from .github_task_protocol import GitHubTaskError, validate_issue_body
from .github_issue_intake import IntakeError, validate_task_project_binding
from .patch_artifacts import LocalPatchArtifactStore, PatchArtifactError

SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

class PatchReviewGateError(ValueError):
    """A proposed patch is not authorized for human review."""

def _moment(value: str) -> datetime:
    if not isinstance(value, str):
        raise PatchReviewGateError("Current time must be timezone-aware ISO-8601 text.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PatchReviewGateError("Current time is invalid.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PatchReviewGateError("Current time must include a timezone.")
    return parsed.astimezone(timezone.utc)

def validate_patch_for_human_review(record: Any, envelope: Any, result: Any,
        store: LocalPatchArtifactStore, issue_data: Any, lease_record: Any,
        lock_commit: str, *, repository: str, repository_metadata: dict[str, Any],
        project_schema: dict[str, Any] | None = None,
        project_manifests: list[dict[str, Any]] | None = None,
        branch: str, head_sha: str, base_is_ancestor: bool,
        worktree_clean: bool, now: str) -> dict[str, Any]:
    """Bind current Issue/lease/workspace observations and exact patch bytes to one task.

    The caller obtains live GitHub and Git observations through trusted adapters.
    This function performs no network, Git, write, patch-application, or execution.
    """
    if not isinstance(record, dict):
        raise PatchReviewGateError("Local task record must be an object.")
    if record.get("state") not in {"prepared", "implementation", "verification", "review_ready"}:
        raise PatchReviewGateError("Task state does not permit patch review.")
    task_id = record.get("task_id")
    if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", task_id):
        raise PatchReviewGateError("Local task ID is invalid.")
    repo = record.get("repository")
    scope = record.get("scope")
    handoff = record.get("github_handoff")
    if not all(isinstance(x, dict) for x in (repo, scope, handoff)):
        raise PatchReviewGateError("Task is not linked to a verified GitHub handoff.")
    base_sha, expected_branch = repo.get("base_sha"), repo.get("branch")
    if not isinstance(base_sha, str) or not SHA_RE.fullmatch(base_sha):
        raise PatchReviewGateError("Pinned base SHA is invalid.")
    if not isinstance(expected_branch, str) or branch != expected_branch:
        raise PatchReviewGateError("Workspace branch differs from the task branch.")
    if not isinstance(head_sha, str) or not SHA_RE.fullmatch(head_sha):
        raise PatchReviewGateError("Workspace HEAD is invalid.")
    if base_is_ancestor is not True:
        raise PatchReviewGateError("Pinned base is no longer an ancestor of workspace HEAD.")
    if worktree_clean is not True:
        raise PatchReviewGateError("Workspace is dirty; refusing ambiguous patch review.")

    if not isinstance(envelope, dict) or envelope.get("task_id") != task_id:
        raise PatchReviewGateError("Agent envelope does not belong to this task.")
    envelope_repo, envelope_scope = envelope.get("repository"), envelope.get("scope")
    if not isinstance(envelope_repo, dict) or not isinstance(envelope_scope, dict):
        raise PatchReviewGateError("Agent envelope repository or scope is malformed.")
    if (envelope.get("goal") != record.get("goal")
        or envelope.get("capability") != record.get("capability_improved")
        or envelope.get("risk") != record.get("risk")
        or envelope_repo.get("name") != repository
        or envelope_repo.get("branch") != expected_branch
        or envelope_repo.get("base_sha") != base_sha
        or envelope_scope.get("allowed_paths") != scope.get("allowed")
        or envelope_scope.get("excluded_paths") != scope.get("excluded")):
        raise PatchReviewGateError("Agent envelope differs from the prepared task.")

    if not isinstance(issue_data, dict):
        raise PatchReviewGateError("Current GitHub Issue response is malformed.")
    issue_number = handoff.get("issue_number")
    if (isinstance(issue_number, bool) or not isinstance(issue_number, int)
        or issue_data.get("number") != issue_number
        or issue_data.get("state") != "open"
        or issue_data.get("html_url") != handoff.get("issue_url")):
        raise PatchReviewGateError("Task Issue is closed or no longer matches the handoff.")
    labels = issue_data.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(x, dict) and x.get("name") == "agent-task" for x in labels
    ):
        raise PatchReviewGateError("Current Issue no longer has the agent-task label.")
    body = issue_data.get("body")
    if not isinstance(body, str) or hashlib.sha256(body.encode("utf-8")).hexdigest() != handoff.get("issue_body_sha256"):
        raise PatchReviewGateError("Current Issue body differs from the accepted handoff.")
    try:
        task = validate_issue_body(
            body, repository_metadata=repository_metadata, allow_legacy_jet_vpn=True
        )
    except GitHubTaskError as exc:
        raise PatchReviewGateError("Current Issue task payload is invalid.") from exc
    if task["schema_version"] == 2:
        if not isinstance(project_schema, dict) or not isinstance(project_manifests, list):
            raise PatchReviewGateError("Trusted project manifest configuration is unavailable.")
        try:
            binding = validate_task_project_binding(
                task, repository_metadata, schema=project_schema,
                project_manifests=project_manifests,
            )
            project_binding = binding
        except IntakeError as exc:
            raise PatchReviewGateError("Current project binding is invalid or inactive.") from exc
        expected_binding = dict(binding, base_sha=base_sha)
        if record.get("github_project_binding") != expected_binding:
            raise PatchReviewGateError("Persisted project identity or pinned base SHA differs from the current task.")
    elif record.get("github_project_binding") is not None:
        raise PatchReviewGateError("A project-aware task cannot be reviewed through a legacy v1 task body.")
    if (task["task_id"] != task_id or task["goal"] != record.get("goal")
        or task["capability"] != record.get("capability_improved")
        or task["risk"] != record.get("risk")
        or task["assigned_agent"] != record.get("assigned_agent")
        or task["allow"] != scope.get("allowed")
        or task["exclude"] != scope.get("excluded")
        or task["scope_reason"] != scope.get("reason")
        or task["verification_profiles"] != record.get("planned_checks")):
        raise PatchReviewGateError("Current Issue task definition differs from the local task.")

    try:
        lease = validate_lease(lease_record)
        expected_lock = lock_branch(task_id, project_binding)
    except LeaseError as exc:
        raise PatchReviewGateError("Current remote lease is invalid.") from exc
    if not isinstance(lock_commit, str) or not SHA_RE.fullmatch(lock_commit):
        raise PatchReviewGateError("Observed lock-ref commit SHA is invalid.")
    if (lease["task_id"] != task_id or lease["owner"] != handoff.get("owner")
        or lease["claim_id"] != handoff.get("claim_id") or lease["status"] != "active"
        or lease["base_sha"] != base_sha or handoff.get("base_sha") != base_sha
        or lease.get("project_binding") != project_binding
        or handoff.get("lock_branch") != expected_lock
        or handoff.get("lock_commit") != lock_commit
        or task["assigned_agent"] not in {"any", lease["owner"]}):
        raise PatchReviewGateError("Current remote lease does not match the accepted claim.")
    if _moment(lease["expires_at"]) <= _moment(now):
        raise PatchReviewGateError("Current task lease has expired.")
    if _moment(handoff.get("lease_expires_at")) != _moment(lease["expires_at"]):
        raise PatchReviewGateError("Lease expiry differs from the accepted handoff; renew and re-accept.")

    try:
        validated = store.validate_result_patch(result, envelope)
    except PatchArtifactError as exc:
        raise PatchReviewGateError("Patch artifact failed integrity, contract, or scope validation.") from exc
    return {
        "task_id": task_id, "issue_number": issue_number,
        "patch_ref": validated["patch_ref"],
        "patch_validation": validated["patch_validation"],
        "status": "ready_for_human_review", "applied": False,
        "authorization": {"issue_current": True, "lease_active": True,
            "lease_ref_current": True, "pinned_base_is_ancestor": True,
            "workspace_clean": True, "branch_matches": True},
        "workspace_head_sha": head_sha, "pinned_base_sha": base_sha,
    }
