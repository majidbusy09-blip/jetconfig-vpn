# ChatGPT GitHub Connector Pilot

## Scope

This file records a documentation-only test of the user-activated ChatGPT GitHub connection. It intentionally changes no application source, workflow, credentials, payment behavior, release configuration, or production resource.

## Verified steps

- Task Issue: #90.
- Task owner label: chatgpt.
- Active lease: verified from the GitHub lock ref `agent-locks/github-connector-docs-pilot`.
- Claim ID: `9020261124183330`.
- Lease lock commit: `ee479b5aef75134dc8cb8f88474ca0d815463a83`.
- The lock ref was read before and after the lease JSON; both reads returned the same commit SHA.
- Pinned implementation base: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e`.
- Remote implementation branch: `agent/github-connector-docs-pilot`, created directly from the pinned base SHA.
- GitHub connector operations used in this pilot: read Issue and comments, read lock ref and lease blob, create branch, create file commit, and open a Draft PR.

## Boundaries

- The handoff and agent-input artifacts were created by GitHub Actions but were not used as automatic chat attachments.
- No model API key, paid model API endpoint, external source-upload adapter, or sandbox was used.
- No arbitrary code was executed. The declared verification profile is handled by GitHub Actions.
- The lease owner is a protocol label selected for this task, not cryptographic proof of model identity.
- This PR must remain unmerged until human review. The lease should be released after verification is complete.