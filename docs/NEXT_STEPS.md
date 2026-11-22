# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable programming collaborator with durable project memory and safe execution. Every candidate task must pass the question in `AGENTS.md`: does it bring us closer to an independent, accurate programming collaborator with project memory? If not, defer it unless explicitly requested.

## P0 — Finish and activate the memory/agent foundation

1. Complete review of PR #3's refreshed documentation and request explicit user approval before merging.
2. After PR #3 is merged, refresh the main SHA and verify the documents against the resulting source.
3. Rebase/recheck PR #4, which is based on PR #3; preserve its successful memory-index audit and ensure the generated index/fingerprint match the post-merge source.
4. Decide whether PR #1's initial documentation should be closed as superseded; do not merge it alongside PR #3.
5. Decide whether PR #2's isolated PR-validation workflow should be merged separately; it is not a production release trigger, but still requires approval.
6. Ensure every future task loads project memory, checks current source, works on a dedicated branch, reports exact verification, and updates memory when needed.

## P1 — Make the agent's knowledge executable

1. Extend the lexical Dart index toward semantic symbol and call/reference relationships using Dart tooling where feasible; clearly label limitations.
2. Create focused automated tests for recovery admission, payment token ownership, profile switching, and lifecycle restoration.
3. Establish a repeatable baseline: format, analyze, test, debug build; preserve logs/artifact references.
4. Keep the documentation freshness check strict and source-fingerprint based.
5. Add a task template requiring context loaded, priority test, scope, branch, diff, tests, PR, and memory update.

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
