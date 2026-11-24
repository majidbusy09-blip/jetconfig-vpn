# JET AI — Safe Project Onboarding

**Status:** Proposed read-only onboarding procedure  
**Parent architecture:** Issue #95  
**Design phase:** Issue #96

## 1. Purpose and safety invariant

Onboarding discovers whether a GitHub repository can safely become a JET AI-managed project. The initial operation is strictly read-only. It must not create branches, issues, files, tags, releases, deployments, secrets, credentials, installations, provider accounts, or external spending.

A dry run produces a readiness report and explicit blockers. It does not register the project or authorize implementation. Registration is a separate reviewed control-plane operation after the owner confirms the repository identity and configuration.

## 2. Required input

The requester must supply the exact canonical GitHub repository URL. A project name or an approximate repository name is not sufficient.

The onboarding operator must resolve and record:

- exact HTTPS repository URL;
- live GitHub immutable numeric repository ID;
- canonical owner/name;
- actual default branch;
- repository visibility and read permissions available to the connected agent;
- intended stable JET AI project ID, confirmed by the project owner;
- intended project display name and project type.

Do not guess that «حسابگر من» is in a particular repository. Its exact URL has not yet been supplied. Do not register or modify that project until its repository has been independently inspected.

## 3. Dry-run procedure

### Step 1 — Verify repository identity

Using read-only GitHub repository metadata:

1. Fetch the repository from the exact supplied URL.
2. Confirm the returned numeric repository ID.
3. Confirm the canonical full name and HTTPS URL.
4. Confirm the actual default branch exists and resolve its current commit SHA.
5. Check whether the repository is already registered by either project ID or numeric repository ID.
6. Reject redirects, ambiguous identity, repository mismatch, inaccessible metadata, or duplicate bindings.

A repository rename is not a new project. It requires an explicit migration of the existing repository binding. A new numeric repository ID is a different repository.

### Step 2 — Inventory technology and source layout

Read repository metadata and bounded, relevant tracked files without running repository code.

Inspect relevant indicators such as:

- Flutter/Dart: pubspec.yaml, pubspec.lock, analysis_options.yaml, lib/, test/;
- Python: pyproject.toml, requirements files, lockfiles, src/, package and test layout;
- web: package.json, lockfiles, TypeScript configuration, source and test layout;
- backend/service: language manifests, container/build descriptors, service entrypoints, tests and deployment descriptors.

Record toolchain versions only when the repository or a trusted setup source establishes them. Otherwise report them as unknown. Do not install dependencies, execute build scripts, run package lifecycle scripts, or execute arbitrary repository code during dry-run onboarding.

### Step 3 — Inspect project memory

Identify existing agent instructions, project context, current status, next steps, development log, architecture decisions, known issues, API/data/security documentation, and test instructions.

For each candidate memory document, record:

- repository-relative path;
- whether it is a tracked regular file at the pinned source SHA;
- blob SHA-256 or Git object identity;
- size in bytes;
- whether its contents are current, stale, incomplete, or unknown.

Do not create missing memory files during a dry run. Missing mandatory memory is a readiness blocker or a separately scoped documentation task.

### Step 4 — Determine source-index strategy

Select an adapter only when supported by the repository's actual language and layout:

- Dart Analyzer for supported Dart/Flutter projects;
- Python AST or another approved Python index for Python repositories;
- TypeScript/JavaScript index for web projects;
- Markdown/documentation index for documentation-only repositories;
- no source index when source navigation is not required;
- custom adapter only after separate design, review, and test coverage.

The strategy must list tracked input paths, generated artifacts, source fingerprinting, freshness checks, and precision limitations. Never apply a Dart index or Flutter assumptions to a Python-only project.

### Step 5 — Map verification capabilities

For each proposed verification profile, classify it as:

- supported and runnable by an existing fixed runner;
- supported only after an adapter is implemented;
- unavailable;
- blocked by missing toolchain or repository prerequisites.

Separate unit tests, static analysis, type checking, formatting, builds, security checks, memory audits, and runtime/device checks. A skipped or unavailable check is not a pass. Do not execute arbitrary scripts during discovery.

### Step 6 — Identify protected paths and operational constraints

Identify sensitive paths and operations such as signing material, credentials, environment files, production configuration, release workflows, deployment manifests, payment data, user data, and infrastructure state.

Project-specific restrictions may be stricter than global JET AI policy; they may never weaken it. Manifests must not contain secret values, API keys, tokens, passwords, private keys, or other credentials.

### Step 7 — Produce readiness report

The dry-run report must include the exact repository ID, canonical name, default branch, pinned source SHA, proposed project ID, detected technology, proposed adapters, memory status, verification capabilities, protected paths, blockers, unknowns, and a final readiness state.

The report is an audit artifact in the JET AI control plane. It is not written to the target repository.

## 4. Readiness states

Use exactly one overall state:

