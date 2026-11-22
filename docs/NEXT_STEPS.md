# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) succeeded on the current main commit.
- App version remains `2.4.5+284`; `lib/main.dart`, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior were not changed by PR #18.
- The active `main-protection` ruleset remains in force. No direct-main write, bypass, release, or deployment.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Implement and validate the task execution orchestrator

1. **Completed:** the design was documented in `docs/TASK_ORCHESTRATOR_DESIGN.md`; the design-only PR head passed both Project Memory Audit and Non-production PR Validation.
2. **In progress:** a local Python standard-library MVP now exists under `tools/task_orchestrator/`: task record, clean-branch/context preparation, base-SHA pinning, scope gates, artifact availability recording, fixed verification profiles, append-only check attempts, and final handoff.
3. **Verification pending:** run its temporary-Git-repository integration tests in CI on the latest implementation head; review/fix every failure before treating the MVP as usable.
4. **Still required:** test missing context, rename/delete scope handling, timeout behavior, stale semantic artifact labeling, and a full test pass; then inspect the complete PR diff and update the task docs.
5. CI integration is currently in the existing non-production PR validation workflow. Do not add a required branch-protection check until reliability is demonstrated.
6. GitHub PR creation remains a later optional phase. The orchestrator must not merge, release, tag, deploy, or dispatch the production workflow.

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
