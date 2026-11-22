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


def task_path(root: Path, task_id: str) -> Path:
    if not TASK_ID_RE.fullmatch(task_id):
        raise TaskError("Invalid task ID; use 3-64 lowercase letters, digits, and hyphens.")
    return root / TASK_DIR / task_id / "task.json"


def load_record(root: Path, task_id: str) -> tuple[dict[str, Any], Path]:
    path = task_path(root, task_id)
    if not path.is_file():
        raise TaskError(f"Task record not found: {path.relative_to(root)}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskError(f"Task record is unreadable: {exc}") from exc
    if record.get("schema_version") != SCHEMA_VERSION or record.get("task_id") != task_id:
        raise TaskError("Unsupported or inconsistent task record schema.")
    return record, path


def save_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(path)


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


def is_task_metadata(path: str, task_id: str) -> bool:
    prefix = (TASK_DIR / task_id).as_posix() + "/"
    return path.startswith(prefix)


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
            if file.is_file():
                result[relative] = sha256_bytes(file.read_bytes())
    return result


def path_fingerprints(root: Path, paths: list[str], task_id: str) -> dict[str, str]:
    result = {}
    for relative in paths:
        if is_task_metadata(relative, task_id):
            continue
        target = root / relative
        if target.is_file():
            result[relative] = sha256_bytes(target.read_bytes())
        elif target.is_symlink():
            result[relative] = sha256_bytes(os.readlink(target).encode("utf-8"))
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


def command_init(args: argparse.Namespace) -> None:
    root = repository_root()
    clean_before_init(root)
    if not args.allow:
        raise TaskError("At least one explicit --allow path pattern is required.")
    if not args.check:
        raise TaskError("At least one named --check profile is required.")
    unknown = sorted(set(args.check) - set(PROFILES))
    if unknown:
        raise TaskError("Unknown verification profile(s): " + ", ".join(unknown))
    if args.risk not in {"low", "medium", "high"}:
        raise TaskError("Risk must be low, medium, or high.")
    path = task_path(root, args.task_id)
    if path.exists():
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
        "scope": {"allowed": sorted(set(args.allow)), "excluded": sorted(set(args.exclude))},
        "planned_checks": list(dict.fromkeys(args.check)),
        "required_context": list(REQUIRED_CONTEXT),
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
    save_record(record, path)
    print(f"Created {path.relative_to(root)}. Next: prepare --task-id {args.task_id}")


def command_prepare(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id)
    require_state(record, "draft")
    branch = current_branch(root)
    unexpected = [p for p in status_paths(root) if not is_task_metadata(p, args.task_id)]
    if unexpected:
        raise TaskError("Worktree has pre-existing changes outside this task record: " + ", ".join(unexpected[:12]))
    missing = [p for p in REQUIRED_CONTEXT if not (root / p).is_file()]
    if missing:
        raise TaskError("Required project context is missing: " + ", ".join(missing))
    head = run_git(root, "rev-parse", "HEAD")
    record["repository"].update({
        "branch": branch,
        "base_sha": head,
        "start_sha": head,
        "prepared_at": now_iso(),
    })
    record["context_fingerprints"] = {
        p: sha256_bytes((root / p).read_bytes()) for p in REQUIRED_CONTEXT
    }
    record["pre_change_fingerprints"] = file_fingerprints(root, record["scope"]["allowed"])
    record["state"] = "prepared"
    record["updated_at"] = now_iso()
    save_record(record, path)
    print(f"Prepared task on {branch} at {head}. Verified {len(REQUIRED_CONTEXT)} required context files.")


def command_impact(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id)
    require_state(record, "prepared", "implementation", "verification")
    candidates = [
        "docs/generated/jet_vpn_resolved_index.json",
        "docs/generated/jet_vpn_critical_paths.json",
        "docs/critical_paths.json",
    ]
    artifacts = {}
    summaries = []
    for relative in candidates:
        file = root / relative
        if not file.is_file():
            artifacts[relative] = {"status": "unavailable"}
            continue
        raw = file.read_bytes()
        entry: dict[str, Any] = {"status": "present_unverified", "sha256": sha256_bytes(raw)}
        try:
            parsed = json.loads(raw)
            if relative.endswith("jet_vpn_critical_paths.json"):
                paths = parsed.get("paths", []) if isinstance(parsed, dict) else []
                summaries.extend(
                    {"id": item.get("id"), "summary": item.get("summary")}
                    for item in paths if isinstance(item, dict)
                )
            elif relative.endswith("critical_paths.json"):
                configured = parsed.get("paths", []) if isinstance(parsed, dict) else []
                entry["configured_path_ids"] = [
                    item.get("id") for item in configured if isinstance(item, dict)
                ]
        except (json.JSONDecodeError, AttributeError):
            entry["status"] = "present_invalid_json"
        artifacts[relative] = entry
    record["semantic_artifacts"] = {
        "collected_at": now_iso(),
        "artifacts": artifacts,
        "critical_path_summaries": summaries,
        "limitation": "Presence and file hashes are recorded; freshness and path-specific semantic impact are not independently established by this MVP.",
    }
    record["updated_at"] = now_iso()
    save_record(record, path)
    print("Recorded semantic artifact availability. This is not a claim of complete impact analysis.")


def command_begin(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id)
    require_state(record, "prepared")
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
    record, path = load_record(root, args.task_id)
    require_state(record, "prepared", "implementation", "verification")
    base = record.get("repository", {}).get("base_sha")
    if not base:
        raise TaskError("Task has no pinned base SHA.")
    paths = changed_paths(root, base)
    metadata = (TASK_DIR / args.task_id / "task.json").as_posix()
    violations = []
    for item in paths:
        if item == metadata:
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
        "path_fingerprints": path_fingerprints(root, paths, args.task_id),
    }
    record["updated_at"] = now_iso()
    save_record(record, path)
    if violations:
        raise TaskError("Scope validation failed: " + "; ".join(violations))
    print(f"Scope validation passed for {len(paths)} changed path(s).")


