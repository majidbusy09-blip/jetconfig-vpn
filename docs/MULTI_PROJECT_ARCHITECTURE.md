# JET AI Multi-Project Architecture

**Status:** Proposed architecture; documentation phase only  
**Parent:** GitHub Issue #95  
**Design task:** GitHub Issue #96  
**Scope:** Central orchestration of multiple independent GitHub repositories

## 1. Architectural objective

JET AI must operate as a reusable engineering control plane, not as an orchestrator whose assumptions are tied to the JET VPN Flutter application. A project can be a Flutter/Dart mobile app, Python service, web frontend, backend, library, or a future supported type. Registering another repository must be a data/configuration operation; it must not require editing orchestrator source code.

The system has four distinct scopes:

1. **Global JET AI control scope** — safety policy, agent identities, task protocol, lease protocol, approval boundaries, registry validation, audit format, and common orchestration logic.
2. **Project scope** — one immutable project identity bound to one canonical GitHub repository identity, its default branch, project manifest, memory, adapters, and verification capabilities.
3. **Task scope** — one project-bound task, pinned base commit, allowlist, lease, context package, branch, PR, checks, artifacts, and audit trail.
4. **Explicit cross-project scope** — an exceptional task that names every participating project and obtains separate authorization and leases for each. It is never inferred from task prose.

Global policy always takes precedence. A project manifest may add stricter restrictions but cannot weaken global safety, identity, review, or approval requirements.

## 2. Control-plane and repository separation

The long-term control plane owns the project registry and global JET AI policy. Project source repositories remain independently authoritative for their own code, branches, issues, tests, and project memory.

The current `majidbusy09-blip/jetconfig-vpn` repository is a transitional host for both the JET VPN Android client and JET AI tooling. That historical arrangement must not become a permanent architectural assumption. A later extraction of the control plane into a dedicated repository must preserve project IDs and audit history; it must not silently re-key projects.

Recommended logical control-plane records:

- `registry/projects/<project_id>.json` — validated project manifest.
- `registry/index.json` — index mapping immutable project IDs and canonical repository IDs to manifest digests.
- `policy/global.json` — global safety and approval policy, owned separately from project manifests.
- `audit/<project_id>/<task_id>/...` — project-scoped task/audit references.

These are logical locations, not files created by this design-only task. The registry index is authoritative for uniqueness; a manifest copied into a project repository is informational unless its digest is registered centrally.

## 3. Stable project identity and repository binding

Every registered project has an immutable `project_id` matching the schema in `PROJECT_MANIFEST_SCHEMA.json`. It is a stable system identifier, not a display name, repository name, branch name, or owner-controlled free-form alias.

A GitHub repository binding contains:

- GitHub's immutable numeric repository ID;
- canonical `owner/name` full name;
- canonical HTTPS repository URL;
- explicitly configured default branch.

The immutable numeric repository ID is the primary repository identity. The full name and URL are checked against the live GitHub repository object on every onboarding refresh and before consequential operations. A repository rename may update the canonical name only through an explicit, audited registry migration; a different numeric repository ID is a different repository and must be rejected.

Registration must fail closed when:

- the project ID is unknown, malformed, duplicated, or already assigned;
- the numeric repository ID is already bound to another active project;
- the supplied owner/name or URL resolves to a different repository ID;
- the configured default branch does not exist or differs from the explicitly approved setting;
- repository identity cannot be read or verified;
- a manifest contains unsupported fields, unsafe paths, or prohibited credentials.

Never choose a project by searching task text for words such as “VPN” or “calculator”. Every task must explicitly resolve to exactly one registered `project_id`.

## 4. Project manifest and adapters

The JSON Schema in `PROJECT_MANIFEST_SCHEMA.json` defines the versioned manifest contract. The manifest is declarative data; it is not executable configuration and must never contain shell commands, model prompts with authority, API keys, tokens, passwords, signing material, or arbitrary plugin code.

Each project declares:

- project type and language/toolchain inventory;
- required and optional project-memory documents;
- source-index strategy and tracked input/output paths;
- verification profiles and required checks;
- protected paths and project-specific operational constraints.

Adapters are selected by declared capabilities and validated project type, not by a single global language assumption. Examples:

| Project | Source/index adapter | Verification profile examples |
|---|---|---|
| JET VPN Android | Dart Analyzer + explicit Java boundary | Flutter analysis/tests, Python tooling tests, memory audit |
| Python-only service | Python AST or configured Python index | Python unit/type/lint profiles |
| Web frontend | TypeScript/JavaScript module index | Node test/type/lint/build profiles |
| Documentation-only repository | No source index or a Markdown index | Link/schema/documentation checks |

