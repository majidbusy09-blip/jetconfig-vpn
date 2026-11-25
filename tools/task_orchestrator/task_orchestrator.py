#!/usr/bin/env python3
"""Auditable, fail-closed task workflow for the JET VPN repository.

This tool records engineering work and runs a small allowlist of fixed checks.
It deliberately has no GitHub write, commit, push, merge, release, or deploy API.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    from .context_builder import ContextBuildError, build_context
except ImportError:
    try:
        from tools.task_orchestrator.context_builder import ContextBuildError, build_context
    except ImportError:
        from context_builder import ContextBuildError, build_context

try:
    from .project_cache_store import build_context_cached
except ImportError:
    try:
        from tools.task_orchestrator.project_cache_store import build_context_cached
    except ImportError:
        from project_cache_store import build_context_cached

try:
    from .envelope_builder import EnvelopeBuildError, build_agent_envelope
except ImportError:
    try:
        from tools.task_orchestrator.envelope_builder import EnvelopeBuildError, build_agent_envelope
    except ImportError:
        from envelope_builder import EnvelopeBuildError, build_agent_envelope

try:
    from .context_selector import ContextSelectionError, select_context
except ImportError:
    try:
        from tools.task_orchestrator.context_selector import ContextSelectionError, select_context
    except ImportError:
        from context_selector import ContextSelectionError, select_context

try:
    from .impact_analyzer import ImpactAnalysisError, analyze_impact
except ImportError:
    try:
        from tools.task_orchestrator.impact_analyzer import ImpactAnalysisError, analyze_impact
    except ImportError:
        from impact_analyzer import ImpactAnalysisError, analyze_impact


try:
    from .project_artifact_namespace import index_output_paths, ensure_namespace_directory
except ImportError:
    try:
        from tools.task_orchestrator.project_artifact_namespace import index_output_paths, ensure_namespace_directory
    except ImportError:
        from project_artifact_namespace import index_output_paths, ensure_namespace_directory

try:
    from .project_namespace import (
        ProjectNamespaceError, local_task_branch, task_record_directory,
        task_record_path as project_task_record_path,
    )
except ImportError:
    try:
        from tools.task_orchestrator.project_namespace import (
            ProjectNamespaceError, local_task_branch, task_record_directory,
            task_record_path as project_task_record_path,
        )
    except ImportError:
        from project_namespace import (
            ProjectNamespaceError, local_task_branch, task_record_directory,
            task_record_path as project_task_record_path,
        )

try:
    from .safe_local_files import SafeLocalFileError, atomic_write_bytes, ensure_directory, read_bytes
except ImportError:
    try:
        from tools.task_orchestrator.safe_local_files import (
            SafeLocalFileError, atomic_write_bytes, ensure_directory, read_bytes,
        )
    except ImportError:
        from safe_local_files import SafeLocalFileError, atomic_write_bytes, ensure_directory, read_bytes

SCHEMA_VERSION = 1
REQUIRED_CONTEXT = (
    "AGENTS.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/CURRENT_STATUS.md",
    "docs/NEXT_STEPS.md",
    "docs/TASK_TEMPLATE.md",
    "docs/DEVELOPMENT_LOG.md",
)
PROTECTED_BRANCHES = {"main", "master"}
TASK_DIR = Path(".agent/tasks")
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
PROFILES = {
    "python-tooling-tests": {
        "argv": [sys.executable, "-m", "unittest", "discover", "-s",
                 "tools/task_orchestrator/tests", "-p", "test_*.py"],
        "timeout": 180,
    },
    "flutter-tests": {"argv": ["flutter", "test", "--no-pub"], "timeout": 900},
    "flutter-analysis": {
        "argv": ["flutter", "analyze", "lib", "test", "--no-pub",
                 "--no-fatal-infos", "--no-fatal-warnings"],
        "timeout": 900,
    },
    "lexical-memory-audit": {
        "argv": [sys.executable, "tools/project_memory/index_dart.py",
                 "--check", "--check-status"],
        "timeout": 180,
    },
}


class TaskError(Exception):
    """A policy or task-state gate rejected the requested operation."""


def run_git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, shell=False,
    )
    if check and result.returncode:
        raise TaskError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def repository_root(start: Path | None = None) -> Path:
    cwd = start or Path.cwd()
    try:
        return Path(run_git(cwd, "rev-parse", "--show-toplevel")).resolve()
    except (TaskError, OSError) as exc:
        raise TaskError("Run this command inside a Git working tree.") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()



def _assert_safe_task_path(root: Path, path: Path) -> None:
    root_abs = root.absolute()
    path_abs = path.absolute()
    try:
        relative = path_abs.relative_to(root_abs)
    except ValueError as exc:
        raise TaskError("Task metadata path escapes the repository root.") from exc
    cursor = root_abs
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise TaskError("Task metadata path contains a symlink; refusing traversal.")
    if path_abs.exists() and not path_abs.is_file():
        raise TaskError("Task metadata target is not a regular file.")


def task_path(root: Path, task_id: str, project_binding: dict[str, Any] | None = None) -> Path:
    try:
        relative = project_task_record_path(task_id, project_binding)
    except ProjectNamespaceError as exc:
        raise TaskError(str(exc)) from exc
    path = root / relative
    _assert_safe_task_path(root, path)
    return path


def _candidate_task_paths(root: Path, task_id: str) -> list[Path]:
    tasks_root = root / TASK_DIR
    if tasks_root.is_symlink():
        raise TaskError("Task metadata root is a symlink; refusing traversal.")
    _assert_safe_task_path(root, tasks_root / "_scan")
    if not tasks_root.is_dir():
        return []
    candidates: list[Path] = []
    legacy = tasks_root / task_id / "task.json"
    if legacy.is_symlink():
        raise TaskError("Legacy task record is a symlink; refusing traversal.")
    if legacy.is_file():
        candidates.append(legacy)
    try:
        with os.scandir(tasks_root) as project_entries:
            for project_entry in project_entries:
                if project_entry.is_symlink():
                    raise TaskError("Project task namespace contains a symlink; refusing ambiguous lookup.")
                if not project_entry.is_dir(follow_symlinks=False):
                    continue
                with os.scandir(project_entry.path) as repository_entries:
                    for repository_entry in repository_entries:
                        if repository_entry.is_symlink():
                            raise TaskError("Repository task namespace contains a symlink; refusing ambiguous lookup.")
                        if not repository_entry.is_dir(follow_symlinks=False):
                            continue
                        task_dir = Path(repository_entry.path) / task_id
                        if task_dir.is_symlink():
                            raise TaskError("Namespaced task directory is a symlink; refusing traversal.")
                        candidate = task_dir / "task.json"
                        if candidate.is_symlink():
                            raise TaskError("Namespaced task record is a symlink; refusing traversal.")
                        if candidate.is_file():
                            candidates.append(candidate)
    except OSError as exc:
        raise TaskError("Unable to enumerate project-scoped task records safely.") from exc
    return sorted(candidates)


def load_record(
    root: Path, task_id: str, project_binding: dict[str, Any] | None = None
) -> tuple[dict[str, Any], Path]:
    if not TASK_ID_RE.fullmatch(task_id):
        raise TaskError("Invalid task ID; use 3-64 lowercase letters, digits, and hyphens.")
    if project_binding is not None:
        path = task_path(root, task_id, project_binding)
        candidates = [path] if path.is_file() else []
    else:
        candidates = _candidate_task_paths(root, task_id)
        if len(candidates) > 1:
            raise TaskError(
                f"Task ID '{task_id}' exists in multiple projects; provide an explicit project binding."
            )
        path = candidates[0] if candidates else task_path(root, task_id)
    if not candidates:
        raise TaskError(f"Task record not found: {path.relative_to(root)}")
    _assert_safe_task_path(root, path)
    try:
        raw = read_bytes(root, path.relative_to(root).as_posix(), max_bytes=2_000_000)
        record = json.loads(raw.decode("utf-8", errors="strict"))
    except (SafeLocalFileError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskError(f"Task record is unreadable or unsafe: {exc}") from exc
    if not isinstance(record, dict):
        raise TaskError("Task record must be a JSON object.")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("task_id") != task_id:
        raise TaskError("Unsupported or inconsistent task record schema.")
    record_binding = record.get("github_project_binding")
    if record_binding is not None:
        expected_path = task_path(root, task_id, record_binding)
        if expected_path != path:
            raise TaskError("Task record project identity does not match its storage namespace.")
    elif path != task_path(root, task_id):
        raise TaskError("A legacy task record cannot reside in a project-scoped directory.")
    if project_binding is not None and record_binding != project_binding:
        raise TaskError("Task record project binding does not match the requested project.")
    return record, path


def save_record(record: dict[str, Any], path: Path, *, create_only: bool = False) -> None:
    root = repository_root()
    _assert_safe_task_path(root, path)
    try:
        relative = path.relative_to(root).as_posix()
        parent = path.parent.relative_to(root).as_posix()
        ensure_directory(root, parent)
        encoded = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        atomic_write_bytes(root, relative, encoded, replace=not create_only)
    except (ValueError, SafeLocalFileError, UnicodeEncodeError) as exc:
        raise TaskError(f"Task record could not be saved safely: {exc}") from exc


def status_paths(root: Path) -> list[str]:
    raw = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False,
    )
    if raw.returncode:
        raise TaskError(f"Unable to inspect worktree: {raw.stderr.decode(errors='replace')}")
    # Porcelain -z uses a second NUL-delimited path for rename/copy records.
    fields = raw.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        item = fields[index]
        path = item[3:]
        paths.append(path)
        if item[:2].strip() in {"R", "C"} and index + 1 < len(fields):
            index += 1
            paths.append(fields[index])
        index += 1
    return sorted(set(paths))


def is_task_metadata(
    path: str, task_id: str, project_binding: dict[str, Any] | None = None
) -> bool:
    # Only the orchestrator-owned files inside this exact task namespace are exempt.
    try:
        base = task_record_directory(task_id, project_binding)
    except ProjectNamespaceError:
        return False
    if path in {f"{base}/task.json", f"{base}/HANDOFF.md", f"{base}/agent_input.json", f"{base}/impact_report.json"}:
        return True
    return path.startswith(f"{base}/context_suggestions_") and path.endswith(".json")


def clean_before_init(root: Path) -> None:
    paths = status_paths(root)
    if paths:
        raise TaskError(
            "Worktree must be clean before creating a task record; existing changes: "
            + ", ".join(paths[:12])
        )


def current_branch(root: Path) -> str:
    branch = run_git(root, "branch", "--show-current")
    if not branch:
        raise TaskError("Detached HEAD is not permitted for task preparation.")
    protected = set(PROTECTED_BRANCHES)
    remote_head = run_git(
        root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD",
        check=False,
    )
    if remote_head.startswith("origin/"):
        protected.add(remote_head[len("origin/"):])
    if branch in protected:
        raise TaskError(f"Refusing to prepare work directly on protected/default branch '{branch}'.")
    return branch


def safe_remote_identity(remote: str) -> str | None:
    """Keep repository identity while stripping URL credentials and query tokens."""
    if not remote:
        return None
    if "://" in remote:
        parsed = urlsplit(remote)
        host = parsed.hostname or ""
        try:
            if parsed.port:
                host += f":{parsed.port}"
        except ValueError:
            pass
        return f"{parsed.scheme}://{host}{parsed.path}"
    # SCP-style SSH remotes commonly look like git@github.com:owner/repo.git.
    if "@" in remote and ":" in remote.split("@", 1)[1]:
        remote = remote.split("@", 1)[1]
    return remote.split("?", 1)[0].split("#", 1)[0]


def tracked_files(root: Path) -> list[str]:
    raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, shell=False,
    )
    if raw.returncode:
        raise TaskError("Unable to enumerate tracked files.")
    return sorted(p for p in raw.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p)


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def file_fingerprints(root: Path, patterns: list[str]) -> dict[str, str]:
    result = {}
    for relative in tracked_files(root):
        if matches_any(relative, patterns):
            file = root / relative
            if file.is_symlink():
                result[relative] = sha256_bytes(os.readlink(file).encode("utf-8"))
            elif file.is_file():
                result[relative] = sha256_bytes(file.read_bytes())
    return result


def path_fingerprints(root: Path, paths: list[str], task_id: str, project_binding: dict[str, Any] | None = None) -> dict[str, str]:
    result = {}
    for relative in paths:
        if is_task_metadata(relative, task_id, project_binding):
            continue
        target = root / relative
        if target.is_symlink():
            result[relative] = sha256_bytes(os.readlink(target).encode("utf-8"))
        elif target.is_file():
            result[relative] = sha256_bytes(target.read_bytes())
        else:
            result[relative] = "deleted"
    return result


def changed_paths(root: Path, base_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-status", "-z", "--find-renames", base_sha, "--"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False,
    )
    if result.returncode:
        raise TaskError(f"Unable to calculate diff from pinned base: {result.stderr.decode(errors='replace')}")
    fields = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    changed: list[str] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        i += 1
        if status.startswith(("R", "C")):
            if i + 1 >= len(fields):
                raise TaskError("Malformed Git rename/copy diff output.")
            changed.extend([fields[i], fields[i + 1]])
            i += 2
        else:
            if i >= len(fields):
                raise TaskError("Malformed Git diff output.")
            changed.append(fields[i])
            i += 1
    changed.extend(status_paths(root))
    return sorted(set(changed))


def require_state(record: dict[str, Any], *states: str) -> None:
    if record.get("state") not in states:
        raise TaskError(f"Operation requires state {', '.join(states)}; current state is {record.get('state')}.")


def require_task_branch(root: Path, record: dict[str, Any]) -> None:
    """Reject branch/remote drift after preparation while allowing commits on the pinned branch."""
    repository = record.get("repository", {})
    expected_branch = repository.get("branch")
    if not expected_branch:
        raise TaskError("Task has no pinned working branch.")
    actual_branch = run_git(root, "branch", "--show-current")
    if actual_branch != expected_branch:
        raise TaskError(
            f"Working branch changed from '{expected_branch}' to '{actual_branch or 'detached HEAD'}'; "
            "return to the pinned branch before continuing."
        )
    actual_origin = safe_remote_identity(
        run_git(root, "remote", "get-url", "origin", check=False)
    )
    if actual_origin != repository.get("origin"):
        raise TaskError("Repository origin changed after preparation.")
    base_sha = repository.get("base_sha")
    head_sha = run_git(root, "rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, head_sha],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False,
    )
    if ancestor.returncode != 0:
        raise TaskError("Pinned base is no longer an ancestor of HEAD; re-prepare on a fresh task/branch.")


def command_init(args: argparse.Namespace) -> None:
    root = repository_root()
    clean_before_init(root)
    if not args.goal.strip() or not args.capability.strip():
        raise TaskError("Goal and capability must be non-empty.")
    if not args.allow:
        raise TaskError("At least one explicit --allow path pattern is required.")
    if not args.check:
        raise TaskError("At least one named --check profile is required.")
    if len(set(args.context)) != len(args.context):
        raise TaskError("--context paths must be unique.")
    broad_patterns = [pattern for pattern in args.allow if pattern in {"*", "**", "**/*"}]
    if broad_patterns and (args.risk != "high" or not args.scope_reason.strip()):
        raise TaskError("Repository-wide scope patterns require --risk high and a non-empty --scope-reason.")
    unknown = sorted(set(args.check) - set(PROFILES))
    if unknown:
        raise TaskError("Unknown verification profile(s): " + ", ".join(unknown))
    if args.risk not in {"low", "medium", "high"}:
        raise TaskError("Risk must be low, medium, or high.")
    project_binding = getattr(args, "project_binding", None)
    path = task_path(root, args.task_id, project_binding)
    if path.exists() or path.is_symlink():
        raise TaskError("A task with this ID already exists.")
    record = {
        "schema_version": SCHEMA_VERSION,
        "task_id": args.task_id,
        "goal": args.goal,
        "capability_improved": args.capability,
        "risk": args.risk,
        "state": "draft",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "repository": {"root_name": root.name, "origin": safe_remote_identity(run_git(root, "remote", "get-url", "origin", check=False))},
        "scope": {"allowed": sorted(set(args.allow)), "excluded": sorted(set(args.exclude)),
                  "reason": args.scope_reason.strip() or None},
        "planned_checks": list(dict.fromkeys(args.check)),
        "required_context": list(getattr(args, "required_context", REQUIRED_CONTEXT)),
        "context_paths": list(dict.fromkeys(args.context)),
        "context_package": None,
        "context_fingerprints": {},
        "pre_change_fingerprints": {},
        "semantic_artifacts": {"status": "not_collected"},
        "check_attempts": [],
        "changed_paths": [],
        "scope_validation": {"status": "not_run"},
        "final_diff": None,
        "unresolved_risks": [],
        "handoff": None,
    }
    if project_binding is not None:
        record["github_project_binding"] = project_binding
        record["project_memory_manifest"] = getattr(args, "project_memory_manifest", None)
    save_record(record, path, create_only=True)
    print(f"Created {path.relative_to(root)}. Next: prepare --task-id {args.task_id}")


def command_prepare(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "draft")
    branch = current_branch(root)
    origin = safe_remote_identity(run_git(root, "remote", "get-url", "origin", check=False))
    if origin != record["repository"].get("origin"):
        raise TaskError("Repository origin changed after task initialization; create a fresh task record.")
    unexpected = [p for p in status_paths(root) if not is_task_metadata(p, args.task_id, record.get("github_project_binding"))]
    if unexpected:
        raise TaskError("Worktree has pre-existing changes outside this task record: " + ", ".join(unexpected[:12]))
    head = run_git(root, "rev-parse", "HEAD")
    record["repository"].update({
        "branch": branch,
        "base_sha": head,
        "start_sha": head,
        "prepared_at": now_iso(),
    })
    try:
        package = build_context_cached(
            root=root, task_id=args.task_id, source_revision=head,
            required_paths=record["required_context"],
            source_paths=record.get("context_paths", []),
            allowed_patterns=record["scope"]["allowed"],
            excluded_patterns=record["scope"]["excluded"],
            project_binding=record.get("github_project_binding"),
            memory_manifest_version=(record.get("project_memory_manifest") or {}).get("version"),
            memory_manifest_max_total_bytes=(record.get("project_memory_manifest") or {}).get("max_total_bytes"),
        )
    except ContextBuildError as exc:
        raise TaskError(f"Context build blocked: {exc}") from exc
    record["context_package"] = package
    all_documents = package["project_context"] + package["source_context"]
    record["context_fingerprints"] = {item["path"]: item["sha256"] for item in all_documents}
    record["pre_change_fingerprints"] = file_fingerprints(root, record["scope"]["allowed"])
    record["state"] = "prepared"
    record["updated_at"] = now_iso()
    save_record(record, path)
    print(
        f"Prepared task on {branch} at {head}. Built context package "
        f"{package['context_sha256'][:12]} with {len(package['project_context'])} project and "
        f"{len(package['source_context'])} source documents."
    )


def command_build_envelope(args: argparse.Namespace) -> None:
    root = repository_root()
    record, task_record_path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared", "implementation", "verification")
    require_task_branch(root, record)
    try:
        package_from_git = build_context(
            root=root,
            task_id=args.task_id,
            source_revision=record["repository"]["base_sha"],
            required_paths=record.get("required_context", []),
            source_paths=record.get("context_paths", []),
            allowed_patterns=record["scope"]["allowed"],
            excluded_patterns=record["scope"]["excluded"],
            project_binding=record.get("github_project_binding"),
            memory_manifest_version=(record.get("project_memory_manifest") or {}).get("version"),
            memory_manifest_max_total_bytes=(record.get("project_memory_manifest") or {}).get("max_total_bytes"),
        )
        if package_from_git != record.get("context_package"):
            raise TaskError(
                "Persisted context package differs from the exact blobs at the pinned Git revision; "
                "do not hand it to an agent. Re-prepare on a fresh task."
            )
        envelope = build_agent_envelope(record)
    except ContextBuildError as exc:
        raise TaskError(f"Pinned context re-verification blocked: {exc}") from exc
    except EnvelopeBuildError as exc:
        raise TaskError(f"Agent envelope blocked: {exc}") from exc
    target = task_record_path.parent / "agent_input.json"
    encoded = (json.dumps(envelope, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if target.exists():
        try:
            existing = target.read_bytes()
        except OSError as exc:
            raise TaskError("Existing agent envelope cannot be read safely.") from exc
        if existing != encoded:
            raise TaskError("An agent_input.json already exists with different content; refusing to overwrite it.")
        print(f"Agent envelope is already current: {target.relative_to(root)}")
        return
    temporary = target.with_suffix(".json.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(target)
    print(
        f"Built contract v1.1 envelope for {args.task_id}: "
        f"{len(envelope['project_context'])} project and "
        f"{len(envelope['source_context'])} source documents. "
        "Local-only; no provider was called and no source was uploaded."
    )


def command_accept_context(args: argparse.Namespace) -> None:
    root = repository_root()
    record, task_record_path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared")
    require_task_branch(root, record)
    base_sha = record.get("repository", {}).get("base_sha")
    if run_git(root, "rev-parse", "HEAD") != base_sha:
        raise TaskError("Pinned base moved; prepare a fresh task before accepting context suggestions.")
    suggestions_path = Path(args.suggestions)
    if not suggestions_path.is_absolute():
        suggestions_path = root / suggestions_path
    if (suggestions_path.is_symlink() or not suggestions_path.is_file()
            or suggestions_path.parent.resolve() != task_record_path.parent.resolve()):
        raise TaskError("Suggestions file must be a regular local artifact inside this task's metadata directory.")
    try:
        raw = suggestions_path.read_bytes()
        if len(raw) > 2_000_000:
            raise TaskError("Suggestions artifact exceeds the 2 MB limit.")
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise TaskError(f"Duplicate key in suggestions artifact: {key}")
                result[key] = value
            return result
        suggestion_record = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskError("Suggestions artifact is unreadable or invalid UTF-8 JSON.") from exc
    if (not isinstance(suggestion_record, dict)
            or suggestion_record.get("schema_version") != 1
            or suggestion_record.get("task_id") != args.task_id
            or suggestion_record.get("source_revision") != base_sha
            or not isinstance(suggestion_record.get("suggestions"), list)):
        raise TaskError("Suggestions artifact does not match this task and pinned base.")
    suggestion_map = {}
    for item in suggestion_record["suggestions"]:
        relative = item.get("path") if isinstance(item, dict) else None
        digest = item.get("git_blob_sha") if isinstance(item, dict) else None
        if (not isinstance(relative, str) or not relative.startswith("lib/")
                or not relative.endswith(".dart") or "\\" in relative
                or any(part in {"", ".", ".."} for part in relative.split("/"))
                or not isinstance(digest, str)
                or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", digest)
                or relative in suggestion_map):
            raise TaskError("Suggestions artifact contains malformed, unsafe, or duplicate Dart candidates.")
        suggestion_map[relative] = digest
    selected = args.path
    if not selected or len(selected) != len(set(selected)):
        raise TaskError("Choose one or more unique paths from the suggestion artifact.")
    for relative in selected:
        expected_sha = suggestion_map.get(relative)
        if expected_sha is None:
            raise TaskError(f"Selected path was not suggested: {relative}")
        try:
            actual_sha = run_git(root, "rev-parse", f"{base_sha}:{relative}")
        except TaskError as exc:
            raise TaskError(f"Selected path is not present at the pinned base: {relative}") from exc
        if actual_sha != expected_sha:
            raise TaskError(f"Suggested source fingerprint is stale or mismatched: {relative}")
    existing = record.get("context_paths", [])
    if not isinstance(existing, list) or not all(isinstance(item, str) for item in existing):
        raise TaskError("Task source-context manifest is malformed.")
    new_paths = sorted(set(existing) | set(selected))
    if new_paths == sorted(set(existing)):
        print("All selected context paths are already accepted; task context is unchanged.")
        return
    envelope_path = task_record_path.parent / "agent_input.json"
    if envelope_path.exists() or envelope_path.is_symlink():
        raise TaskError("An agent_input.json already exists. Refusing to invalidate or overwrite an existing envelope.")
    try:
        package = build_context_cached(
            root=root,
            task_id=args.task_id,
            source_revision=base_sha,
            required_paths=record.get("required_context", []),
            source_paths=new_paths,
            allowed_patterns=record["scope"]["allowed"],
            excluded_patterns=record["scope"]["excluded"],
            project_binding=record.get("github_project_binding"),
            memory_manifest_version=(record.get("project_memory_manifest") or {}).get("version"),
            memory_manifest_max_total_bytes=(record.get("project_memory_manifest") or {}).get("max_total_bytes"),
        )
    except ContextBuildError as exc:
        raise TaskError(f"Selected context blocked by source/scope validation: {exc}") from exc
    record["context_paths"] = new_paths
    record["context_package"] = package
    record["context_selection"] = {
        "suggestions_sha256": sha256_bytes(raw),
        "accepted_paths": selected,
        "accepted_at": now_iso(),
        "note": "Explicitly selected suggestions; task scope was not changed.",
    }
    record["updated_at"] = now_iso()
    save_record(record, task_record_path)
    print(f"Accepted {len(selected)} source file(s) into the pinned context package. Scope unchanged.")


def command_suggest_context(args: argparse.Namespace) -> None:
    root = repository_root()
    record, task_record_path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared", "implementation", "verification")
    require_task_branch(root, record)
    try:
        result = select_context(
            root=root,
            task_record=record,
            query=args.query,
            resolved_index_path=Path(args.resolved_index),
            critical_paths_path=Path(args.critical_paths),
            limit=args.limit,
        )
    except ContextSelectionError as exc:
        raise TaskError(f"Context selection blocked: {exc}") from exc
    target_dir = task_record_path.parent
    target = target_dir / f"context_suggestions_{result['query_sha256'][:12]}.json"
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if target.exists():
        if target.is_symlink() or target.read_bytes() != encoded:
            raise TaskError("An existing context-suggestion artifact differs; refusing to overwrite it.")
        print(f"Context suggestions are already current: {target.relative_to(root)}")
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(target)
    print(
        f"Ranked {result['candidate_count']} in-scope source file(s); "
        f"wrote {len(result['suggestions'])} suggestions to {target.relative_to(root)}. "
        "Suggestions are advisory; task scope and context were not changed."
    )
    for item in result["suggestions"]:
        print(f"  {item['score']:>3}  {item['path']}  [{', '.join(item['reasons'])}]")


def command_impact(args: argparse.Namespace) -> None:
    root = repository_root()
    record, task_record_path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared", "implementation", "verification")
    require_task_branch(root, record)
    base_sha = record.get("repository", {}).get("base_sha")
    if not isinstance(base_sha, str):
        raise TaskError("Task has no pinned base SHA.")
    project_binding = record.get("github_project_binding")
    if project_binding is not None:
        index_paths = index_output_paths(project_binding=project_binding, source_revision=base_sha)
    else:
        index_paths = index_output_paths()
    resolved_index_path = Path(args.resolved_index) if args.resolved_index else Path(index_paths["resolved"])
    critical_paths_path = Path(args.critical_paths) if args.critical_paths else Path(index_paths["critical_paths"])
    changed = [item for item in changed_paths(root, base_sha)
               if not is_task_metadata(item, args.task_id, project_binding)]
    if not changed:
        result = {
            "schema_version": 1, "task_id": args.task_id, "source_revision": base_sha,
            "status": "not_applicable_no_changed_paths", "changed_paths": [],
            "indexed_changed_paths": [], "not_indexed_or_unknown": [],
            "impacted_critical_paths": [], "recommended_verification_profiles": [],
            "risk_flags": [], "limitations": ["No source or repository paths differ from the pinned base; semantic artifacts were not needed."],
        }
    else:
        try:
            result = analyze_impact(
                root=root, task_record=record, changed_paths=changed,
                resolved_index_path=resolved_index_path,
                critical_paths_path=critical_paths_path,
            )
        except (ImpactAnalysisError, ContextSelectionError) as exc:
            raise TaskError(f"Verified impact analysis blocked: {exc}") from exc
    if project_binding is not None:
        try:
            report_directory = ensure_namespace_directory(
                root / "docs/generated", "reports",
                project_binding=project_binding, source_revision=base_sha,
                relative_directory=f"impact/{args.task_id}",
            )
        except ValueError as exc:
            raise TaskError(f"Project-scoped impact report path is unsafe: {exc}") from exc
        target = report_directory / "impact_report.json"
    else:
        target = task_record_path.parent / "impact_report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
    report_path = target.relative_to(root).as_posix()
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\\n").encode("utf-8")
    temporary = target.with_suffix(".json.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(target)
    record["impact_analysis"] = {
        "status": result.get("status") or ("completed_with_unknowns" if result["not_indexed_or_unknown"] else "completed"),
        "report_path": report_path,
        "report_sha256": sha256_bytes(encoded),
        "source_revision": base_sha,
        "changed_paths": result["changed_paths"],
        "impacted_critical_path_ids": [item["id"] for item in result["impacted_critical_paths"]],
        "recommended_verification_profiles": result["recommended_verification_profiles"],
        "risk_flags": result["risk_flags"],
        "analyzed_at": now_iso(),
    }
    record["updated_at"] = now_iso()
    save_record(record, task_record_path)
    print(f"Verified impact report: {report_path}")
    print(f"Analysis status: {result.get('status', 'completed')}")
    print(f"Changed paths: {len(result['changed_paths'])}; indexed: {len(result['indexed_changed_paths'])}; unknown: {len(result['not_indexed_or_unknown'])}")
    print("Impacted critical paths: " + (", ".join(str(item["id"]) for item in result["impacted_critical_paths"]) or "none identified"))
    print("Suggested profiles (advisory): " + (", ".join(result["recommended_verification_profiles"]) or "none"))
    if result["risk_flags"]:
        print("Risk flags: " + ", ".join(result["risk_flags"]))
    if result["not_indexed_or_unknown"]:
        print("WARNING: Some changed paths are not covered by the semantic index; review them manually.")


def command_begin(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared")
    require_task_branch(root, record)
    current = run_git(root, "rev-parse", "HEAD")
    if current != record["repository"]["base_sha"]:
        raise TaskError("Base SHA moved since prepare; re-prepare on a fresh task/branch rather than silently rebasing.")
    record["repository"]["implementation_start_sha"] = current
    record["state"] = "implementation"
    record["implementation_started_at"] = now_iso()
    record["updated_at"] = now_iso()
    save_record(record, path)
    print(f"Implementation phase started at {current}.")


def command_validate_scope(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "prepared", "implementation", "verification")
    require_task_branch(root, record)
    base = record.get("repository", {}).get("base_sha")
    if not base:
        raise TaskError("Task has no pinned base SHA.")
    paths = changed_paths(root, base)
    violations = []
    for item in paths:
        if is_task_metadata(item, args.task_id, record.get("github_project_binding")):
            continue
        if matches_any(item, record["scope"]["excluded"]):
            violations.append(f"excluded: {item}")
        elif not matches_any(item, record["scope"]["allowed"]):
            violations.append(f"outside allowed scope: {item}")
    record["changed_paths"] = paths
    record["scope_validation"] = {
        "status": "failed" if violations else "passed",
        "checked_at": now_iso(),
        "violations": violations,
        "path_fingerprints": path_fingerprints(root, paths, args.task_id, record.get("github_project_binding")),
    }
    record["updated_at"] = now_iso()
    save_record(record, path)
    if violations:
        raise TaskError("Scope validation failed: " + "; ".join(violations))
    print(f"Scope validation passed for {len(paths)} changed path(s).")


def command_verify(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "implementation", "verification")
    require_task_branch(root, record)
    profile = args.profile
    if profile not in record["planned_checks"]:
        raise TaskError(f"Profile '{profile}' was not declared in the task plan.")
    definition = PROFILES[profile]
    started = time.monotonic()
    timestamp = now_iso()
    base_sha = record.get("repository", {}).get("base_sha")
    verification_paths_before = changed_paths(root, base_sha) if base_sha else []
    verification_fingerprints_before = path_fingerprints(
        root, verification_paths_before, args.task_id, record.get("github_project_binding")
    )
    allowed_env = {
        "PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "CI",
        "JAVA_HOME", "JAVA_HOME_17_X64", "JAVA_HOME_21_X64",
        "ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_USER_HOME",
        "ANDROID_NDK_HOME", "ANDROID_NDK_ROOT", "FLUTTER_ROOT",
        "PUB_CACHE", "PUB_HOSTED_URL", "GRADLE_USER_HOME",
    }
    # Do not forward API tokens or arbitrary local secrets into test processes.
    check_env = {key: value for key, value in os.environ.items() if key in allowed_env}
    # Verification must not dirty the worktree with bytecode cache files.
    check_env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            definition["argv"], cwd=root, env=check_env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=definition["timeout"], check=False, shell=False,
        )
        exit_code = result.returncode
        status = "passed" if exit_code == 0 else "failed"
        output = result.stdout or ""
    except FileNotFoundError as exc:
        exit_code, status, output = 127, "failed", str(exc)
    except subprocess.TimeoutExpired as exc:
        # TimeoutExpired may carry bytes even when text=True was requested.
        # Store only a stable diagnostic string; never persist raw child output.
        exit_code, status, output = 124, "failed", f"Verification timed out after {definition['timeout']} seconds."
    except OSError as exc:
        exit_code, status, output = 126, "failed", str(exc)
    duration = round(time.monotonic() - started, 3)
    verification_paths = changed_paths(root, base_sha) if base_sha else []
    verification_fingerprints = path_fingerprints(root, verification_paths, args.task_id, record.get("github_project_binding"))
    source_stable = (
        verification_paths_before == verification_paths
        and verification_fingerprints_before == verification_fingerprints
    )
    if not source_stable and status == "passed":
        status = "failed"
        exit_code = 125
        output = "Source files changed while verification was running; rerun the check on a stable worktree."
    attempt = {
        "profile": profile,
        "status": status,
        "exit_code": exit_code,
        "source_stable_during_check": source_stable,
        "verification_input_path_fingerprints": verification_fingerprints_before,
        "duration_seconds": duration,
        "started_at": timestamp,
        "finished_at": now_iso(),
        "output_sha256": sha256_bytes(output.encode("utf-8", errors="replace")),
        "argv": definition["argv"],
        "timeout_seconds": definition["timeout"],
        "verified_paths": verification_paths,
        "verified_path_fingerprints": verification_fingerprints,
    }
    record["check_attempts"].append(attempt)
    record["state"] = "verification"
    record["updated_at"] = now_iso()
    save_record(record, path)
    print(f"{profile}: {status} (exit={exit_code}, {duration}s)")
    if status != "passed":
        raise TaskError(f"Verification profile '{profile}' failed; see its CI/local command output.")


def command_finalize(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id, getattr(args, "project_binding", None))
    require_state(record, "verification", "implementation")
    require_task_branch(root, record)
    if not args.reviewed_diff:
        raise TaskError("Finalization requires explicit --reviewed-diff confirmation after reviewing the complete diff.")
    if record.get("scope_validation", {}).get("status") != "passed":
        raise TaskError("A successful scope validation is required before finalization.")
    latest = {}
    for attempt in record["check_attempts"]:
        latest[attempt["profile"]] = attempt
    missing = [p for p in record["planned_checks"] if p not in latest or latest[p]["status"] != "passed"]
    if missing:
        raise TaskError("Required checks are missing or not passing: " + ", ".join(missing))
    base = record["repository"]["base_sha"]
    # Create the report path before snapshotting so the final inventory includes it.
    handoff_path = path.parent / "HANDOFF.md"
    handoff_path.touch(exist_ok=True)
    paths = changed_paths(root, base)
    violations = [
        item for item in paths if not is_task_metadata(item, args.task_id, record.get("github_project_binding")) and (
            matches_any(item, record["scope"]["excluded"])
            or not matches_any(item, record["scope"]["allowed"])
        )
    ]
    if violations:
        raise TaskError("Final diff contains out-of-scope paths: " + ", ".join(violations))
    current_fingerprints = path_fingerprints(root, paths, args.task_id, record.get("github_project_binding"))
    if current_fingerprints != record["scope_validation"].get("path_fingerprints", {}):
        raise TaskError("Files changed after scope validation; rerun validate-scope and review the complete diff.")
    stale_checks = []
    for profile in record["planned_checks"]:
        attempt = latest[profile]
        verified = attempt.get("verified_path_fingerprints")
        if attempt.get("source_stable_during_check") is not True:
            stale_checks.append(profile)
        elif verified is None or verified != current_fingerprints:
            stale_checks.append(profile)
    if stale_checks:
        raise TaskError(
            "Source files changed after the latest successful verification for: "
            + ", ".join(stale_checks) + ". Rerun those checks before finalization."
        )
    diff = run_git(root, "diff", "--stat", base, "--")
    tracked = set(tracked_files(root))
    untracked = [item for item in status_paths(root) if item not in tracked]
    record["changed_paths"] = paths
    record["final_diff"] = {
        "reviewed": True,
        "reviewed_at": now_iso(),
        "head_sha": run_git(root, "rev-parse", "HEAD"),
        "stat": diff,
        "untracked_paths": untracked,
        "path_fingerprints": current_fingerprints,
        "task_metadata_paths": [
            item for item in paths
            if is_task_metadata(item, args.task_id, record.get("github_project_binding"))
        ],
    }
    record["state"] = "review_ready"
    record["finalized_at"] = now_iso()
    record["updated_at"] = now_iso()
    record["handoff"] = render_handoff(record)
    handoff_temp = handoff_path.with_suffix(".md.tmp")
    handoff_temp.write_text(record["handoff"], encoding="utf-8")
    handoff_temp.replace(handoff_path)
    save_record(record, path)
    print(f"Task {args.task_id} is review_ready. Handoff: {handoff_path}")


def render_handoff(record: dict[str, Any]) -> str:
    latest: dict[str, dict[str, Any]] = {}
    for item in record.get("check_attempts", []):
        latest[item["profile"]] = item
    lines = [
        f"# Task handoff: {record['task_id']}", "",
        f"- **Goal:** {record['goal']}",
        f"- **State:** {record['state']}",
        f"- **Risk:** {record['risk']}",
        f"- **Branch:** {record.get('repository', {}).get('branch', 'unknown')}",
        f"- **Base SHA:** {record.get('repository', {}).get('base_sha', 'unknown')}",
        f"- **Final SHA:** {record.get('final_diff', {}).get('head_sha', 'not finalized')}",
        "", "## Changed paths",
    ]
    metadata_paths = set(record.get("final_diff", {}).get("task_metadata_paths", []))
    lines.extend(f"- `{item}`" for item in record.get("changed_paths", []) if item not in metadata_paths)
    lines.extend(["", "## Task metadata", "- Machine-readable task record and this handoff are stored under `.agent/tasks/<task-id>/`.", "", "## Verification"])
    for profile in record.get("planned_checks", []):
        attempt = latest.get(profile)
        if attempt:
            lines.append(f"- {profile}: **{attempt['status']}** (exit {attempt['exit_code']}, {attempt['duration_seconds']}s)")
        else:
            lines.append(f"- {profile}: **not run**")
    lines.extend([
        "", "## Scope",
        f"- Validation: {record.get('scope_validation', {}).get('status', 'not run')}",
        "", "## Limitations",
        "- Static artifacts and tests do not establish real-device runtime behavior.",
        "- Merge, release, and deployment require separate explicit approval.",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a task record; requires a clean worktree.")
    init.add_argument("--task-id", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--capability", required=True)
    init.add_argument("--risk", required=True, choices=["low", "medium", "high"])
    init.add_argument("--allow", action="append", default=[])
    init.add_argument("--exclude", action="append", default=[])
    init.add_argument("--scope-reason", default="")
    init.add_argument("--check", action="append", default=[])
    init.add_argument("--context", action="append", default=[], metavar="REPO_PATH",
                      help="Explicit source file to include in agent context (repeatable).")
    init.set_defaults(func=command_init)
    accept = sub.add_parser("accept-context", help="Add explicitly selected, suggested source files to a prepared task context.")
    accept.add_argument("--task-id", required=True)
    accept.add_argument("--suggestions", required=True, metavar="TASK_LOCAL_JSON")
    accept.add_argument("--path", action="append", required=True, metavar="REPO_PATH")
    accept.set_defaults(func=command_accept_context)
    suggest = sub.add_parser("suggest-context", help="Rank in-scope source files from verified semantic artifacts; advisory only.")
    suggest.add_argument("--task-id", required=True)
    suggest.add_argument("--query", required=True, help="Plain-language task request; treated only as search text.")
    suggest.add_argument("--resolved-index", required=True, metavar="JSON_PATH")
    suggest.add_argument("--critical-paths", required=True, metavar="JSON_PATH")
    suggest.add_argument("--limit", type=int, default=12)
    suggest.set_defaults(func=command_suggest_context)
    envelope = sub.add_parser("build-envelope", help="Verify the pinned context and create a local v1.1 agent input envelope.")
    envelope.add_argument("--task-id", required=True)
    envelope.set_defaults(func=command_build_envelope)
    for name, func, help_text in [
        ("prepare", command_prepare, "Load context and pin the clean branch baseline."),
        ("begin", command_begin, "Enter the implementation state."),
        ("validate-scope", command_validate_scope, "Validate every changed path against declared scope."),
    ]:
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--task-id", required=True)
        item.set_defaults(func=func)
    impact = sub.add_parser("impact", help="Analyze changed paths against verified semantic and critical-path artifacts.")
    impact.add_argument("--task-id", required=True)
    impact.add_argument("--resolved-index")
    impact.add_argument("--critical-paths")
    impact.set_defaults(func=command_impact)
    verify = sub.add_parser("verify", help="Run one declared, fixed verification profile.")
    verify.add_argument("--task-id", required=True)
    verify.add_argument("--profile", required=True, choices=sorted(PROFILES))
    verify.set_defaults(func=command_verify)
    finalize = sub.add_parser("finalize", help="Create the review handoff after all gates pass.")
    finalize.add_argument("--task-id", required=True)
    finalize.add_argument("--reviewed-diff", action="store_true")
    finalize.set_defaults(func=command_finalize)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except TaskError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
