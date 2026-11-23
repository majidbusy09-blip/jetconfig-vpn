# ADR-001 — Isolated coding-agent worker architecture

- **Status:** proposed architecture decision; no worker provisioned or enabled
- **Date:** 2026-11-23
- **Scope:** PR #20, non-production coding-agent execution only
- **Decision owner:** project owner; this record is a technical recommendation, not deployment approval

## Context

The current GitHub-hosted validation runner passed a controlled Bubblewrap self-test for network namespace separation, read-only source, writable scratch, hidden host sentinel, and denied outbound connectivity. That is useful partial evidence, but the same runner's read-only inventory reported:

- Seccomp mode 0 (no filter visible for the inspected process).
- No writable delegated cgroup controls; cgroup.subtree_control is empty.
- cpu.max and memory.max are max; pids.max is 17436.
- The conventional Docker socket path exists on the host.

The fail-closed preflight therefore correctly reports blocked. The runner must not be used to execute untrusted model-generated code, and host ownership/cgroup restrictions must not be bypassed.

## Options evaluated

| Option | Advantages | Blocking risks / limitations | Decision |
|---|---|---|---|
| Current GitHub-hosted runner as the worker | Already integrated with CI; simple artifact flow | Actual host evidence fails Seccomp/cgroup/socket gates; the workflow runner is not a demonstrated untrusted-code boundary | **Reject for agent execution** |
| Long-lived self-hosted runner | More host configuration control | Persistent host state, residual workspaces, credentials, runner compromise/persistence, and cross-task contamination; requires substantial hardening and lifecycle controls | **Reject as the default** |
| One-task ephemeral VM worker, provisioned by a separate control plane | Dedicated kernel/VM boundary per attempt; can explicitly delegate cgroups, enforce Seccomp, omit host credentials/sockets, and destroy the VM after each task | Requires infrastructure, secure provisioning, attestation/acceptance tests, cost controls, and reliable cleanup evidence | **Preferred candidate to prototype** |
| Managed isolated execution service | May provide a maintained isolation boundary and faster initial implementation | Product claims are insufficient; must verify filesystem/network policy, process/resource limits, secret isolation, data retention, artifact export, cancellation, and auditability against this project's exact threat model | **Keep as a parallel candidate** |

## Proposed trust boundaries

1. **Orchestrator/control plane:** owns task identity, project memory, pinned repository/base SHA, scope, budgets, provider credentials, verification policy, and audit records. It does not execute agent-produced code.
2. **Model/provider:** receives only the bounded task context it needs and proposes edits. It receives no GitHub write token, signing key, production secret, or unrestricted host access.
3. **Worker broker/provisioner:** creates a fresh, one-task VM from a pinned image and verified source snapshot. Its privileged provisioning authority is not exposed to the model or worker.
4. **Untrusted worker sandbox:** runs as a non-root identity with read-only source, per-attempt writable scratch, no host home, no SSH/Git credentials, no Docker/runtime socket, no cloud metadata access, no devices, and no network egress. Enforce CPU, memory, PID, disk, and wall-clock limits with delegated cgroups; enforce syscall policy with a verified Seccomp profile; kill the complete process tree.
5. **Artifact return channel:** exports only a bounded patch, changed-path manifest, and bounded diagnostics. The orchestrator independently validates all returned bytes and metadata. No worker-side Git commit, push, PR, merge, release, deployment, or production dispatch.
6. **Verification and human review:** trusted fixed verification runs only after patch acceptance in a separate controlled environment; human review remains mandatory.

The model must not control VM provisioning, sandbox policy, mount configuration, network rules, host process supervision, or cleanup.

## Mandatory acceptance gates before any untrusted execution

All checks must run against the actual candidate runtime and fail closed:

- Prove worker UID is non-root and no extra capabilities/privileged mode are present.
- Prove Seccomp filtering is active inside the worker and test denied syscall cases, not merely host metadata.
- Prove delegated cgroup v2 limits are created and enforced for CPU, memory, and PID count.
- Prove source is read-only and scratch is writable; host home, sentinel, secrets, signing files, devices, runtime sockets, and metadata endpoints are inaccessible.
- Prove network, DNS, IPv4/IPv6 egress, and alternate network paths are denied.
- Prove wall-clock, disk, output, process, and memory limits are enforced.
- Prove timeout/cancellation kills descendants, including detached/background processes.
- Prove cleanup on success, failure, timeout, cancellation, provisioning error, and host error; cleanup failure blocks the task.
- Prove every attempt uses a distinct VM/workspace and cannot observe prior-attempt residue.
- Prove exported patch path normalization, scope, protected-path, size, and digest checks are independently enforced by the orchestrator.
- Record immutable image digest, policy version, task/attempt IDs, source/base SHA, limits, timestamps, and cleanup result.
- Run adversarial tests repeatedly on the target runner class; a unit test of configuration or a successful benign Bubblewrap test alone is not acceptance.

A candidate that cannot expose evidence for any gate is rejected. A preflight pass is not itself authorization.

## Implementation sequence

1. Keep the current hosted runner limited to trusted repository CI and benign runtime reconnaissance.
2. Prototype the worker broker and one-task VM lifecycle using a harmless, fixed test payload; do not connect a live coding model.
3. Implement the acceptance suite and collect machine-readable evidence for every gate above.
4. Demonstrate teardown and cleanup-failure behavior, including killing the complete process tree.
5. Only after all gates pass, propose a separate, read-only provider integration PR. Provider credentials stay in the control plane.
6. Later, separately propose patch-producing integration. The first patch flow remains validate-only until a dedicated application gate is reviewed.
7. Evaluate a managed execution service against the same checklist before choosing self-managed infrastructure; do not lower requirements to fit a vendor.

## Explicit non-goals and approval boundary

This ADR does not provision cloud infrastructure, create accounts, incur spend, install a runner, connect a provider, enable network access, execute agent-generated code, apply patches, grant GitHub write permissions, or authorize merge/release/deployment. Those are separate decisions requiring explicit approval.

PR #20 remains Draft and unmerged. Production app, bot, payment, backend, server, signing, and release behavior remain out of scope.