A profile is eligible only when the project manifest declares the capability and the runner supports it. A Python-only project must not run Flutter commands. Missing toolchains or profiles produce a clear blocked result; they must not be silently replaced with unrelated checks. Profile identifiers shown in the manifest examples (such as proposed Python-specific profiles) are design examples, not claims that those runners already exist. The registry must reject an unimplemented required profile or classify it as an explicit onboarding blocker until its adapter is delivered and tested.

## 5. Identity propagation and strict isolation

The following fields are required in every new task envelope and persisted task record:

- `project_id`;
- immutable GitHub `repository_id`;
- canonical `repository_full_name`;
- configured `default_branch`;
- exact `base_sha`;
- manifest schema version and manifest digest.

The same identity tuple must be carried and revalidated in:

- task intake and task records;
- lease records and lock refs;
- context packages and per-document fingerprints;
- local/remote workspaces and branch names;
- pull requests and expected-head checks;
- verification jobs and reports;
- caches, generated indexes, artifacts, and audit events;
- memory reads and memory updates.

Recommended namespaces:

- branch: `agent/<project_id>/<task_id>`;
- lease ref: `agent-locks/<project_id>/<task_id>`;
- task memory/audit: `<project_id>/<task_id>`;
- cache key: hash of project ID + repository ID + base SHA + adapter/profile version + declared inputs;
- artifact key: project ID + task ID + source revision + artifact digest.

Existing branch/ref formats may be accepted during a versioned migration for the legacy JET VPN project only. New projects must use project-qualified namespaces. Do not silently reinterpret a legacy task ID as belonging to a different project.

Isolation requirements:

1. A task for project A can read/write only project A's repository, manifest, memory, workspace, cache namespace, artifacts, and lease.
2. A project ID and repository ID mismatch is a hard failure before source access or writes.
3. Context builders must resolve paths from the selected project's pinned tree only; no fallback to another project's memory or source.
4. Workspaces must be separate disposable roots with no shared writable mounts. Shared immutable tool caches are permitted only when content-addressed and namespaced by project and toolchain.
5. Cache and artifact lookups must validate the complete project/repository identity tuple, not only a task ID or filename.
6. Branch, lock, and task identifiers must be collision-resistant across projects.
7. Cross-project access is denied by default.

A cross-project task must explicitly enumerate all participating project IDs, repository IDs, intended read/write operations, and per-project path scopes. It requires explicit human authorization, a separate pinned base SHA and active lease for each repository, independent verification, and a combined audit record. Failure or expiry in any participant blocks the whole cross-project operation. This exception is not a shortcut for ordinary tasks.

## 6. Independent project memory

Global JET AI policy and architecture decisions belong to the control-plane scope. They must not be copied into every project's memory as if they were application facts.

Each project manifest declares its own canonical memory manifest. A project may require files such as:

- agent instructions;
- project context and current status;
- next steps and development log;
- architecture/API/data/decision records;
- known issues and testing guidance;
- generated source indexes, where appropriate.

The project-memory gate must validate the exact base/head diff and verify that every required canonical path survives as a tracked regular file in the exact target tree. Deleted or renamed-away documents do not satisfy an update requirement. Memory prose remains subject to human review for factual accuracy.

A project's memory cannot be read as a fallback for another project's missing memory. If required project memory is absent, stale, oversized, or inconsistent with the pinned source revision, task preparation must report the blocker rather than silently substitute global or neighboring documents.

## 7. Verification and policy composition

Verification is composed from three layers:

1. **Global mandatory checks** — task identity, scope, lease, base SHA, path safety, memory integrity, artifact provenance, and approval boundaries.
2. **Project-required checks** — the profiles declared by the selected project's manifest.
3. **Task-specific checks** — a bounded subset selected for the task and accepted by the project adapter.

A task cannot remove a global mandatory check. A project cannot declare a check that the runner does not implement. A task cannot add arbitrary shell commands to a verification profile. The orchestrator must report each check as passed, failed, skipped with reason, or not run.

## 8. Task lifecycle

The project-aware lifecycle is:

