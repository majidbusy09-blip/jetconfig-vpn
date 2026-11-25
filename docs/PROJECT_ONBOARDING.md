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


## 7. Verified حسابگر من discovery — 2026-11-25

The owner supplied the exact repository URL and the live GitHub identity was independently fetched:

- Repository: `majidbusy09-blip/hesabgar_man`
- URL: `https://github.com/majidbusy09-blip/hesabgar_man`
- Immutable repository ID: `1423683236`
- Default branch: `main`
- Inspected source baseline: `a07992d3f4721fe1524bd093502f08171dafc92b`
- Package: `hesabgar_man`; version: `1.0.9+10`
- Project ID approved in Issue #105 task payload: `hesabgar-man`

The repository contains a Flutter/Dart application under `lib/`, tests under `test/`, a `pubspec.yaml`, and an existing release-oriented `.github/workflows/build.yml`. That release workflow is not used for pull-request validation.

A separate target-repository PR adds project memory and a read-only Flutter validation workflow pinned to Flutter 3.27.4. The initial validation attempt passed static analysis but failed tests because the repository's declared Vazirmatn font assets are downloaded only by the existing release workflow and are not committed in the source tree. The PR validation workflow was updated to stage the same pinned font release before tests; the rerun must pass before the Flutter profiles are marked verified.

The source-index implementation has a reusable multi-file Dart analyzer library and a project-bound CLI that accepts an explicit repository root, project manifest, and pinned source revision. Its generated outputs are namespaced by project identity, manifest digest, and source revision rather than being restricted to JET VPN artifact names. The current Dart CLI still enumerates tracked Dart files under `lib/`; this matches حسابگر من's configured source layout but is not yet a manifest-driven multi-language adapter. More importantly, the central task orchestrator can resolve project-scoped artifact paths and consume verified indexes, but automatic runtime generation/retrieval and freshness enforcement are not yet proven end-to-end. Therefore the Hesabgar manifest correctly remains `source_index.strategy=none` until those runtime gates and isolation tests pass.

The inspected baseline has no committed `pubspec.lock`. Dependency resolution therefore remains less reproducible than a lockfile-pinned app build. Do not claim full reproducibility until a reviewed lockfile is committed.

Dry-run onboarding remains read-only and the manifest lifecycle stays `registered`. Missing CI evidence, target PR merge, and source-index policy keep the overall state at `NEEDS_REVIEW`; no activation is authorized.


## 8. Actual حسابگر من dry-run report — 2026-11-25

