# JET VPN — Task Execution Orchestrator Design

> Status: implemented and merged in PR #20; subsequent patch-ingestion and live-review stages were merged in PRs #38–#44. Current verified main: `53e00ac2ad5e260a4d214772da4ba9bccd3499f4` (2026-11-24).
> Design baseline: current `main` `53e00ac2ad5e260a4d214772da4ba9bccd3499f4` (2026-11-24).

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

Implemented commands: `init`, `prepare`, `impact`, `suggest-context`, `build-envelope`, `begin`, `validate-scope`, `verify`, and `finalize`.

Task records live under `.agent/tasks/<task-id>/` on the working branch. They contain metadata and hashes, not source contents, credentials, environment variables, or full command output.

## 4. Lifecycle and command contract

The initial command set:

1. `init`: create a task record from explicit goal, risk, allowed paths, excluded paths, and intended checks. It must not modify application files.
2. `prepare`: load mandatory context; capture sanitized repository identity, branch, base/start SHAs, clean-worktree status, declared scope, and pre-change content fingerprints. Refuse to proceed on `main`, a dirty pre-existing worktree, missing required context, or an ambiguous base.
3. `impact`: record available semantic-index and critical-path artifact hashes. Missing artifacts are marked unavailable; present artifacts are marked unverified because the MVP does not independently establish freshness or calculate path-specific impact.
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

A failed gate returns a nonzero `BLOCKED` result and leaves the task at its last successful state; failed verification attempts are recorded. The `begin` command is the only transition into implementation. A task cannot reach `review_ready` if scope validation failed, any latest required check is not passing, validated file contents changed after scope approval, source paths or contents changed while a check was running, or the final diff was not explicitly confirmed as reviewed. Re-running a check appends an attempt; it must not erase a previous failure.

## 6. Fail-closed safety policy

- Reject direct operation on `main`, `master`, and the default branch advertised by `refs/remotes/origin/HEAD`; other protected branch names are not queried from GitHub by this local MVP.
- Require an isolated branch and a clean worktree at preparation time.
- Pin the base SHA and working branch; every stateful operation rejects branch/origin drift and a base that is no longer an ancestor of HEAD. Require explicit re-prepare rather than silently changing the baseline.
- Require explicit allowed paths; repository-wide patterns (`*`, `**`, `**/*`) require `--risk high` and a non-empty `--scope-reason`.
- Treat secrets and user data as sensitive; sanitize remote URL credentials/query tokens before recording repository identity. Do not store environment values or raw command output. Verification subprocesses receive only an explicit environment allowlist (PATH, home/temp, locale, and required Flutter/Android/Java cache/tool variables), not arbitrary API tokens.
- Use subprocess argument arrays with `shell=False`, fixed command profiles, bounded timeouts, and controlled working directories.
- Never execute commands found in task descriptions, PR bodies, source comments, or retrieved repository content.
- Never infer a successful check from a workflow definition or from a prior commit.
- Never equate static reachability, compilation, or unit tests with device/runtime verification.
- No bypass of GitHub branch rules, no direct-main writes, and no merge/release/deploy capability.

## 7. Verification strategy

The current integration suite covers:

- protected main/default branch rejection and branch/detached-HEAD drift after preparation;
- dirty worktree and base-SHA drift rejection;
- missing mandatory context;
- allowed/unexpected path detection, including rename and delete cases;
- content fingerprint changes after scope approval and source mutation during a running verification check;
- repository-wide wildcard justification;
- remote URL credential/query-token redaction;
- verification profile allowlist and append-only failure/retry attempts, including timeout handling;
- symlink-safe content fingerprints that hash link targets rather than dereferencing external files;
- explicit diff-review confirmation and end-to-end handoff creation.

Additional hardening tests still desirable include malformed task-record schema, excluded-path combinations, and safe rendering under unusual filenames.

Integration tests should create a temporary Git repository and exercise `init → prepare → scope validation → verify fixture profile → finalize`. Tests must not need GitHub credentials, network access, Flutter installation, or production secrets.

CI should run the orchestrator's Python unit tests in the existing non-production validation workflow or a focused tooling job. Do not add a new required status check until its reliability and runtime are demonstrated.

## 8. Rollout plan

