# JET VPN — Isolated Coding-Agent Workspace Boundary

> Status: security and implementation contract. This document does not create a sandbox, launch a container, or authorize a live provider.
> Scope: PR #20, non-production Orchestrator work only.

## 1. Decision

A Python adapter interface, temporary directory, Git worktree, or patch validator is not an OS security boundary. The first implementation must not describe any of those alone as a sandbox.

The coding model/provider and the code-execution worker are separate trust domains:

- The provider receives a bounded task envelope and returns a structured result plus a patch artifact.
- A disposable worker validates and tests the proposed change in a restricted runtime.
- The orchestrator remains authoritative for task state, repository identity, path scope, verification evidence, and human handoff.

No live provider or worker is enabled by this contract.

## 2. Required isolation properties

A future worker is not eligible for untrusted agent-generated code until all properties below are demonstrated by automated tests and runtime inspection.

### Filesystem

- Start from an immutable, verified source snapshot pinned to the task base SHA.
- Mount the source snapshot read-only.
- Give write access only to a newly created, per-attempt scratch workspace.
- Do not mount the host home directory, SSH directory, Git credentials, Docker/container socket, cloud metadata socket, signing material, application secrets, or production configuration.
- Reject symlinks and path traversal when exporting/importing artifacts; resolve paths and verify they remain beneath the designated workspace.
- Use a unique workspace per attempt. Never reuse a failed or partially cleaned workspace.

### Process and privilege

- Run rootless and unprivileged; no privileged container, host PID/network/IPC namespaces, device passthrough, or added capabilities.
- Do not expose a host shell or arbitrary command endpoint to the model.
- Execute only fixed, typed tool operations with bounded arguments, timeouts, output sizes, and process counts.
- Apply CPU, memory, process-count, disk, and wall-clock limits.
- Terminate the complete process tree on timeout or cancellation.

### Network and credentials

- Default to no network in the execution worker.
- Do not pass API tokens, GitHub credentials, signing keys, payment credentials, production variables, or user secrets into the worker environment.
- If a future dependency-fetching phase is approved, it must use a separate, narrowly allowlisted, logged fetch service and immutable dependency lockfiles; it must not silently enable general egress.
- Provider API credentials, if later selected, remain in the orchestrator/provider adapter and never enter the code-execution worker.

### Lifecycle and evidence

- Create a fresh worker for each attempt from a pinned, reviewed runtime image digest.
- Record image digest, policy version, task ID, attempt ID, base SHA, workspace identity, resource limits, timestamps, and cleanup outcome.
- On success, failure, timeout, cancellation, or host error, terminate the worker and remove its scratch workspace.
- A cleanup failure is a hard failure; do not reuse the workspace or mark the attempt review-ready.
- Export only a patch artifact and bounded diagnostics. The worker cannot commit, push, open/merge PRs, release, deploy, or dispatch production workflows.

## 3. Patch handoff sequence

1. Orchestrator validates the task envelope and pins branch/base/context fingerprints.
2. Worker creates a fresh, restricted workspace from the pinned source snapshot.
3. Agent tools can edit only within that workspace; tool operations are typed and allowlisted.
4. Worker exports a patch and a manifest of changed paths; it does not apply the patch to the task branch.
5. Orchestrator validates the structured result, exact patch digest/size, diff syntax, protected paths, scope, and changed-path agreement.
6. A separately controlled application step may later apply the patch to a dedicated task branch only after all gates pass. That application step is not part of this contract.
7. Fixed verification profiles run outside the untrusted agent process, with restricted environment and stable-source fingerprints.
8. Human reviews the full diff and evidence. Merge/release/deploy remains separately approval-gated.

## 4. Mandatory adversarial acceptance tests

A runtime implementation must prove, not merely claim, that:

- Worker cannot read a host sentinel file outside its mounts.
- Worker cannot read host home, SSH material, Git credentials, signing files, or injected secret sentinels.
- Worker cannot access container/runtime sockets or host devices.
- Network egress and DNS fail from inside the worker.
- Writes to the source mount fail; writes inside the attempt workspace succeed.
- Traversal, absolute paths, symlink escapes, hardlink escapes, and archive path tricks are rejected.
- Resource limits and wall-clock timeout terminate child processes and descendants.
- Cancellation and every failure path trigger cleanup; cleanup failure blocks the attempt.
- A second attempt receives a different workspace and cannot observe the first attempt's residue.
- Worker cannot mutate the pinned base snapshot or task record outside its designated output channel.
- Exported patch is independently revalidated; worker claims are never treated as test evidence.

Tests must run in the actual selected runtime on the supported CI host. Unit tests of a policy object alone do not establish isolation.

## 5. Runtime selection gate

The non-production PR validation workflow now runs `tools/task_orchestrator/runtime_probe.py`. This is deliberately a read-only inventory: it reports discoverable runtime tools, selected namespace/cgroup/seccomp metadata, user-namespace settings, and whether the conventional Docker socket path exists. It does not invoke Docker, Podman, bubblewrap, `unshare`, or any other runtime; it does not attempt privileged operations or network tests.

Treat the output as reconnaissance only. Tool presence, visible namespaces, a non-root UID, or cgroup files do not prove a secure worker. In particular, a Docker socket is a high-privilege host control surface and must never be mounted into an untrusted agent worker.


Do not select Docker, Podman, bubblewrap, a hosted runner, or another mechanism by convenience alone. Before implementation, compare availability on the target CI environment, rootless operation, network isolation, filesystem mount controls, process-tree termination, resource limits, image pinning, and cleanup observability.

If the CI host cannot provide the required properties, stop and report the limitation. Do not silently downgrade to a temporary directory or ordinary Git worktree and call it a sandbox.

## 6. Explicit non-goals

This phase does not connect a model provider, fetch dependencies, execute agent code, apply patches, change application source, or grant repository/production write permissions. It does not authorize merging PR #20 or changing `main`.
