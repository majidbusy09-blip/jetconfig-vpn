# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) succeeded on the current main commit.
- App version remains `2.4.5+284`; `lib/main.dart`, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior remain outside this PR.
- PR #20 is Draft/open/unmerged on `design/task-execution-orchestrator-20261123`, based on the pinned main SHA above. No merge/release/deployment is authorized.
- Latest verified CI before the current patch-pipeline commits: Project Memory Audit #45110490054 and Non-production PR Validation #45110490052 both succeeded on `fc2ad137707a91a2cad72277239b72ed69171e36`. Newer patch-pipeline commits require fresh CI.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Build and validate the coding-agent collaborator

1. **Implemented:** local Python standard-library orchestrator with branch/origin/base pinning, declared-scope enforcement, fixed verification profiles, stable-source checks, append-only attempts, latest-attempt semantics, and human-reviewed handoff.
2. **CI-verified on earlier implementation heads:** orchestrator lifecycle, Flutter analysis/tests, debug smoke build, and ARM64 validation build. CI build evidence is not physical-device VPN runtime evidence.
3. **Implemented:** provider-neutral coding-agent contract and strict task-envelope/result schema validation with adversarial fixtures.
4. **Implemented:** read-only provider interface with immutable task envelope and validated structured response. Fixture only; no live provider, SDK, API key, network, shell, or filesystem capability. This interface is not an OS sandbox.
5. **Implemented:** unified-diff patch guard and a result-to-patch integrity pipeline. It checks exact SHA-256, reported byte count, allowed/excluded paths, protected paths, diff structure, and exact agreement with agent-declared changed paths. A pass means only `validated_for_human_review`; the patch is never applied.
6. **Verified on patch-guard/scope head:** Project Memory Audit #45113429133 and Non-production PR Validation #45113429119 both succeeded on `363fe8066358646ce696baecaf876a4222bf8149`.
7. **Implemented after that CI head:** segment-aware scope matching shared by the agent contract and patch guard, with regression tests. Fresh CI is required on the newest head before these later commits are treated as verified.
8. **Implemented:** `docs/ISOLATED_AGENT_WORKSPACE_BOUNDARY.md` defines OS-level isolation requirements, threat boundaries, patch handoff, adversarial acceptance tests, and runtime-selection criteria. It is a design contract only; no sandbox or live provider exists.
9. **Next:** select and verify an isolation runtime on the actual CI host against the adversarial acceptance tests. Do not substitute a temporary directory or ordinary Git worktree and call it a sandbox. Implement a disposable worker only after runtime isolation passes; provider selection/integration remains later and separately permission-limited.
8. Keep model execution outside GitHub write permissions. No direct commit/push/PR/merge/release/deploy capability; no production workflow dispatch.

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