- **READY_FOR_REGISTRATION** — identity is verified, project ID is approved and unique, manifest is schema-valid, mandatory memory exists, and required adapter/check capabilities are available or explicitly accepted as deferred.
- **NEEDS_REVIEW** — technical discovery is substantially complete but a human decision is required (for example, project type, memory policy, protected paths, or toolchain policy).
- **BLOCKED** — identity is ambiguous, permissions are insufficient, required memory is missing, unsafe paths or constraints are unresolved, or a mandatory capability cannot be verified.

A dry run can never return **ACTIVE** or authorize code changes. Registration and activation are separate state transitions.

## 5. Readiness report format

The report should be machine-readable JSON plus a concise human-readable summary. Suggested shape (illustrative only):

    {
      "report_schema_version": 1,
      "mode": "dry_run_read_only",
      "project_id_candidate": "example-project",
      "repository": {
        "provider": "github",
        "repository_id": "123456789",
        "full_name": "owner/repository",
        "url": "https://github.com/owner/repository",
        "default_branch": "main",
        "base_sha": "<full commit SHA>",
        "identity_verified": true
      },
      "discovery": {
        "project_type": "python",
        "languages": ["Python"],
        "toolchains": [],
        "memory": {
          "required_documents_found": [],
          "missing_documents": [],
          "stale_documents": []
        },
        "source_index": {
          "proposed_strategy": "python_ast",
          "status": "adapter_required"
        },
        "verification": {
          "available": [],
          "adapter_required": [],
          "unavailable": []
        },
        "protected_paths": [],
        "unknowns": []
      },
      "blockers": [],
      "human_decisions": [],
      "writes_performed": false,
      "overall_readiness": "NEEDS_REVIEW"
    }

The placeholder SHA above is explanatory only; an actual report must contain a verified full commit SHA. The report must never contain credentials or private source content.

## 6. JET VPN compatibility fixture

The current JET VPN repository is the first compatibility fixture because it already hosts the existing orchestrator and its project memory.

Observed GitHub metadata for the design baseline:

- Repository: **majidbusy09-blip/jetconfig-vpn**
- Immutable repository ID: **1349356614**
- Default branch: **main**
- Verified main SHA at the start of this design task: **27d591e20864009aae482ceeeb490eb140703316**
- Project type: Flutter Android application, with Dart as the primary application language and additional repository tooling/native Java boundaries.
- Candidate project ID: **jet-vpn-android** (must be explicitly confirmed in the registry operation).

The repository also contains JET AI orchestration tooling. The eventual registry design must distinguish the JET VPN application project from global JET AI control-plane responsibilities even while they share one physical repository. The transitional co-location must not cause every future project to inherit JET VPN's Dart/Flutter requirements.

The tracked project-memory documents currently contain older snapshot references. Therefore, before JET VPN is marked fully ready under the new registry, the project-memory baseline must be refreshed and verified against the actual target SHA. This design task does not modify those files.

## 7. Future onboarding: «حسابگر من»

«حسابگر من» is a separate future project, not an alias or subfolder of JET VPN.

Before onboarding:

1. Obtain the exact GitHub repository URL from the owner.
2. Resolve its immutable repository ID, canonical name, and default branch.
3. Inspect the current source and repository structure at a pinned SHA.
4. Confirm the project ID and intended ownership.
5. Determine Flutter/Dart version constraints from the repository itself; do not infer them from conversational history alone.
6. Define its own required memory manifest, protected paths, verification profiles, and operational constraints.
7. Produce a read-only readiness report.
8. Register only after the report and manifest are reviewed and approved.

No version bump, source write, release, deployment, or app change is part of onboarding. The current app version policy and project-specific constraints remain independent of JET VPN.

## 8. Registration and activation gates

After a dry-run report is reviewed:

1. Owner confirms the project ID, exact repository identity, default branch, project type, and intended scope.
2. Registry validator checks schema, duplicate project IDs, duplicate repository IDs, live GitHub identity, manifest digest, safe paths, and global-policy compatibility.
3. Registry creates a versioned registration record in the central control plane and records an audit event.
4. A project-specific manifest and memory baseline are reviewed; no target-repository write is implicit.
5. Project-specific adapters and fixed verification profiles are tested against safe fixtures.
6. Isolation tests prove no context, memory, workspace, lease, branch, cache, or artifact leakage across at least two projects with different toolchains.
7. The project moves from **registered** to **active** only after explicit approval and all required readiness gates pass.

Pausing a project blocks new implementation tasks but preserves its registry identity and audit history. Retiring a project blocks all new tasks and preserves historical records. Neither operation deletes the source repository or its history.

## 9. Explicit non-goals

Onboarding does not:

- create a GitHub repository or install/configure a GitHub App;
- request new permissions or credentials;
- add API keys, model APIs, paid services, providers, or spending;
- upload private source to a third-party service;
- create branches, commits, PRs, releases, or deployments in the target repository;
- execute arbitrary build scripts or untrusted code;
- enable production or sandbox execution;
- merge code or change production settings.

Any capability outside read-only discovery requires a separately scoped task, valid project identity, active lease, and the relevant explicit approval.
