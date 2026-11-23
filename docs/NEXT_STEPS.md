# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) succeeded on the current main commit.
- App version remains `2.4.5+284`; `lib/main.dart`, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior remain outside this PR.
- PR #20 is Draft/open/unmerged on `design/task-execution-orchestrator-20261123`, based on the pinned main SHA above. No merge/release/deployment is authorized.
- Latest verified Non-production PR Validation [#45116058927](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45116058927) succeeded on `aec5bf4354cd7cff59d00b7483f561e38da942fc`, including the controlled Bubblewrap self-test. The subsequent cgroup-inventory changes are newer and require fresh CI.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Build and validate the coding-agent collaborator

1. **Implemented:** local Python standard-library orchestrator with branch/origin/base pinning, declared-scope enforcement, fixed verification profiles, stable-source checks, append-only attempts, latest-attempt semantics, and human-reviewed handoff.
2. **CI-verified on earlier implementation heads:** orchestrator lifecycle, Flutter analysis/tests, debug smoke build, and ARM64 validation build. CI build evidence is not physical-device VPN runtime evidence.
3. **Implemented:** provider-neutral coding-agent contract and strict task-envelope/result schema validation with adversarial fixtures.
4. **Implemented:** read-only provider interface with immutable task envelope and validated structured response. Fixture only; no live provider, SDK, API key, network, shell, or filesystem capability. This interface is not an OS sandbox.
5. **Implemented:** unified-diff patch guard and a result-to-patch integrity pipeline. It checks exact SHA-256, reported byte count, allowed/excluded paths, protected paths, diff structure, and exact agreement with agent-declared changed paths. A pass means only `validated_for_human_review`; the patch is never applied.
6. **CI-verified:** segment-aware scope matching shared by the agent contract and patch guard, with regression tests. Project Memory Audit #45113429133 and Non-production PR Validation #45113429119 succeeded on `363fe8066358646ce696baecaf876a4222bf8149`.
7. **Implemented:** `docs/ISOLATED_AGENT_WORKSPACE_BOUNDARY.md` defines OS-level isolation requirements, threat boundaries, patch handoff, adversarial acceptance tests, and runtime-selection criteria. It is a design contract only; no complete sandbox or live provider exists.
8. **Implemented and CI-executed:** read-only CI isolation inventory for runtime-tool discovery and selected kernel/user-namespace/cgroup/seccomp metadata. This is reconnaissance, not sandbox proof.
9. **CI-verified:** controlled benign Bubblewrap self-test passed five checks on run #45116058927: separate network namespace, read-only source mount, writable scratch mount, hidden host sentinel, and denied outbound connectivity. It does not execute agent code or prove a complete sandbox.
10. **Implemented, awaiting fresh CI:** read-only cgroup v2 inventory now inspects the current process cgroup path, controller names, `cpu.max`, `memory.max`, `pids.max`, `cgroup.subtree_control`, and directory write-access indicators. It does not write cgroup files, create child cgroups, or prove resource-limit enforcement.
11. **Next:** use the new CI inventory to decide whether the runner actually delegates child cgroups. Then separately validate seccomp policy, CPU/memory/PID/disk enforcement, process-tree cancellation, and cleanup. Do not enable untrusted agent code until every required control is demonstrated.
12. Keep model execution outside GitHub write permissions. No direct commit/push/PR/merge/release/deploy capability; no production workflow dispatch.

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
