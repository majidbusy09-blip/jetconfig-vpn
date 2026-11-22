# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable programming collaborator with durable project memory and safe execution. Every candidate task must pass the question in `AGENTS.md`; tasks that fail it are deferred unless explicitly requested.

## P0 — Make the collaborator workflow repeatable and safe

1. **Completed:** PR #4 added the deterministic lexical source index and read-only memory audit; its final audit passed.
2. **Completed:** PR #7's disposable negative test proved the audit rejects a deliberately stale source fingerprint; the test PR was closed unmerged.
3. **Completed in this change:** add `docs/TASK_TEMPLATE.md` and make it part of the mandatory agent operating procedure.
4. PR #2's isolated validation workflow passed run #11: static analysis and debug APK build succeeded; tests were skipped because the tested revision had no `test/` directory. The PR remains open; merge only after explicit user approval.
5. Review the dependent source/tooling PR chain #8–#13 in dependency order. Do not merge any PR without explicit user approval.
6. PR #14 is payment-related and remains parked at the user's direction. Do not extend payment/backend work unless the user re-prioritizes it.
7. Keep PR #1 unmerged because its documentation overlaps with merged PR #3; close it only with explicit approval.

## P1 — Improve executable project understanding and verification

1. **Implemented in review branches, not yet on main:** PR #8 AST extraction, PR #9 analyzer-resolved Elements, and PR #10 multi-file static critical-path reports. Their CI runs passed; preserve their documented limitations and review their dependency chain.
2. **Implemented in review branches, not yet on main:** PRs #11–#13 add focused recovery and live-connection verification policies with unit tests. CI passed; Android device and real tunnel validation remain outstanding.
3. After the approved source/tooling changes are integrated, run one repeatable validation against the exact combined candidate: format, analyze, full app tests, debug APK build, and memory freshness audit. Preserve exact run IDs and artifact references.
4. Keep generated semantic graphs and critical-path reports labeled as static analysis, not runtime traces or proof of reachability.
5. Extend source-fingerprint coverage to important architecture and workflow documents without making routine maintenance excessively expensive.

## P2 — Deferred application risks

- Password storage migration, credential transport changes, and Android VPN revoke-path validation remain separate, evidence-driven tasks. Do not mix them into the collaborator-foundation work.
- Payment/backend audit and related changes are deferred while the current bot/payment service is operating normally, unless the user explicitly changes priority.

## P3 — Expand the collaborator to other projects

After the JET VPN workflow is reliable, apply the same project-memory, source-verification, isolated-branch, test, and PR process to JET VPN TV and حسابگر من. Keep each repository's source, decisions, and status separate.

## Explicitly out of current priority

Do not prioritize new product features, visual redesigns, marketing, unrelated refactors, or deferred payment work until the programming collaborator can reliably understand, verify, and maintain the existing project—unless the user explicitly changes the priority.
