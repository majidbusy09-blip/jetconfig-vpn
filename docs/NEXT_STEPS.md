# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) succeeded on the current main commit.
- App version remains `2.4.5+284`; `lib/main.dart`, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior were not changed by PR #18.
- The active `main-protection` ruleset remains in force. No direct-main write, bypass, release, or deployment.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Build and validate the coding-agent collaborator

1. **Completed:** documented the local orchestrator design and implemented its standard-library MVP under `tools/task_orchestrator/`.
2. **Completed:** branch/origin/base pinning, declared-scope enforcement, fixed verification profiles, stable-source checks, append-only attempts, latest-attempt semantics, and human-reviewed handoff are implemented and covered by integration tests.
3. **Verified on implementation head `c4acaf8c32a5c70cea2919b9eb5f2c68303b3559`:** Project Memory Audit [#45105873991](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45105873991) and Non-production PR Validation [#45105874008](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45105874008) both succeeded. The latter ran the orchestrator integration suite, app analysis/tests, and debug/ARM64 validation builds.
4. **Completed:** `docs/CODING_AGENT_ADAPTER_CONTRACT.md` defines a provider-neutral input/output contract, sandbox permissions, patch acceptance gates, audit requirements, and phased rollout. It is a design contract only; no model provider is connected yet.
5. **Completed and CI-verified on head `4dd6f8110bd9462fde73c7c9ab256a72c971c55e`:** strict schema validation and adversarial fixture tests cover malformed output, traversal, protected paths, budget limits, stale context, profile injection, and failure states. Both Project Memory Audit and Non-production PR Validation passed.
6. **Implemented on newer PR #20 commits; CI pending:** `readonly_adapter.py` defines a provider-neutral interface. It passes a deeply immutable, validated task envelope to a provider and validates structured output. A fixture provider supports tests; no live provider, SDK, API key, network, shell, filesystem access, or patch application is connected. This interface is not an OS sandbox.
7. **Next:** validate this adapter with fresh CI and review. Then select a provider and implement a separately permission-limited connector, still without filesystem writes or patch application.
6. Keep all provider/model execution outside GitHub write permissions. No direct commit/push/PR/merge/release/deploy capability; no production workflow dispatch.
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
