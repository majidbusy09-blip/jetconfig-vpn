#!/usr/bin/env python3
"""Require durable project-memory updates for implementation-sensitive PRs.

This gate checks the PR's Git diff, not its working tree, so a required memory
file must actually be part of the proposed change. It is intentionally a
change-policy check; it does not claim that prose is factually correct.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

CORE_MEMORY = frozenset({
    "docs/CURRENT_STATUS.md",
    "docs/NEXT_STEPS.md",
    "docs/DEVELOPMENT_LOG.md",
    "docs/PROJECT_CONTEXT.md",
})
ARCHITECTURE_MEMORY = frozenset({
    "AGENTS.md",
    "docs/DECISIONS.md",
})
MEMORY_TOOLING_MEMORY = frozenset({
    "docs/PROJECT_MEMORY_AUTOMATION.md",
})
IMPLEMENTATION_PREFIXES = (
    "lib/",
    "test/",
    "android/",
    "ios/",
    "tools/task_orchestrator/",
    "tools/project_memory/",
    "tools/validation/",
    "tools/v2ray_notif_patch/",
    "gradle/",
    ".github/workflows/",
)
IMPLEMENTATION_FILES = frozenset({
    "pubspec.yaml",
    "pubspec.lock",
    "analysis_options.yaml",
})


class MemoryUpdateError(ValueError):
    """A PR cannot be verified or is missing required durable memory updates."""


def required_memory_paths(changed_paths: Iterable[str]) -> set[str]:
    """Return mandatory memory documents for the PR's changed implementation paths."""
    paths = set(changed_paths)
    implementation = any(
        path in IMPLEMENTATION_FILES
        or path.startswith(IMPLEMENTATION_PREFIXES)
        for path in paths
    )
    if not implementation:
        return set()

    required = set(CORE_MEMORY)
    architecture_change = any(
        path.startswith((
            "tools/task_orchestrator/",
            "tools/project_memory/",
            "tools/validation/",
            ".github/workflows/",
        ))
        for path in paths
    )
    if architecture_change:
        required.update(ARCHITECTURE_MEMORY)

    memory_system_change = any(
        path.startswith(("tools/project_memory/", ".github/workflows/"))
        for path in paths
    )
    if memory_system_change:
        required.update(MEMORY_TOOLING_MEMORY)

    return required


def changed_paths_between(root: Path, base_sha: str, head_sha: str) -> list[str]:
    for value, label in ((base_sha, "base"), (head_sha, "head")):
        if not isinstance(value, str) or not SHA_RE.fullmatch(value):
            raise MemoryUpdateError(f"PR {label} must be a full Git commit SHA.")
        check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, shell=False,
        )
        if check.returncode:
            raise MemoryUpdateError(f"PR {label} commit is unavailable in the checkout.")

    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", f"{base_sha}...{head_sha}"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise MemoryUpdateError(f"Unable to calculate PR changed paths: {detail}")
    try:
        return [
            item.decode("utf-8", errors="strict")
            for item in result.stdout.split(b"\0")
            if item
        ]
    except UnicodeDecodeError as exc:
        raise MemoryUpdateError("PR diff contains a non-UTF-8 path.") from exc


def verify_memory_updates(changed_paths: Iterable[str]) -> list[str]:
    """Return missing required memory paths; an empty list means the gate passes."""
    changed = set(changed_paths)
    required = required_memory_paths(changed)
    return sorted(required - changed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    try:
        changed = changed_paths_between(args.repo_root, args.base_sha, args.head_sha)
        required = required_memory_paths(changed)
        missing = verify_memory_updates(changed)
    except MemoryUpdateError as exc:
        print(f"PROJECT MEMORY GATE ERROR: {exc}", file=sys.stderr)
        return 2

    if not required:
        print("Project-memory update gate: no implementation-sensitive changes detected.")
        return 0
    if missing:
        print("PROJECT MEMORY UPDATE REQUIRED. The PR changes implementation-sensitive files but omits:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        print("Update these tracked documents in the same PR; do not rely on chat history.", file=sys.stderr)
        return 1

    print(f"Project-memory update gate passed ({len(required)} required documents updated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