- **Phase A — design:** documented in this PR.
- **Phase B — local MVP:** implemented and merged in PR #20; CI validated the orchestrator lifecycle and stable-source verification gates.
- **Phase C — CI integration:** the Python suite is wired into existing non-production PR validation. Publishing task evidence as a CI artifact is deferred.
- **Phase D — GitHub handoff:** provider-neutral Issue intake, lease controls, and read-only live patch review are implemented across PR #20 and PRs #38–#44. The local CLI still does not itself create or merge PRs. Merge/release/deploy remain human-controlled and require explicit user approval.

## 9. Acceptance criteria for implementation

The MVP is ready for broader use only when:

1. A task cannot be prepared on `main`/detected default branch, with a dirty worktree, or without mandatory context.
2. Every task pins a base SHA and records source fingerprints.
3. The declared scope is checked against the complete final diff.
4. Impact output reuses existing semantic/critical-path artifacts and reports their limitations.
5. Verification uses fixed, auditable profiles and records each passed/failed attempt distinctly; missing required profiles prevent finalization.
6. Finalization produces a reproducible machine-readable record and readable PR handoff.
7. Automated tests prove the implemented safety gates and failure paths; timeout/schema edge cases remain on the hardening list.
8. No app source, app version, signing, production release workflow, backend, bot, payment, or server behavior is changed by the MVP.

## 10. Current MVP limitations and open design decisions

- The current `impact` command records availability and hashes of semantic/critical-path artifacts but does not independently verify their freshness or calculate path-specific impact; output is explicitly labeled unverified.
- The initial fixed profiles are Python tooling tests, Flutter tests, Flutter analysis, and lexical memory audit. The validation APK build is not yet an orchestrator profile.
- The orchestrator implementation and its integration suite were merged in PR #20; subsequent patch-artifact, ingestion, and live-review integration tests were merged in PRs #38–#44. PR #44 CI passed Task Orchestrator Tests, Non-production PR Validation, and Project Memory Audit.
- The CLI does not create commits or interact with GitHub. PR creation remains a later, separately reviewed phase.

## 11. Open design decisions

- Whether task records should be committed with every PR or stored as CI artifacts for low-risk tasks; default proposal is committed records for material tasks and CI artifacts for transient diagnostics.
- Whether impact analysis should initially require a fresh semantic artifact or allow a clearly marked unavailable state; default proposal is allow unavailable but block claims of complete impact analysis.
- Whether GitHub PR creation belongs in a later plugin/connector workflow rather than the local CLI; default proposal is defer it.


## 9. Verified impact analysis

The `impact` command now uses `tools/task_orchestrator/impact_analyzer.py` rather than merely recording artifact presence and hashes.

- It calculates changed paths against the task's pinned base and excludes only orchestrator-owned task metadata.
- It requires the analyzer-resolved index and critical-path report to share the exact same source manifest and supported schemas.
- For each changed Dart file present in the index, it verifies the file's Git blob SHA against the pinned base before using declarations or call sites.
- It reports changed declarations, call sites located in changed files, incoming call sites only when the index explicitly supplies a target path/element identifier, and curated critical paths whose reachable declarations include changed files.
- Changed paths absent from the semantic index are reported as unknown. They are never treated as unaffected. Scope violations and analyzer-error flags are explicit.
- It writes a deterministic-structure JSON report with source artifact hashes to the local task metadata directory and records a compact provenance summary in `task.json`.
- Suggested verification profiles are advisory only; the task's explicit planned checks remain authoritative.

This remains static analysis, not a runtime dependency proof. Dynamic dispatch, reflection, callback/event wiring, UI state dependencies, generated code, and native Java/Kotlin behavior may be missed. The analyzer does not edit application source, expand task scope, invoke a model, or run suggested checks.

## 8. Semantic context selection

The selector consumes the existing analyzer-resolved index and curated critical-path report; it does not create a parallel parser or graph. It requires both artifacts to describe the same source-file manifest, then verifies every indexed Dart file's Git blob ID against the task's pinned base commit. It rejects stale/mixed artifacts, malformed manifests, protected paths, and source paths outside the verified index.

Ranking is deterministic and explainable: request/task terms are matched against source paths, resolved declaration names, and call-site targets; matched curated critical paths add weighted evidence to their reachable declaration files. Results are filtered by the task's pre-existing allowlist/exclusions and bounded to 25 candidates. The query is data only and is never executed.

