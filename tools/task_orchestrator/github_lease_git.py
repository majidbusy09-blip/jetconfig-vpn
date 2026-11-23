"""Atomic GitHub-ref lease transport using Git's server-side force-with-lease.

Requires an existing checkout, git, GITHUB_REPOSITORY, and a short-lived
GITHUB_TOKEN with contents:write. Credentials are passed only through a
process environment HTTP header; shell execution is never used.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_lease import (
    LeaseError, lock_branch, make_lease, release_plan, transition_plan,
    validate_lease,
)

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
LEASE_PATH = ".agent-locks/lease.json"


class LeaseGitError(RuntimeError):
    """A remote lease operation could not be proven successful."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _remote_url(repository: str) -> str:
    if not isinstance(repository, str) or not REPO_RE.fullmatch(repository):
        raise LeaseGitError("GITHUB_REPOSITORY must be owner/repository.")
    return "https://github.com/" + repository + ".git"


def _git(args: list[str], *, token: str, input_text: str | None = None,
         index_path: str | None = None) -> str:
    if not isinstance(token, str) or not token.strip():
        raise LeaseGitError("A GitHub token is required.")
    env = os.environ.copy()
    basic = base64.b64encode(("x-access-token:" + token).encode("utf-8")).decode("ascii")
    env.update({
        "GIT_CONFIG_COUNT": "3",
        "GIT_CONFIG_KEY_0": "http.extraheader",
        "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic " + basic,
        "GIT_CONFIG_KEY_1": "core.hooksPath",
        "GIT_CONFIG_VALUE_1": "/dev/null",
        "GIT_CONFIG_KEY_2": "credential.helper",
        "GIT_CONFIG_VALUE_2": "",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "JET VPN Agent Lease",
        "GIT_AUTHOR_EMAIL": "jet-agent-lease@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "JET VPN Agent Lease",
        "GIT_COMMITTER_EMAIL": "jet-agent-lease@users.noreply.github.com",
    })
    if index_path is not None:
        env["GIT_INDEX_FILE"] = index_path
    try:
        result = subprocess.run(
            ["git", *args], input=input_text, text=True, capture_output=True,
            check=False, env=env,
        )
    except OSError as exc:
        raise LeaseGitError("Git executable could not be started.") from exc
    if result.returncode != 0:
        # Do not forward stderr: it may contain remote or credential diagnostics.
        raise LeaseGitError("Git operation failed: " + args[0] + " (exit " + str(result.returncode) + ").")
    return result.stdout.strip()


def _remote_sha(remote: str, branch: str, token: str) -> str | None:
    ref = "refs/heads/" + branch
    output = _git(["ls-remote", "--heads", remote, ref], token=token)
    if not output:
        return None
    fields = output.split()
    if len(fields) != 2 or fields[1] != ref or not SHA_RE.fullmatch(fields[0]):
        raise LeaseGitError("Remote lock ref response was malformed.")
    return fields[0]


def _fetch_head(remote: str, branch: str, token: str) -> str:
    ref = "refs/heads/" + branch
    _git(["fetch", "--no-tags", remote, ref], token=token)
    sha = _git(["rev-parse", "--verify", "FETCH_HEAD^{commit}"], token=token)
    if not SHA_RE.fullmatch(sha):
        raise LeaseGitError("Fetched lock ref did not resolve to a full commit.")
    return sha


def _read_lease(commit_sha: str, token: str) -> dict[str, Any]:
    raw = _git(["show", commit_sha + ":" + LEASE_PATH], token=token)
    try:
        parsed = json.loads(raw)
        return validate_lease(parsed)
    except (json.JSONDecodeError, LeaseError) as exc:
        raise LeaseGitError("Existing lock ref has no valid lease; failing closed.") from exc


def _commit_record(parent_sha: str, record: dict[str, Any], token: str) -> str:
    if not SHA_RE.fullmatch(parent_sha):
        raise LeaseGitError("Parent commit SHA is invalid.")
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    blob = _git(["hash-object", "-w", "--stdin"], token=token, input_text=encoded)
    if not SHA_RE.fullmatch(blob):
        raise LeaseGitError("Lease blob creation failed.")
    index_name = ""
    try:
        with tempfile.NamedTemporaryFile(prefix="jet-agent-lease-index-", delete=False) as handle:
            index_name = handle.name
        _git(["read-tree", parent_sha], token=token, index_path=index_name)
        cacheinfo = "100644," + blob + "," + LEASE_PATH
        _git(["update-index", "--add", "--cacheinfo", cacheinfo],
             token=token, index_path=index_name)
        tree = _git(["write-tree"], token=token, index_path=index_name)
        if not SHA_RE.fullmatch(tree):
            raise LeaseGitError("Lease tree creation failed.")
        commit = _git(
            ["commit-tree", tree, "-p", parent_sha, "-m", "chore: update agent task lease"],
            token=token,
        )
        if not SHA_RE.fullmatch(commit):
            raise LeaseGitError("Lease commit creation failed.")
        return commit
    finally:
        if index_name:
            try:
                Path(index_name).unlink(missing_ok=True)
                Path(index_name + ".lock").unlink(missing_ok=True)
            except OSError:
                pass


