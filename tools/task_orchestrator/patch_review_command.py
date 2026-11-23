"""Read-only CLI that connects live GitHub/Git observations to the patch review gate.

The command does not apply patches, run verification profiles, or write to GitHub.
It prints a machine-readable authorization result for human review only.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import task_orchestrator as orchestrator
from .envelope_builder import _repository_name
from .github_task_handoff_accept import _read_current_lease
from .github_task_pr_guard import api_get
from .patch_artifacts import LocalPatchArtifactStore, PatchArtifactError
from .patch_review_gate import PatchReviewGateError, validate_patch_for_human_review


class PatchReviewCommandError(RuntimeError):
    """The live review command could not establish trusted observations."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PatchReviewCommandError("JSON input contains a duplicate key.")
        result[key] = value
    return result


def _read_json_object(path: Path, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    """Read a bounded regular file without following a final-component symlink."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PatchReviewCommandError("Required JSON input is missing or unsafe: " + path.name) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size < 1 or metadata.st_size > max_bytes:
            raise PatchReviewCommandError("JSON input must be a non-empty regular file within the size limit.")
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(max_bytes + 1)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    if len(raw) != metadata.st_size or len(raw) > max_bytes:
        raise PatchReviewCommandError("JSON input changed while being read or exceeds the size limit.")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PatchReviewCommandError("JSON input is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise PatchReviewCommandError("JSON input must contain an object.")
    return value


def _base_is_ancestor(root: Path, base_sha: str, head_sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, head_sha],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, shell=False,
    )
    if result.returncode not in {0, 1}:
        raise PatchReviewCommandError("Git could not establish pinned-base ancestry.")
    return result.returncode == 0


def _inside_task_directory(root: Path, task_dir: Path, supplied: Path) -> Path:
    if supplied.is_symlink():
        raise PatchReviewCommandError("Result and artifact paths must not be symlinks.")
    resolved = supplied.resolve(strict=True)
    try:
        resolved.relative_to(task_dir.resolve(strict=True))
    except ValueError as exc:
        raise PatchReviewCommandError("Result and artifact paths must remain inside this task directory.") from exc
    if resolved == task_dir.resolve(strict=True):
        raise PatchReviewCommandError("A file or artifact-store path is required, not the task directory itself.")
    return resolved


def review_task_patch(
    task_id: str,
    *,
    result_path: Path | None = None,
    artifact_dir: Path | None = None,
    token: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Fetch current remote facts and validate the exact local patch artifact."""
    if not orchestrator.TASK_ID_RE.fullmatch(task_id):
        raise PatchReviewCommandError("Invalid task ID.")
    root = orchestrator.repository_root()
    record, record_path = orchestrator.load_record(root, task_id)
    task_dir = record_path.parent
    handoff = record.get("github_handoff")
    if not isinstance(handoff, dict):
        raise PatchReviewCommandError("Task has no accepted GitHub handoff.")
    issue_number = handoff.get("issue_number")
    if isinstance(issue_number, bool) or not isinstance(issue_number, int) or issue_number < 1:
        raise PatchReviewCommandError("Task handoff Issue number is invalid.")

    origin = orchestrator.safe_remote_identity(
        orchestrator.run_git(root, "remote", "get-url", "origin", check=False)
    )
    repository = _repository_name(origin)
    if not repository:
        raise PatchReviewCommandError("Git origin is not a recognized GitHub repository.")
    auth = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not isinstance(auth, str) or not auth.strip():
        raise PatchReviewCommandError("Set GITHUB_TOKEN or GH_TOKEN with read-only access to this repository.")

    issue_data = api_get(repository, "/issues/" + str(issue_number), auth)
    lease_record, lock_commit = _read_current_lease(repository, task_id, auth)

    branch = orchestrator.current_branch(root)
    head_sha = orchestrator.run_git(root, "rev-parse", "HEAD")
    base_sha = record.get("repository", {}).get("base_sha")
    if not isinstance(base_sha, str):
        raise PatchReviewCommandError("Task has no pinned base SHA.")
    base_is_ancestor = _base_is_ancestor(root, base_sha, head_sha)
    worktree_clean = not orchestrator.status_paths(root)

    envelope_file = task_dir / "agent_input.json"
    result_file = result_path or (task_dir / "agent_result.json")
    artifact_root = artifact_dir or (task_dir / "patch-artifacts")
    result_file = _inside_task_directory(root, task_dir, result_file)
    artifact_root = _inside_task_directory(root, task_dir, artifact_root)
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise PatchReviewCommandError("Patch artifact directory must already exist and must not be a symlink.")

    envelope = _read_json_object(envelope_file)
    result = _read_json_object(result_file)
    try:
        store = LocalPatchArtifactStore(artifact_root)
        return validate_patch_for_human_review(
            record, envelope, result, store, issue_data, lease_record, lock_commit,
            repository=repository, branch=branch, head_sha=head_sha,
            base_is_ancestor=base_is_ancestor, worktree_clean=worktree_clean,
            now=now or datetime.now(timezone.utc).isoformat(),
        )
    except (PatchArtifactError, PatchReviewGateError) as exc:
        raise PatchReviewCommandError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--result-file", help="Task-local JSON result; defaults to .agent/tasks/<id>/agent_result.json")
    parser.add_argument("--artifact-dir", help="Task-local patch artifact directory; defaults to .agent/tasks/<id>/patch-artifacts")
    args = parser.parse_args(argv)
    try:
        result = review_task_patch(
            args.task_id,
            result_path=Path(args.result_file) if args.result_file else None,
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
    except (PatchReviewCommandError, orchestrator.TaskError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Human review only: no patch was applied, no verification command was run, and no GitHub state was changed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
