# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable programming collaborator with durable project memory and safe execution.

## P0 — Finish the memory/agent foundation

1. Review and merge the documentation PR only after user approval.
2. Verify whether PR #1's initial documentation should be closed, superseded, or retained; do not merge both blindly.
3. Decide whether the PR-validation workflow in PR #2 should be merged separately. Its merge is not a production release trigger by itself, but do not merge without approval.
4. After any merge, refresh the main SHA and mark this memory snapshot current only after re-verification.

## P1 — Make the agent's knowledge executable

1. Build a symbol/call graph for `lib/main.dart` (functions, callers, shared state, persistence, API actions).
2. Create focused automated tests for recovery admission, payment token ownership, profile switching, and lifecycle restoration.
3. Establish a repeatable baseline: format, analyze, test, debug build; preserve logs/artifact references.
4. Add a lightweight documentation freshness check that flags source changes affecting documented files.
5. Add a task template requiring context loaded, scope, branch, diff, tests, PR, and memory update.

## P2 — Close critical source-level risks (separate code PRs)

1. Fix and test `connect_timeout` recovery allowlist mismatch.
2. Define a single live-verification invariant for resume and normal connection paths.
3. Bind pending payment tokens to invoice owner/context and verify backend behavior.
4. Design encrypted credential storage migration.
5. Coordinate POST-body credential transport with backend owner.
6. Review `onRevoke` behavior with Android device tests.

## P3 — Backend visibility

Obtain read-only access to the authoritative backend source before making security/payment claims or changing API semantics. Map server-side authorization, invoice creation/approval, idempotency, and rate limits.

## Explicitly out of current priority

Do not prioritize new product features, visual redesigns, marketing, or unrelated refactors until the agent can reliably understand, verify, and maintain the existing project—unless the user explicitly changes the priority.