def command_verify(args: argparse.Namespace) -> None:
    root = repository_root()
    record, path = load_record(root, args.task_id)
    require_state(record, "implementation", "verification")
    profile = args.profile
    if profile not in record["planned_checks"]:
        raise TaskError(f"Profile '{profile}' was not declared in the task plan.")
    definition = PROFILES[profile]
    started = time.monotonic()
    timestamp = now_iso()
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
        exit_code, status, output = 124, "failed", str(exc)
    duration = round(time.monotonic() - started, 3)
    attempt = {
        "profile": profile,
        "status": status,
        "exit_code": exit_code,
        "duration_seconds": duration,
        "started_at": timestamp,
        "finished_at": now_iso(),
        "output_sha256": sha256_bytes(output.encode("utf-8", errors="replace")),
        "argv": definition["argv"],
        "timeout_seconds": definition["timeout"],
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
    record, path = load_record(root, args.task_id)
    require_state(record, "verification", "implementation")
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
    paths = changed_paths(root, base)
    metadata = (TASK_DIR / args.task_id / "task.json").as_posix()
    violations = [
        item for item in paths if item != metadata and (
            matches_any(item, record["scope"]["excluded"])
            or not matches_any(item, record["scope"]["allowed"])
        )
    ]
    if violations:
        raise TaskError("Final diff contains out-of-scope paths: " + ", ".join(violations))
    current_fingerprints = path_fingerprints(root, paths, args.task_id)
    if current_fingerprints != record["scope_validation"].get("path_fingerprints", {}):
        raise TaskError("Files changed after scope validation; rerun validate-scope and review the complete diff.")
    diff = run_git(root, "diff", "--stat", base, "--")
    tracked = set(run_git(root, "ls-files").splitlines())
    untracked = [item for item in status_paths(root) if item not in tracked]
    record["changed_paths"] = paths
    record["final_diff"] = {
        "reviewed": True,
        "reviewed_at": now_iso(),
        "head_sha": run_git(root, "rev-parse", "HEAD"),
        "stat": diff,
        "untracked_paths": untracked,
    }
    record["state"] = "review_ready"
    record["finalized_at"] = now_iso()
    record["updated_at"] = now_iso()
    record["handoff"] = render_handoff(record)
    save_record(record, path)
    print(f"Task {args.task_id} is review_ready. Handoff: {path.parent / 'HANDOFF.md'}")
    (path.parent / "HANDOFF.md").write_text(record["handoff"], encoding="utf-8")


def render_handoff(record: dict[str, Any]) -> str:
    checks = record.get("check_attempts", [])
    latest: dict[str, dict[str, Any]] = {}
    for item in checks:
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
    lines.extend(f"- `{item}`" for item in record.get("changed_paths", []))
    lines.extend(["", "## Verification"])
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
    init.add_argument("--check", action="append", default=[])
    init.set_defaults(func=command_init)
    for name, func, help_text in [
        ("prepare", command_prepare, "Load context and pin the clean branch baseline."),
        ("impact", command_impact, "Record available semantic and critical-path artifacts."),
        ("begin", command_begin, "Enter the implementation state."),
        ("validate-scope", command_validate_scope, "Validate every changed path against declared scope."),
    ]:
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--task-id", required=True)
        item.set_defaults(func=func)
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