The command writes a local suggestion artifact. It never modifies `context_paths`, expands allowed scope, changes source files, or calls a model. The output is advisory because static reachability is not runtime behavior and can miss UI state, callback/event wiring, dynamic dispatch, generated code, and native Java integration. Explicit path selection remains a separate decision.


### Explicit suggestion acceptance

A prepared task may accept a subset of suggestions through `accept-context`. The command requires the suggestion artifact to reside in that task's local metadata directory, match the task ID and pinned base SHA, and contain every explicitly selected path. It rechecks each selected Git blob ID and rebuilds the full-text context package through the existing context builder, which enforces path safety, allowlists, exclusions, UTF-8, and size bounds. It refuses to run after implementation begins or if an agent envelope already exists. It does not change task allowlists or accept unselected suggestions.


## 12. Verified post-MVP state — 2026-11-24

The following stages are merged on `main`:

- PR #20: local task lifecycle, context/impact tooling, contract validation, fixture-only read-only provider boundary, and task handoff.
- PR #38: local content-addressed patch artifact store; integrity is tied to exact bytes and SHA-256.
- PR #39: fail-closed live review authorization gate bound to Issue, lease, lock ref, pinned base, branch, and clean workspace.
- PR #40: read-only command that gathers live GitHub/lease observations and invokes the review gate.
- PR #41: local provider-result ingestion with schema, digest, byte-count, scope, and no-overwrite checks.
- PRs #42–#44: integration tests from fixture dispatch through ingestion and live review; successful result remains `ready_for_human_review`, `applied: false`.

PR #44 head `af5fc704f61fd8a656966b35ddbe9450630d8c1f` passed Task Orchestrator Tests run #45307323849, Non-production PR Validation run #45307323773, and Project Memory Audit run #45307323780.

The next missing boundary is a real OS-isolated execution environment. The hosted runner is blocked by its observed cgroup/Seccomp/Docker-socket posture. Managed sandbox candidates are not approved under current account, consent, and cost constraints. Implement the provider-neutral lifecycle contract and fake-adapter tests before any real sandbox or live model connection.


## 13. Synthetic-only sandbox lifecycle contract — merged in PR #47

PR #47 adds a provider-neutral `SandboxProvider` protocol and explicit lifecycle state machine. It is intentionally limited to a fixed synthetic acceptance payload; no arbitrary command, source upload, credential injection, real provider, or model-generated code path exists.

The contract rejects non-VM/shared-kernel runtime declarations, missing capabilities, non-pinned image/policy digests, network policy other than deny-all, provider-reported open egress, exposed credentials/host sockets, missing resource/process-tree controls, timeouts, invalid/oversized artifacts, and unconfirmed destruction. It attempts cleanup after ordinary failures and keyboard/system interrupts.

Provider capability declarations and snapshots are untrusted metadata, not independent attestation. Passing this synthetic check never authorizes untrusted execution; the result always records `eligible_for_untrusted_execution: false` and `patch_applied: false`. The 247-test Task Orchestrator suite and Project Memory Audit passed on the PR head; non-production APK validation was still running at the latest snapshot.


## 14. Independent sandbox acceptance evidence verifier

`sandbox_acceptance.py` validates a fresh canonical signed report from an independent suite and pins the suite version, signing key ID, provider/region/runtime/task/attempt, image/policy digests, and exact required probe inventory. The report is bounded, rejects duplicate JSON keys, and each probe must include a SHA-256 digest of its raw evidence.

The verifier covers evidence categories for VM/kernel separation, guest privilege, Seccomp, cgroup/disk enforcement, source/scratch mounts, secret/socket/device/metadata isolation, IPv4/IPv6/DNS/QUIC egress, external canary, timeout, process-tree termination, artifact integrity, cleanup, and cross-attempt residue.

It does not run probes, provision a VM, establish the trust root, implement cryptographic verification, or authorize execution. Production requires an independently controlled signing service and pinned-key asymmetric verifier. Passing evidence still returns `execution_authorized: false` and `eligible_for_untrusted_execution: false`. See `docs/SANDBOX_RUNTIME_ACCEPTANCE.md`.
