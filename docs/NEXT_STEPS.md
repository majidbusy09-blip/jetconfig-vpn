# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable programming collaborator with durable project memory and safe execution. Every candidate task must pass the question in `AGENTS.md`; tasks that fail it are deferred unless explicitly requested.

## P0 — Activate and validate the memory/agent foundation

1. Complete review of PR #4 after rebasing it onto the merged PR #3 baseline; require a fresh successful memory-audit run and inspect its artifact.
2. After PR #4 is approved and merged, verify the audit workflow runs on relevant pull requests and catches a stale index in a safe test branch.
3. Decide whether PR #1's initial documentation should be closed as superseded; do not merge it alongside PR #3.
4. Decide separately whether PR #2's isolated PR-validation workflow should be merged; it is not a production release trigger, but still requires explicit approval.
5. Ensure every task loads project memory, checks current source, works on an isolated branch, reports exact verification, and updates memory when needed.

## P1 — Make the agent's knowledge executable

1. Upgrade the lexical Dart index toward semantic AST and call/reference relationships using Dart tooling where feasible; label all limitations.
2. Compare lexical index output with Dart Analyzer output and document false positives/omissions before relying on it for navigation.
3. Create focused automated tests for recovery admission, payment-token ownership, profile switching, and lifecycle restoration.
4. Establish a repeatable baseline: format, analyze, test, debug build; preserve logs and artifact references.
5. Extend source-fingerprint coverage to additional documented files and symbol-level evidence as the architecture is split across files.
6. Add a task template requiring context loaded, priority test, scope, branch, diff, tests, PR, and memory update.

## P2 — Close critical source-level risks (separate code PRs)

1. Fix and test `connect_timeout` recovery allowlist mismatch.
2. Define a single live-verification invariant for resume and normal connection paths.
3. Bind pending payment tokens to invoice owner/context and verify backend behavior.
4. Design encrypted credential storage migration.
5. Coordinate POST-body credential transport with backend owner.
6. Review `onRevoke` behavior with Android device tests.

## P3 — Backend visibility

Obtain read-only access to authoritative backend source before making security/payment claims or changing API semantics. Map server-side authorization, invoice creation/approval, idempotency, and rate limits.

## Explicitly out of current priority

Do not prioritize new product features, visual redesigns, marketing, or unrelated refactors until the agent can reliably understand, verify, and maintain the existing project—unless the user explicitly changes the priority.
