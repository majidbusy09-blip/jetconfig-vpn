# Lease-Verified Task Handoff (v2)

## Purpose

The handoff artifact binds a validated GitHub task Issue to the exact, remotely verified lease created by the trusted Issue-comment command workflow. It gives an implementation agent one compact, machine-readable starting point instead of requiring it to reconstruct the command, task payload, and lease state from separate comments and artifacts.

## When it is created

- A successful `/jet-agent claim` creates a handoff artifact.
- A successful `/jet-agent renew` creates a replacement handoff artifact with the new claim ID and expiry.
- A `/jet-agent release` does not create a handoff.
- The workflow uploads the JSON handoff artifact to the same GitHub Actions run for 14 days, then automatically accepts it in a clean local runner workspace and uploads a second `jet-agent-input` artifact containing the prepared contract v1.2 agent envelope. The Issue comment reports the workflow run URL and artifact names; open the run to retrieve each artifact.

## Contents and integrity

The manifest contains:
- Repository identity and Issue number/URL.
- SHA-256 digest of the exact Issue body used for validation.
- The fully validated task payload, including goal, capability, risk, assigned agent, allow/exclude paths, and fixed verification profiles.
- Lease owner, fresh claim ID, active status, expiry, pinned base SHA, lock branch, and lock commit SHA. Renewal handoffs also carry the exact previous claim ID so a local workspace can prove continuity.
- GitHub Actions run ID and attempt.
- Explicit execution flags showing that no model was dispatched or called, no source was uploaded, and no patch was applied.

The builder validates the Issue event again and requires an exact match between the Issue command and the lease result. It rejects mismatched task IDs, Issue numbers, owners, claim IDs, lock branches, malformed SHAs, unverified/released/expired leases, and malformed run identities.

## Security boundary

The handoff builder is local and data-only. It does not make network requests, read repository source files, invoke a model, run commands from the Issue, or modify the lease. The only uploaded file is the bounded JSON task/lease manifest, stored as a GitHub Actions artifact in the same repository.

The artifact is an audit snapshot, not proof that a model has been awakened or that a runtime is available. A user-activated ChatGPT or Grok chat verifies the current lease, reads project memory and in-scope source at the pinned base through its existing GitHub integration, creates a dedicated remote branch, validates changes through GitHub Actions, and submits a Draft PR. This connector-based route does not require a separate model API, source upload, or arbitrary-code runtime. Human review and explicit approval remain required for merge, release, and deployment.

## Retention

Artifacts are retained for 14 days by default. The GitHub lease ref remains the authoritative ownership record; the artifact is an immutable snapshot for handoff and audit, not a lock.

## Local acceptance and recovery

The normal claim/renew workflow creates a lease-verified handoff artifact and attempts to prepare a local agent-input envelope in the ephemeral Actions workspace. These are audit/recovery artifacts; they are not automatically attached to a ChatGPT/Grok chat. For the approved connector route, the agent reads the Issue, lock ref, pinned project-memory documents, and relevant in-scope files directly through GitHub. The handoff artifact is optional unless a local clone needs its machine-readable snapshot.

If automatic preparation fails, or an agent is running in a separate local clone, download the handoff ZIP. The acceptance command re-fetches the current Issue and lease and can create the task branch in that local clone from the exact pinned base SHA. Use a short-lived token with only the required read permissions for acceptance; separate write permissions are needed only if the local clone later pushes commits. Never put a token in an Issue, task file, or commit.

The acceptance command does not push the branch, modify the remote lease, invoke a model, upload source, or apply a patch. Source files are not automatically added to context; use the existing advisory suggest-context and explicit accept-context --path commands when running the local CLI.

If the lease is renewed after the local task was prepared, download the newest handoff artifact and rerun with --refresh-existing; it updates only lease provenance in the local task record and leaves the agent envelope and working files untouched. Refresh is accepted only when the Issue body, owner, task definition, pinned base, and exact previous claim ID all match. If the lease was released, expired, or changed incompatibly, acceptance is rejected.

## Approved ChatGPT/Grok connector route

The user activates one implementation chat at a time and supplies the task Issue URL. The chat uses its existing GitHub integration; no model API key, paid model API endpoint, or external source-upload adapter is part of this design. If the integration cannot post Issue comments, the user posts the /jet-agent claim command. The agent waits for the trusted workflow's verified result, then independently reads the agent-locks/<task_id> ref and checks owner, claim ID, active status, expiry, pinned base SHA, and lock commit.

The agent creates its remote implementation branch from the exact pinned base SHA. The ephemeral branch created by local acceptance in Actions is not the remote implementation branch. The agent reads the required memory documents and only files allowed by the Issue, commits through the GitHub integration, opens a Draft PR with jet-agent-pr:v1 metadata, and reports exact commit/check evidence. A second agent may review read-only but must not edit the same task. Chat sessions do not wake automatically or poll in the background.

The connector may process GitHub content under the provider's integration and account policies; do not claim that data never leaves GitHub. The user-approved restriction is no separate paid model API, API key, or manual source upload to an external model endpoint. Arbitrary untrusted-code execution remains disabled; fixed CI checks and human review are separate controls.
