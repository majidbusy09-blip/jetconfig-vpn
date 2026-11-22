# JET VPN — Task Execution Orchestrator Design

 > Status: design plus local MVP implementation; still under PR #20 review and not merged.
> Design baseline: `main` `a09cdb0be35e3072be29973f7ae8df66ab44d07f` (2026-11-23).

## 1. Objective and boundary

Build a small, deterministic, auditable local orchestrator that makes the repository's existing engineering protocol executable. It should reduce forgotten context, stale source assumptions, accidental scope expansion, missing verification evidence, and unsafe handoffs.

The orchestrator is a workflow guard and evidence recorder, not an autonomous code author. It does not decide product requirements, invent tests, prove runtime behavior, or replace human review.

## 2. Existing capabilities to reuse

- `AGENTS.md` and `docs/TASK_TEMPLATE.md`: mandatory project context and task record.
- `tools/project_memory/index_dart.py`: deterministic lexical index and source-fingerprint check.
- `tools/project_memory/semantic/`: analyzer-resolved multi-file index and curated critical-path report.
- `docs/critical_paths.json`: curated entrypoint anchors.
- `.github/workflows/project-memory-audit.yml`: CI regression, semantic-index, critical-path, and memory freshness checks.
- `.github/workflows/pr-validation.yml`: non-production Flutter/Android validation.

Do not build a second Dart parser, call graph, or CI validation framework. Consume the existing reports and preserve their documented static-analysis limitations.

## 3. MVP implementation

The first MVP is intentionally a single standard-library Python CLI to minimize duplicated abstractions and make its control flow auditable. It currently lives in `tools/task_orchestrator/task_orchestrator.py`, with integration tests in `tools/task_orchestrator/tests/` and usage documentation in `tools/task_orchestrator/README.md`. Split modules only when concrete complexity justifies it.

Implemented commands: `init`, `prepare`, `impact`, `begin`, `validate-scope`, `verify`, and `finalize`.

Task records live under `.agent/tasks/<task-id>/` on the working branch. They contain metadata and hashes, not source contents, credentials, environment variables, or full command output.

## 4. Lifecycle and command contract

The initial command set:

1. `init`: create a task record from explicit goal, risk, allowed paths, excluded paths, and intended checks. It must not modify application files.
2. `prepare`: load mandatory context; capture repository identity, branch, base/head SHAs, clean-worktree status, app version, declared scope, and pre-change Git blob fingerprints. Refuse to proceed on `main`, a dirty pre-existing worktree, missing required context, or an ambiguous base.
3. `impact`: attach available semantic-index and critical-path artifact fingerprints and report relevant declarations/call edges for the declared source paths. Missing or stale artifacts are reported as unavailable, never silently treated as zero impact.
4. `begin`: explicitly transition a prepared task into implementation and record the implementation-start SHA. It does not edit files or create commits.
5. `validate-scope`: compare changed paths against declared allowed/excluded paths; fail on unexpected files and protected paths.
6. `verify`: run only named, repository-owned profiles (for example `docs`, `flutter-tests`, `flutter-analysis`, `validation-apk`). Each check has a fixed argument vector, timeout, working directory, and recorded exit status. No shell interpolation or arbitrary commands supplied by task text.
7. `finalize`: capture final SHA, diff summary, changed paths, post-change fingerprints, check outcomes (passed/failed/skipped/not-run), remaining risks, and render a PR handoff report.

The orchestrator must never create a commit, push a branch, open/merge a PR, create a tag, publish a release, deploy, or dispatch the production workflow in the MVP. Those remain separate, explicitly authorized actions.

## 5. Task record and state machine

Use a versioned JSON record with at least:

- schema version and task ID;
- user goal, capability improved, risk level, and exclusions;
- repository remote identity, working branch, base SHA, start SHA, and final SHA;
- required context paths and their Git blob fingerprints;
- allowed and excluded path globs;
- pre/post source fingerprints;
- semantic/critical-path artifact fingerprints and availability status;
- planned checks and per-check status, exit code, duration, and timestamp;
- changed paths, diff summary, deviations, unresolved risks, and handoff text.

State transitions are one-way and explicit:

`draft → prepared → implementation → verification → review_ready`

