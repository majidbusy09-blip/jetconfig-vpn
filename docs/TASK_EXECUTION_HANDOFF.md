# Lease-Verified Task Handoff (v1)

## Purpose

The handoff artifact binds a validated GitHub task Issue to the exact, remotely verified lease created by the trusted Issue-comment command workflow. It gives an implementation agent one compact, machine-readable starting point instead of requiring it to reconstruct the command, task payload, and lease state from separate comments and artifacts.

## When it is created

- A successful `/jet-agent claim` creates a handoff artifact.
- A successful `/jet-agent renew` creates a replacement handoff artifact with the new claim ID and expiry.
- A `/jet-agent release` does not create a handoff.
- The workflow uploads the JSON artifact to the same GitHub Actions run for 14 days and links that run in its Issue comment.

## Contents and integrity

The manifest contains:
- Repository identity and Issue number/URL.
- SHA-256 digest of the exact Issue body used for validation.
- The fully validated task payload, including goal, capability, risk, assigned agent, allow/exclude paths, and fixed verification profiles.
- Lease owner, fresh claim ID, active status, expiry, pinned base SHA, lock branch, and lock commit SHA.
- GitHub Actions run ID and attempt.
- Explicit execution flags showing that no model was dispatched or called, no source was uploaded, and no patch was applied.

The builder validates the Issue event again and requires an exact match between the Issue command and the lease result. It rejects mismatched task IDs, Issue numbers, owners, claim IDs, lock branches, malformed SHAs, unverified/released/expired leases, and malformed run identities.

## Security boundary

The handoff builder is local and data-only. It does not make network requests, read repository source files, invoke a model, run commands from the Issue, or modify the lease. The only uploaded file is the bounded JSON task/lease manifest, stored as a GitHub Actions artifact in the same repository.

The artifact is an execution handoff, not proof that a model has been awakened or that a runtime is available. An agent must still verify the lease is current before editing, obtain current project memory/source context through an authorized channel, work in an isolated runtime, validate its patch, and submit a PR. Human review and explicit approval remain required for merge, release, and deployment.

## Retention

Artifacts are retained for 14 days by default. The GitHub lease ref remains the authoritative ownership record; the artifact is an immutable snapshot for handoff and audit, not a lock.

## Accepting the artifact locally

Download the artifact ZIP from the linked GitHub Actions run. In a clean clone, create a dedicated branch from the exact pinned base SHA shown in the Issue comment:

```bash
git switch -c agent/<task-id> <pinned-base-sha>
```

Then run the acceptance command with a read-only GitHub token (contents:read and issues:read):

```bash
GITHUB_REPOSITORY=owner/repository \
GITHUB_TOKEN=<read-only-token> \
python -m tools.task_orchestrator.github_task_handoff_accept \
  --handoff-file /path/to/jet-agent-handoff.zip
```

The command reads the ZIP in memory without extracting paths, re-fetches the current Issue and lease, verifies the Issue-body digest, task payload, current claim ID, lock commit, expiry, repository identity, local origin, clean worktree, dedicated branch, and exact HEAD/base SHA match. It then initializes the existing local Task Orchestrator, builds the six required project-memory documents, and writes a contract v1.1 `agent_input.json` under the ignored local `.agent/tasks/<task-id>/` directory.

The command does not create or push a branch, modify the remote lease, invoke a model, upload source, or apply a patch. Source files are not automatically added to context; use the existing advisory `suggest-context` and explicit `accept-context --path` commands when relevant. If the lease has been renewed, released, expired, or otherwise changed, obtain the newest handoff and retry.