1. Resolve explicit `project_id` in the registry.
2. Verify the canonical repository identity and manifest digest.
3. Validate task payload, capability, risk, path scope, and project adapter support.
4. Read current project memory and inspect the target default branch.
5. Claim a project-qualified lease that pins the exact base SHA.
6. Build a context package from that project's tree and memory only.
7. Create a project-qualified branch and isolated workspace.
8. Execute only through an explicitly enabled adapter; arbitrary untrusted-code execution remains disabled until the separate sandbox acceptance policy is satisfied.
9. Validate proposed changes against scope and identity.
10. Run global, project, and task verification profiles.
11. Open a Draft PR with exact project identity, base/head, evidence, and task envelope.
12. Obtain an independent review and human approval before merge.
13. Update only that project's durable memory and audit trail.
14. Release the lease and verify release.

GitHub Issue events do not wake a model or create background polling. Agents remain user-activated chat sessions unless a separately authorized dispatch service is implemented.

## 9. Backward-compatible migration

The current JET VPN repository is the compatibility fixture. Migration must be incremental and reversible.

### Phase A — design and inventory
- Document the registry, manifest, identity tuple, isolation model, adapter contract, and threat model.
- Inventory current hard-coded repository names, fixed memory paths, task/envelope versions, lease refs, branch naming, caches, and verification assumptions.
- No source or workflow behavior changes in this phase.

### Phase B — registry and identity primitives
- Introduce a versioned registry loader and strict manifest validator.
- Register the existing JET VPN repository using its verified immutable GitHub repository ID.
- Make all new tasks require explicit project identity.
- Reject unknown/mismatched identity before source reads or writes.

### Phase C — JET VPN compatibility adapter
- Define a JET VPN manifest matching the verified current repository.
- Preserve legacy v1.1/v1.2 envelope parsing only through an explicit legacy adapter bound to this repository identity.
- Add project identity to new envelope versions and test old/new compatibility.
- Preserve existing lease semantics during a versioned namespace migration; never accept a stale lock as a new project lease.

### Phase D — project-aware context, memory, indexes, and checks
- Replace fixed global document lists with per-project memory manifests.
- Add adapter capability negotiation and project-specific source-index/verification strategies.
- Add isolation tests for workspaces, leases, branches, caches, artifacts, and memory.

### Phase E — dry-run onboarding and first additional project
- Implement read-only onboarding and readiness reporting.
- Re-run JET VPN onboarding as the compatibility fixture.
- Inspect an additional repository only after its exact URL is supplied and repository identity is verified. Do not infer the repository for «حسابگر من».

Each phase is independently reviewable and must keep existing JET VPN task behavior working until the migration gate is explicitly closed.

## 10. Threat model and failure-closed rules

Threats include accidental cross-repository writes, malicious or malformed Issue payloads, repository rename/transfer confusion, project-ID collision, stale base or manifest use, cache poisoning, path traversal, memory deletion/rename bypass, lease races, adapter overreach, and unsafe code execution.

Required controls:

- strict schema validation with duplicate-key rejection and unknown-field rejection;
- immutable project ID and repository ID binding;
- live repository identity revalidation;
- exact base SHA and manifest digest pinning;
- path normalization and protected-path enforcement;
- project-qualified lease/branch/cache/artifact namespaces;
- independent lease verification and expected-head compare-and-swap;
- content-addressed artifacts with bounded size and provenance;
- exact-tree memory survival checks;
- no implicit cross-project fallback;
- global approval gates for merge, release, deploy, credentials, spending, and execution authorization.

When identity, permission, branch, manifest, lease, memory, or verification state is ambiguous, stop before writing. Never “repair” identity by guessing.

## 11. Decisions still requiring explicit review

- The final location and ownership model for the central registry (in-repository transitional storage versus a dedicated JET AI control repository).
- Whether the numeric GitHub repository ID and owner/name should be stored together in every envelope or resolved from a signed registry snapshot.
- The exact version at which legacy envelope acceptance is retired.
- Whether a future project may opt into shared immutable build caches and the exact provenance requirements.
- The supported adapter/profile catalogue and its versioning policy.

These decisions must be recorded in the control-plane decision log before implementation. This document is a proposed design, not evidence that any of these mechanisms are already implemented.


## Phase 2D-1 — lease and workspace namespace contract

V2 project tasks derive lock refs and lease-record paths from validated `project_id` and immutable numeric `repository_id`. Lease records carry the complete project identity tuple and pinned base SHA. Handoff creation/acceptance, PR validation, and patch-review authorization must all use the same namespace helper and reject project-binding drift. Workspace identifiers additionally include the manifest digest, task ID, and base SHA. Legacy v1 JET VPN lease refs and paths remain unchanged. Local task records, context packages, patch artifacts, caches, source indexes, and audit paths are deferred to Phase 2D-2.
