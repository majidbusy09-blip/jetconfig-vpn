# Live Patch Review Gate

## Purpose
The patch review gate is the validation-only boundary before a proposed agent patch is marked ready for human review. It binds exact patch bytes to the prepared local task and rechecks current Issue, lease, lock-ref, and workspace observations.

## Trusted observations required
The caller supplies the current GitHub Issue object, lease record and observed lock-ref commit SHA, current local branch and HEAD, pinned-base ancestry result, and worktree cleanliness. Those facts must come from trusted read-only GitHub and Git adapters.

The gate compares them with the local task record, accepted handoff metadata, and agent envelope. It then resolves the exact SHA-256 patch reference through the local content-addressed store and invokes the existing result, digest, unified-diff, and scope validators.

## Outcome
A successful result is ready_for_human_review with applied=false. It is not authorization to apply, commit, push, merge, or release. Stale or edited Issues, removed labels, expired/released/replaced leases, base or branch drift, dirty worktrees, envelope mismatches, and invalid patches fail closed.

## Boundaries
- No GitHub API or Git commands are run by this module.
- No patch is applied or executed.
- No verification profile is executed.
- No source, prompt, or patch is uploaded to a provider.
- A real isolated execution environment remains mandatory before untrusted provider code can run.
