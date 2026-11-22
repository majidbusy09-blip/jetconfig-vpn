# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) succeeded on the current main commit.
- App version remains `2.4.5+284`; `lib/main.dart`, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior were not changed by PR #18.
- The active `main-protection` ruleset remains in force. No direct-main write, bypass, release, or deployment.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Design and implement the task execution orchestrator

1. **Design in progress:** `docs/TASK_ORCHESTRATOR_DESIGN.md` defines a small Python 3.12, standard-library-only local orchestrator.
2. **Next:** implement a fail-closed local MVP that loads required context, pins repository/branch/base SHA, fingerprints scoped files, reuses semantic/critical-path reports, validates changed paths, runs only fixed verification profiles, and produces an auditable task record and PR handoff.
3. Add unit/integration tests using temporary Git repositories; no GitHub credentials or network should be required.
4. Integrate tests into existing non-production PR validation only after the local test suite is stable. Do not add a required status check until reliability is demonstrated.
5. Keep GitHub PR creation as a later optional phase. The orchestrator must not merge, release, tag, deploy, or dispatch the production workflow.

## P1 — Reconcile outstanding draft work

- Review existing draft PRs for overlap, stale base SHAs, and whether their changes are already represented in main. Do not merge blindly.
- PR #15 contains an earlier task-protocol/template draft; compare it with the current main template and the new orchestrator design before deciding whether it is superseded.
- Keep payment-related PR #14 parked at the user's direction unless a concrete issue is raised.

## P2 — Cross-repository project memory

- Perform a read-only architecture and workflow inventory of `jetconfig-vpn-tv` and `hesabgar_man`.
- Establish repository-specific agent instructions and a shared project map only after verifying each repository's current source.
- Keep JET VPN Android as the primary development priority.

## Deferred by user

- Telegram bot, payment, backend, and server changes: currently working; defer absent a concrete issue.
- Product features, marketing, and visual redesigns: lower priority than collaborator reliability and verification.

## Approval and safety boundary

- Do not commit directly to `main`.
- Do not merge PRs without explicit user approval.
- Do not publish releases, create production tags, deploy, or dispatch the production workflow without explicit approval.
- Do not change app version, signing, production package identity, bot/payment/backend/server behavior as part of memory/orchestrator work.
