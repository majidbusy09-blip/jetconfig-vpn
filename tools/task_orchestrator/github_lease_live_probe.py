"""Live GitHub ref-CAS smoke test for a disposable CI-only branch.

Runs only from a trusted push to main. It creates a unique probe ref, races
two force-with-lease updates against the same expected SHA, verifies exactly
one winner, and deletes the probe ref in a finally block.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Sequence

REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class ProbeError(RuntimeError):
    pass


def probe_branch(run_id: str, attempt: str) -> str:
    if not re.fullmatch(r"[0-9]{1,20}", run_id) or not re.fullmatch(r"[0-9]{1,5}", attempt):
        raise ProbeError("Invalid GitHub Actions run identity.")
    return "agent-locks/ci-cas-probe-" + run_id + "-" + attempt


def _git(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = "JET VPN Lease CAS Probe"
    env["GIT_AUTHOR_EMAIL"] = "jet-lease-probe@users.noreply.github.com"
    env["GIT_COMMITTER_NAME"] = "JET VPN Lease CAS Probe"
    env["GIT_COMMITTER_EMAIL"] = "jet-lease-probe@users.noreply.github.com"
    try:
        result = subprocess.run(["git", *args], text=True, capture_output=True,
                                check=False, env=env)
    except OSError as exc:
        raise ProbeError("Git executable could not be started.") from exc
    if check and result.returncode != 0:
        raise ProbeError("Git probe command failed: " + str(args[0]) + ".")
    return result


def _remote_sha(ref: str) -> str | None:
    result = _git(["ls-remote", "--heads", "origin", ref])
    if not result.stdout.strip():
        return None
    fields = result.stdout.strip().split()
    if len(fields) != 2 or fields[1] != ref or not SHA_RE.fullmatch(fields[0]):
        raise ProbeError("Remote probe ref response was malformed.")
    return fields[0]


def run_probe() -> dict[str, object]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not REPO_RE.fullmatch(repository):
        raise ProbeError("GITHUB_REPOSITORY is missing or invalid.")
    branch = probe_branch(os.environ.get("GITHUB_RUN_ID", ""),
                          os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    ref = "refs/heads/" + branch
    if _remote_sha(ref) is not None:
        raise ProbeError("Unique probe ref already exists; refusing to overwrite it.")

    base = _git(["rev-parse", "--verify", "HEAD^{commit}"]).stdout.strip()
    if not SHA_RE.fullmatch(base):
        raise ProbeError("Checked-out base commit is invalid.")
    tree = _git(["rev-parse", "--verify", base + "^{tree}"]).stdout.strip()
    candidates = [
        _git(["commit-tree", tree, "-p", base, "-m", "CI lease CAS candidate A"]).stdout.strip(),
        _git(["commit-tree", tree, "-p", base, "-m", "CI lease CAS candidate B"]).stdout.strip(),
    ]
    if any(not SHA_RE.fullmatch(candidate) for candidate in candidates):
        raise ProbeError("Could not prepare both CAS candidate commits.")

    created = False
    cleanup_error: str | None = None
    try:
        initial = _git(["push", "--no-verify", "--porcelain", "origin", base + ":" + ref],
                       check=False)
        if initial.returncode == 0:
            created = True
        after_initial = _remote_sha(ref)
        if after_initial == base:
            created = True
        if initial.returncode != 0 or after_initial != base:
            raise ProbeError("Initial probe ref creation could not be verified.")

        commands = [
            ["git", "push", "--no-verify", "--porcelain",
             "--force-with-lease=" + ref + ":" + base, "origin", candidate + ":" + ref]
            for candidate in candidates
        ]
        processes: list[subprocess.Popen[str]] = []
        try:
            for command in commands:
                processes.append(subprocess.Popen(
                    command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                         "GIT_AUTHOR_NAME": "JET VPN Lease CAS Probe",
                         "GIT_AUTHOR_EMAIL": "jet-lease-probe@users.noreply.github.com",
                         "GIT_COMMITTER_NAME": "JET VPN Lease CAS Probe",
                         "GIT_COMMITTER_EMAIL": "jet-lease-probe@users.noreply.github.com"},
                ))
        except OSError as exc:
            for process in processes:
                process.terminate()
            for process in processes:
                process.wait()
            raise ProbeError("Could not start both concurrent Git writers.") from exc

        results = [process.communicate() + (process.returncode,) for process in processes]
        winners = [i for i, result in enumerate(results) if result[2] == 0]
        if len(winners) != 1:
            raise ProbeError("Expected exactly one successful concurrent compare-and-swap.")
        winner_sha = candidates[winners[0]]
        if _remote_sha(ref) != winner_sha:
            raise ProbeError("Final probe ref does not match the sole successful writer.")
        return {
            "repository": repository,
            "probe_branch": branch,
            "expected_old_sha": base,
            "candidate_shas": candidates,
            "successful_writers": len(winners),
            "winner_sha": winner_sha,
            "github_ref_cas": "verified",
        }
    finally:
        if created:
            cleanup = _git(["push", "--no-verify", "--porcelain", "origin", ":" + ref],
                           check=False)
            if cleanup.returncode != 0 or _remote_sha(ref) is not None:
                cleanup_error = "Probe branch cleanup failed: " + branch
        if cleanup_error:
            raise ProbeError(cleanup_error)


def main() -> int:
    result = run_probe()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