def _push(remote: str, branch: str, commit_sha: str, expected_sha: str | None,
          token: str) -> None:
    ref = "refs/heads/" + branch
    if expected_sha is None:
        # Initial creation is exclusive: a concurrent creator makes this push fail.
        args = ["push", "--no-verify", "--porcelain", remote, commit_sha + ":" + ref]
    else:
        if not SHA_RE.fullmatch(expected_sha):
            raise LeaseGitError("Expected lock SHA is invalid.")
        # Git receive-pack enforces this old-object check atomically on the server.
        lease_arg = "--force-with-lease=" + ref + ":" + expected_sha
        args = ["push", "--no-verify", "--porcelain", lease_arg, remote, commit_sha + ":" + ref]
    _git(args, token=token)
    actual = _remote_sha(remote, branch, token)
    if actual != commit_sha:
        raise LeaseGitError("Lease update could not be verified; ownership is unknown.")


def claim_or_renew(*, operation: str, task_id: str, owner: str, claim_id: str,
                   base_sha: str, duration_minutes: int, now: str,
                   repository: str, token: str, previous_claim_id: str | None = None) -> dict[str, Any]:
    if operation not in {"claim", "renew"}:
        raise LeaseGitError("Operation must be claim or renew.")
    if not SHA_RE.fullmatch(base_sha):
        raise LeaseGitError("A full pinned base commit SHA is required.")
    remote = _remote_url(repository)
    branch = lock_branch(task_id)
    observed = _remote_sha(remote, branch, token)
    if observed is None:
        if operation == "renew":
            raise LeaseGitError("Cannot renew a lease whose lock ref does not exist.")
        record = make_lease(task_id=task_id, owner=owner, claim_id=claim_id,
                            base_sha=base_sha, now=now, duration_minutes=duration_minutes)
        parent = base_sha
        expected = None
    else:
        fetched = _fetch_head(remote, branch, token)
        if fetched != observed:
            # The ref moved during observation; retry from a fresh read, never guess.
            raise LeaseGitError("Lock ref changed during read; retry the operation.")
        current = _read_lease(fetched, token)
        if current["task_id"] != task_id or current["base_sha"] != base_sha:
            raise LeaseGitError("Existing lease is bound to a different task or base commit.")
        proposed = make_lease(task_id=task_id, owner=owner, claim_id=claim_id,
                              base_sha=base_sha, now=now, duration_minutes=duration_minutes)
        if operation == "claim":
            plan = transition_plan(current, proposed, observed_ref_sha=fetched, now=now)
        else:
            from .github_lease import renew_plan
            if previous_claim_id is None:
                raise LeaseGitError("Renewal requires --previous-claim-id for the active claim.")
            plan = renew_plan(current, proposed, observed_ref_sha=fetched,
                              owner=owner, claim_id=previous_claim_id, now=now)
        record, parent, expected = plan["record"], fetched, plan["expected_sha"]
    commit = _commit_record(parent, record, token)
    _push(remote, branch, commit, expected, token)
    return {"task_id": task_id, "owner": owner, "claim_id": claim_id,
            "status": record["status"], "lock_branch": branch, "lock_commit": commit,
            "verified": True}


def release(*, task_id: str, owner: str, claim_id: str, now: str,
            repository: str, token: str) -> dict[str, Any]:
    remote = _remote_url(repository)
    branch = lock_branch(task_id)
    observed = _remote_sha(remote, branch, token)
    if observed is None:
        raise LeaseGitError("Lock ref does not exist.")
    fetched = _fetch_head(remote, branch, token)
    if fetched != observed:
        raise LeaseGitError("Lock ref changed during read; retry the operation.")
    current = _read_lease(fetched, token)
    plan = release_plan(current, observed_ref_sha=fetched, owner=owner,
                        claim_id=claim_id, now=now)
    commit = _commit_record(fetched, plan["record"], token)
    _push(remote, branch, commit, plan["expected_sha"], token)
    return {"task_id": task_id, "owner": owner, "claim_id": claim_id,
            "status": "released", "lock_branch": branch, "lock_commit": commit,
            "verified": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("claim", "renew", "release"))
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--owner", choices=("chatgpt", "grok"), required=True)
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--previous-claim-id")
    parser.add_argument("--base-sha")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--now", default=None)
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    now = args.now or _now()
    try:
        if args.operation in {"claim", "renew"}:
            if not args.base_sha:
                raise LeaseGitError("--base-sha is required for claim/renew.")
            result = claim_or_renew(
                operation=args.operation, task_id=args.task_id, owner=args.owner,
                claim_id=args.claim_id, base_sha=args.base_sha,
                duration_minutes=args.minutes, now=now, repository=repository,
                token=token or "", previous_claim_id=args.previous_claim_id,
            )
        else:
            result = release(task_id=args.task_id, owner=args.owner,
                             claim_id=args.claim_id, now=now,
                             repository=repository, token=token or "")
    except (LeaseGitError, LeaseError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
