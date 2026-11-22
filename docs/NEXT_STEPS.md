# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable programming collaborator with durable project memory and safe execution. Every candidate task must pass the question in `AGENTS.md`; tasks that fail it are deferred unless explicitly requested.

## P0 — Activate and validate the memory/agent foundation

1. **Completed:** PR #4 was merged after a fresh successful audit on the final PR head; the generated index and source fingerprint matched.
2. **Completed:** PR #7's disposable negative test proved that the audit workflow triggers on PRs and rejects a deliberately stale source fingerprint; the test PR was closed unmerged.
3. Decide whether PR #1's initial documentation should be closed as superseded; do not merge it alongside PR #3.
4. Decide separately whether PR #2's isolated PR-validation workflow should be merged; it is not a production release trigger, but still requires explicit approval.
5. Ensure every task loads project memory, checks current source, works on an isolated branch, reports exact verification, and updates memory when needed.

## P1 — Make the agent's knowledge executable

1. **In progress in PR #8:** AST-based declaration and syntactic call-site extraction, with ambiguity/unresolved labels and focused tooling tests.
2. **Completed for PR #8:** CI is green; the AST output remains explicitly syntactic and is not a semantic call graph. Side-by-side comparison with analyzer-resolved Elements is the current follow-up.
3. **Implemented in PR #9; review pending:** analyzer Elements resolve invocation nodes using the app package context; same-name methods, dynamic calls, and app package URI classification have focused tests. Latest PR #9 CI Run #57 passed after enabling the next dependent PR audit trigger. Keep this graph labeled as a static call graph, not runtime reachability.
4. **Implemented in PR #10; review pending:** discover and resolve all tracked Dart files under `lib/`, build cross-file Element edges, and generate source-linked reachability reports for curated VPN, lifecycle, payment, and profile entrypoints. CI Run #58 passed; all 16 configured entrypoints resolved. The current repository still has one tracked Dart file, while a two-file fixture verifies cross-file behavior. Java patch files are linked as boundaries, not analyzed as Dart.
5. **PR #11 implemented and fully CI-verified:** recovery policy extraction and tests for `connect_timeout`, unknown reasons, intent gates, and cooldowns. Runtime/device behavior remains to be checked.
6. Establish a repeatable baseline: format, analyze, test, debug build; preserve logs and artifact references.
7. Extend source-fingerprint coverage to additional documented files and symbol-level evidence as the architecture is split across files.
8. Add a task template requiring context loaded, priority test, scope, branch, diff, tests, PR, and memory update.

## P2 — Close critical source-level risks (separate code PRs)

1. **PR #11 implementation and full CI completed:** fix `connect_timeout` recovery allowlist mismatch. Runtime/device verification remains outstanding.
2. **Implemented and full CI passed in PR #12:** apply one live-verification invariant to UI, cold restore, and app resume. Device validation remains required.
3. **Implemented and CI-verified in PR #13:** isolate the async live-ping/retry sequence behind injected dependencies; all 15 app tests and full project-memory audit passed. Android lifecycle/device verification remains required.
4. **Implemented and CI-verified in PR #14:** persist the payment token with originating username, creation timestamp, and pending status; block cross-profile polling; cancel stale polling after account/password changes. All 19 app tests and full project-memory audit passed. Backend ownership enforcement remains unverified.
5. Obtain read-only backend access and verify invoice ownership, replay/idempotency, and authorization. Never test against production without approval.
6. Design encrypted credential storage migration.
7. Coordinate POST-body credential transport with backend owner.
8. Review `onRevoke` behavior with Android device tests.

## P3 — Backend visibility

Obtain read-only access to authoritative backend source before making security/payment claims or changing API semantics. Map server-side authorization, invoice creation/approval, idempotency, and rate limits.

## Explicitly out of current priority

Do not prioritize new product features, visual redesigns, marketing, or unrelated refactors until the agent can reliably understand, verify, and maintain the existing project—unless the user explicitly changes the priority.
