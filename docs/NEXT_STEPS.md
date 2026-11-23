# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- Current main: a09cdb0be35e3072be29973f7ae8df66ab44d07f.
- PR #16, #17, #18, and #19 are merged. PR #18 refreshed the authoritative project-memory documents after PR #19.
- Post-merge Project Memory Audit #45069210457 succeeded on the current main commit.
- App version remains 2.4.5+284; lib/main.dart, native tunnel implementation, production release workflow, bot, payment, backend, and server behavior remain outside this PR.
- PR #20 is Draft/open/unmerged on design/task-execution-orchestrator-20261123, based on the pinned main SHA above. No merge/release/deployment is authorized.
- Project Memory Audit #45119111241 and Non-production PR Validation #45119111328 both succeeded on 66a8f860a7e119861b9b656c9f2c55d229867936.
- Runtime preflight on the preceding code head reported blocked with seccomp_filter_not_visible, delegated_cgroup_controls_not_available, and docker_socket_present_on_host. eligible_for_untrusted_agent_execution remained false.
- docs/ISOLATED_WORKER_ARCHITECTURE_DECISION.md records the one-task ephemeral VM architecture candidate.
- docs/MANAGED_SANDBOX_CANDIDATE_EVALUATION.md compares E2B and Daytona using their public documentation. E2B is selected as the first candidate for a no-agent, harmless-payload pilot; Daytona remains the alternative. This is not vendor approval or evidence of a passed runtime test.
- No vendor account, key, sandbox, subscription, payment method, infrastructure, private source upload, or provider integration has been created.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution.

## P0 — Build and validate the coding-agent collaborator

1. **Implemented:** local Python standard-library orchestrator with branch/origin/base pinning, declared-scope enforcement, fixed verification profiles, stable-source checks, append-only attempts, latest-attempt semantics, and human-reviewed handoff.
2. **CI-verified on earlier implementation heads:** orchestrator lifecycle, Flutter analysis/tests, debug smoke build, and ARM64 validation build. CI build evidence is not physical-device VPN runtime evidence.
3. **Implemented:** provider-neutral coding-agent contract and strict task-envelope/result schema validation with adversarial fixtures.
4. **Implemented:** read-only provider interface with immutable task envelope and validated structured response. Fixture only; no live provider, SDK, API key, network, shell, or filesystem capability. This interface is not an OS sandbox.
5. **Implemented:** unified-diff patch guard and a result-to-patch integrity pipeline. It checks exact SHA-256, reported byte count, allowed/excluded paths, protected paths, diff structure, and exact agreement with agent-declared changed paths. A pass means validated_for_human_review; the patch is never applied.
6. **CI-verified:** segment-aware scope matching shared by the agent contract and patch guard, with regression tests. Project Memory Audit #45113429133 and Non-production PR Validation #45113429119 succeeded on 363fe8066358646ce696baecaf876a4222bf8149.
7. **Implemented:** docs/ISOLATED_AGENT_WORKSPACE_BOUNDARY.md defines OS-level isolation requirements, threat boundaries, patch handoff, adversarial acceptance tests, and runtime-selection criteria.
8. **Implemented and CI-executed:** read-only CI isolation inventory for runtime-tool discovery and selected kernel/user-namespace/cgroup/seccomp metadata.
9. **CI-verified:** controlled benign Bubblewrap self-test passed five checks: separate network namespace, read-only source mount, writable scratch mount, hidden host sentinel, and denied outbound connectivity. It does not execute agent code or prove a complete sandbox.
10. **CI-verified:** read-only cgroup v2 inventory and tests. The runner's process cgroup is not writable; cgroup.subtree_control is empty; cpu.max and memory.max are max; pids.max is 17436.
11. **Implemented and CI-verified:** fail-closed sandbox preflight correctly classifies the hosted runner as blocked. Passing this preliminary gate is not authorization to execute untrusted code.
12. **Current environment decision:** hosted runner reports Seccomp mode 0, no delegated cgroup write access, and a Docker socket on the host. Do not bypass these restrictions or try to change the parent cgroup. This runner is unsuitable for the intended untrusted-code worker under the current boundary.
13. **Architecture decision recorded:** a one-task ephemeral VM provisioned by a separate control plane is preferred over a long-lived self-hosted runner.
14. **Managed runtime candidate evaluation recorded:** E2B is first candidate for a controlled pilot; Daytona remains an alternative. E2B's network defaults to open and must be explicitly disabled. Domain allowlists have DNS and protocol caveats. No provider documentation is treated as proof of our account's runtime controls.
15. **Next:** after explicit owner approval only, create a dedicated E2B project/key and run a harmless synthetic-payload acceptance pilot. No model, private repository source, GitHub token, secrets, network egress, or paid upgrade. Verify actual microVM class, deny-all egress, limits, timeout kill, process-tree termination, artifact bounds, and destruction. If any gate fails, remain blocked. Review DPA, subprocessors, region and retention before any private source upload.
16. Keep model execution outside GitHub write permissions. No direct commit/push/PR/merge/release/deploy capability; no production workflow dispatch.

## P1 — Reconcile outstanding draft work

- Review existing draft PRs for overlap, stale base SHAs, and whether their changes are already represented in main. Do not merge blindly.
- PR #15 contains an earlier task-protocol/template draft; compare it with the current main template and the new orchestrator design before deciding whether it is superseded.
- Keep payment-related PR #14 parked at the user's direction unless a concrete issue is raised.

## P2 — Cross-repository project memory

- Perform a read-only architecture and workflow inventory of jetconfig-vpn-tv and hesabgar_man.
- Establish repository-specific agent instructions and a shared project map only after verifying each repository's current source.
- Keep JET VPN Android as the primary development priority.

## Deferred by user

- Telegram bot, payment, backend, and server changes: currently working; defer absent a concrete issue.
- Product features, marketing, and visual redesigns: lower priority than collaborator reliability and verification.

## Approval and safety boundary

- Do not commit directly to main.
- Do not merge PRs without explicit user approval.
- Do not publish releases, create production tags, deploy, or dispatch the production workflow without explicit approval.
- Do not change app version, signing, production package identity, bot/payment/backend/server behavior as part of memory/orchestrator work.