Pinned target candidate revision: `26feaf761c751cb5991b98fcc81e1086d94bb97c` (the head of target PR #2; not yet merged to `main`).

The five required memory documents are present as tracked regular files at that exact candidate revision. Their Git blob IDs and byte sizes were read from the target repository tree:

| Required document | Git blob | Bytes |
|---|---|---:|
| `AGENTS.md` | `9295b5b5680ff2bd55ee9ab35c0a7d190798aa7e` | 2,523 |
| `docs/PROJECT_CONTEXT.md` | `018781c137816c1610b69aa44a76dbadf12fe7da` | 2,901 |
| `docs/CURRENT_STATUS.md` | `e4d66480e0660c59c67c1258834c1eb36dc15005` | 1,748 |
| `docs/NEXT_STEPS.md` | `315e99144cd64e6cbef6d83d848da82c638a3211` | 1,898 |
| `docs/DEVELOPMENT_LOG.md` | `a8313a17d24879e561f07263354482ee2f9d691c` | 877 |

Total required memory size: 9,947 bytes (limit: 512,000 bytes).

The exact-head target CI run [45562174116](https://github.com/majidbusy09-blip/hesabgar_man/actions/runs/45562174116) passed Flutter analysis and all 74 tests using Flutter 3.27.4 / Dart 3.6.2. It also uploaded the resolved `pubspec.lock` as artifact `hesabgar-pubspec-lock` (artifact ID `14998157558`); the lockfile is not yet committed to the target repository.

The central manifest SHA-256 is `ec6ad4643acfc0d141e0820a2cbfeff671625edad6a94d6fe55dc6b254d944a0`.

### Machine-readable report

```json
{
  "report_schema_version": 1,
  "mode": "dry_run_read_only",
  "project_id_candidate": "hesabgar-man",
  "manifest_sha256": "ec6ad4643acfc0d141e0820a2cbfeff671625edad6a94d6fe55dc6b254d944a0",
  "repository": {
    "provider": "github",
    "repository_id": "1423683236",
    "full_name": "majidbusy09-blip/hesabgar_man",
    "url": "https://github.com/majidbusy09-blip/hesabgar_man",
    "default_branch": "main",
    "base_sha": "26feaf761c751cb5991b98fcc81e1086d94bb97c",
    "identity_verified": true
  },
  "discovery": {
    "project_type": "flutter_android",
    "languages": ["Dart", "YAML"],
    "toolchains": [
      {"id": "flutter", "expected_version": "3.27.4", "observed_version": "3.27.4", "verified": true},
      {"id": "dart", "expected_version": "3.6.2", "observed_version": "3.6.2", "verified": true}
    ],
    "memory": {
      "required_documents_found": [
        "AGENTS.md",
        "docs/PROJECT_CONTEXT.md",
        "docs/CURRENT_STATUS.md",
        "docs/NEXT_STEPS.md",
        "docs/DEVELOPMENT_LOG.md"
      ],
      "missing_documents": [],
      "invalid_documents": [],
      "total_bytes": 9947,
      "max_total_bytes": 512000
    },
    "source_index": {
      "status": "adapter_required",
      "manifest_strategy": "none",
      "reason": "The existing resolved Dart analyzer library is multi-file, but its current CLI root and generated artifact names are JET VPN-specific."
    },
    "verification": {
      "required_profiles": [
        {"profile": "flutter-analysis", "status": "success"},
        {"profile": "flutter-tests", "status": "success"}
      ],
      "available_profiles": [
        "flutter-analysis",
        "flutter-tests",
        "lexical-memory-audit",
        "python-tooling-tests"
      ]
    },
    "protected_paths": [
      "android/key.properties",
      "android/app/key.properties",
      ".github/workflows/build.yml",
      "secrets"
    ]
  },
  "blockers": [],
  "human_decisions": [
    "Merge the separately reviewed target-repository memory/CI PR before registration readiness.",
    "Commit and review pubspec.lock to make Flutter dependency resolution reproducible.",
    "Implement and review a project-neutral Dart source-index adapter before enabling source indexing."
  ],
  "writes_performed": false,
  "overall_readiness": "NEEDS_REVIEW",
  "implementation_eligible": false
}
```

**Readiness:** `NEEDS_REVIEW`. Identity, required memory and fixed Flutter checks are verified at the candidate PR head. The target PR is not merged, the generated lockfile is not committed, and the source-index adapter remains deferred. The manifest stays `registered`; this report does not activate the project or authorize implementation tasks.


## Post-merge reconciliation — 2026-11-25

- Target PR #2 is merged as `177eb1a1f0ae8ae5a77a2c1c136804dff042d5db`. Its exact-head Flutter 3.27.4 / Dart 3.6.2 validation passed static analysis and 74 tests.
- The five required memory documents are on the target default branch. Their blob identities are unchanged from the validated PR head; the refreshed report pins target merge commit above.
- The resolved `pubspec.lock` remains a reviewed CI artifact and is not yet tracked on target `main`; dependency reproducibility remains a review item.
- Project lifecycle remains `registered`, not active. Dart source indexing remains deferred until the project-neutral adapter is implemented.


## Control-plane reconciliation after Phase 2D-2B — 2026-11-25

- Central manifest/readiness PR #112 is merged; target memory/CI PR #2 is merged into `hesabgar_man` as `177eb1a1f0ae8ae5a77a2c1c136804dff042d5db`.
- Phase 2D-2B project-scoped artifact and Dart index tooling is merged in control-plane PR #113. The project-bound CLI has since been executed against the actual Hesabgar checkout in target PR #12 validation.
- Target PR #10 committed the reviewed `pubspec.lock`; its SHA-256 is `5e758df74d809f0b11c56f834364456d16d7d1bf48534312bc08dd84fa542cac`.
- Target PR #12 merged as `9b5b324e197d806afa7365abe360c972dbeaf13a`. Post-merge Project Validation run `45665085754` and APK/AAB build run `45665085751` both succeeded on that exact main SHA.
- The validation run generated the project-bound resolved index and critical-path report, verified source/repository/project bindings and tracked-file fingerprints, and smoke-tested Task Intelligence against the real artifacts.
- The successful CI smoke test proves project-bound generation and consumption in CI. It does not prove that the local/central orchestrator automatically provisions or retrieves fresh artifacts at runtime. The manifest therefore remains `source_index.strategy=none` and lifecycle `registered`.
- Next gates: automatic runtime artifact provisioning/retrieval with freshness enforcement, cross-project isolation tests using at least two different projects/toolchains, and owner-side Android device acceptance. No activation is implied by the CI pass.


## Latest evidence reconciliation — 2026-11-25 (supersedes stale status statements above)

The older dry-run snapshots in Sections 7–8 are historical records and must not be treated as the current state. The verified current target main SHA is `9b5b324e197d806afa7365abe360c972dbeaf13a`. PR #12 and its post-merge CI runs establish that the reusable Dart CLI can generate project-bound artifacts for Hesabgar and that Task Intelligence can consume those artifacts in CI. The unresolved gap is runtime automation: the task orchestrator currently derives namespaced artifact paths and validates the supplied files, but it does not itself guarantee that the matching artifacts have been generated or retrieved before each task. Cross-project isolation and manual device acceptance also remain open. Keep lifecycle `registered` and source-index strategy `none` until these gates are independently verified.
