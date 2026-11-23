# GitHub Task Ownership Leases (v1)

## Purpose

Issue comments are audit records, not locks. A read-then-comment flow permits two agents to observe an unclaimed task and both begin implementation. Unattended parallel work must remain disabled until ownership uses a Git ref compare-and-swap (CAS).

## Lock storage and acquisition

Each task has one deterministic control-plane branch: agent-locks/<task_id>. Its tip commit contains a machine-readable lease at .agent-locks/lease.json. This branch is not an implementation branch and must never be merged into product code.

1. Read and validate the task Issue.
2. Read the deterministic lock ref. If absent, create it from the task's pinned base commit. GitHub's create-ref operation is the initial uniqueness gate: one concurrent creator wins. A losing creator must re-read the ref and must not assume ownership.
3. The initial empty ref is not a claim. Read its exact head SHA, create a commit whose parent is that SHA and whose tree adds/replaces only .agent-locks/lease.json, then update the lock ref with force=true and expected_sha equal to the observed head. Only the successful CAS winner owns the lease.
4. If the lock ref exists, validate its lease. An active, unexpired lease blocks other agents. A released or expired lease may be replaced only by a commit updated with expected_sha equal to the exact head just read. Concurrent claimants can prepare commits, but only one CAS update wins.
5. The record binds task ID, owner (chatgpt or grok), unique claim ID, status, UTC claim/expiry timestamps, and pinned task base SHA. Duration is at most four hours.
6. Renew before expiry using a fresh claim ID and CAS against the exact current lock head. If renewal loses or expires, stop implementation immediately.
7. Release only with the current owner and claim ID, by committing status released and CAS-updating against the observed head. Never delete or force-reset a lock ref to release it.

The CAS check is the critical property. Never implement this as fetch-then-push without expected-head checking. Never treat an Issue comment, branch name, or local lease JSON as proof of ownership.

## Failure rules

- Existing lock ref without a valid lease file is incomplete, not free. Fail closed.
- Malformed lease, task/base mismatch, unknown owner, stale observation, API timeout with unknown outcome, or failed CAS means ownership is unknown. Re-read the ref and do not edit task files until ownership is proven.
- Expiry alone does not grant ownership; takeover requires CAS.
- A crashed agent's lease can expire; recovery uses a new claim ID and CAS.
- Keep one active implementation lease per task. Read-only reviews do not require a lease, but reviewers must not modify task branches.
- Keep task implementation branches separate from lock branches. Never merge lock branches into default branch or product releases.

## Local helper

github_lease.py validates lease records and builds deterministic CAS plans without network calls:

    python -m tools.task_orchestrator.github_lease --task-id sample-task --owner chatgpt --claim-id 0123456789abcdef --base-sha <full-pinned-git-sha> --now 2026-11-23T10:00:00Z --minutes 60

The authenticated GitHub adapter must still execute create-ref/update-ref operations, verify the final ref SHA, and report the winning claim. The local helper cannot claim ownership by itself.

## Rollout boundary

Lease record schema and deterministic state-transition rules are implemented and tested. An authenticated GitHub adapter wired into each provider runtime, autonomous agent wake-up, and automatic renewal are not yet implemented. The repository now contains an Issues-event validation workflow, but GitHub only activates that workflow after it exists on the default branch; because this PR remains unmerged, it is not active for live Issues yet. Until the adapter is implemented and exercised with concurrent claim attempts, retain one explicitly coordinated implementation agent per task; do not enable unattended parallel implementation.


## Current practical operating boundary

- On this PR branch, the Issue payload validator and event workflow can be reviewed and tested by CI.
- The workflow is intentionally read-only: `contents: read`, `issues: read`; it only uploads a task JSON artifact.
- After an authorized merge, create an Issue from the provided template and add/retain the `agent-task` label. Open, labeled, and edited events validate the payload and publish an artifact.
- The artifact is not an execution grant. An agent must independently check `assigned_agent`, repository identity, issue/body digest, pinned base SHA, and lease ownership before preparing code changes.
- GitHub ref CAS is only effective when the adapter uses the exact observed ref SHA as `expected_sha`. A plain REST ref update, Issue comment, workflow concurrency group, or local file is not a substitute for this CAS.
- No shared, automatic ChatGPT/Grok wake-up is available from this workflow alone. No paid model API, provider credential, private-source upload, or external sandbox is configured.