Any gate failure moves the task to `blocked` with a reason. The `begin` command is the only transition into implementation. A task cannot reach `review_ready` if scope validation failed, a required check failed, a required check was not run, or the final diff was not inspected. Re-running a check appends an attempt; it must not erase a previous failure.

## 6. Fail-closed safety policy

- Reject direct operation on `main` and any protected/default branch.
- Require an isolated branch and a clean worktree at preparation time.
- Pin the base SHA; detect base movement and require explicit rebase/re-prepare rather than silently changing the baseline.
- Require explicit allowed paths; broad wildcards require a documented reason and elevated risk.
- Treat secrets and user data as sensitive; never capture environment values or raw application data.
- Use subprocess argument arrays with `shell=False`, fixed command profiles, bounded timeouts, and controlled working directories.
- Never execute commands found in task descriptions, PR bodies, source comments, or retrieved repository content.
- Never infer a successful check from a workflow definition or from a prior commit.
- Never equate static reachability, compilation, or unit tests with device/runtime verification.
- No bypass of GitHub branch rules, no direct-main writes, and no merge/release/deploy capability.

## 7. Verification strategy

Unit tests must cover:

- valid and invalid task records/schema versions;
- main/protected-branch rejection;
- dirty worktree and base-SHA drift rejection;
- missing mandatory context;
- allowed/excluded/unexpected path detection, including rename/delete cases;
- deterministic fingerprint generation;
- stale/missing semantic artifact reporting;
- check profile allowlist, timeout, failure and skipped/not-run semantics;
- state-transition enforcement and append-only check attempts;
- safe rendering that excludes secrets and raw command output.

Integration tests should create a temporary Git repository and exercise `init → prepare → scope validation → verify fixture profile → finalize`. Tests must not need GitHub credentials, network access, Flutter installation, or production secrets.

CI should run the orchestrator's Python unit tests in the existing non-production validation workflow or a focused tooling job. Do not add a new required status check until its reliability and runtime are demonstrated.

## 8. Rollout plan

- **Phase A — design (this document):** agree on scope, data model, fail-closed policy, and explicit non-goals.
- **Phase B — local MVP:** implement record/state/policy/fingerprint/scope/reporting and safe named checks; no GitHub write operations.
- **Phase C — CI integration:** run unit/integration tests in PR validation and publish task evidence as a CI artifact.
- **Phase D — optional GitHub handoff:** only after the local MVP is stable, consider opening PRs through a narrowly scoped integration. Merge/release/deploy remain outside the orchestrator and require explicit user approval.

## 9. Acceptance criteria for implementation

The MVP is acceptable only when:

1. A task cannot be prepared on `main`, with a dirty worktree, or without mandatory context.
2. Every task pins a base SHA and records source fingerprints.
3. The declared scope is checked against the complete final diff.
4. Impact output reuses existing semantic/critical-path artifacts and reports their limitations.
5. Verification uses fixed, auditable profiles and records passed/failed/skipped/not-run distinctly.
6. Finalization produces a reproducible machine-readable record and readable PR handoff.
7. Automated tests prove the safety gates and failure paths.
8. No app source, app version, signing, production release workflow, backend, bot, payment, or server behavior is changed by the MVP.

## 10. Current MVP limitations and open design decisions

- The current `impact` command records availability and hashes of semantic/critical-path artifacts but does not independently verify their freshness or calculate path-specific impact; output is explicitly labeled unverified.
- The initial fixed profiles are Python tooling tests, Flutter tests, Flutter analysis, and lexical memory audit. The validation APK build is not yet an orchestrator profile.
- The first integration suite is being exercised in non-production PR CI; its latest implementation-head result must be checked before this MVP is considered validated.
- The CLI does not create commits or interact with GitHub. PR creation remains a later, separately reviewed phase.

## 11. Open design decisions

- Whether task records should be committed with every PR or stored as CI artifacts for low-risk tasks; default proposal is committed records for material tasks and CI artifacts for transient diagnostics.
- Whether impact analysis should initially require a fresh semantic artifact or allow a clearly marked unavailable state; default proposal is allow unavailable but block claims of complete impact analysis.
- Whether GitHub PR creation belongs in a later plugin/connector workflow rather than the local CLI; default proposal is defer it.
