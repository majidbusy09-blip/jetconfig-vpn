# JET VPN — Project Memory Automation

> Current main snapshot: `4fc59de5a8d6ef9323de3b48896f78f3c426732d` (PR #47 and PR #48 merged, verified 2026-11-24). The application source fingerprint remains unchanged by PR #20, PRs #38–#44, PR #46, PR #47, and PR #48.

## Purpose

Keep the agent's source navigation index and its documented source fingerprint synchronized with the actual repository. The audit is intended to catch stale project memory before an agent relies on it.

## Components

- `tools/project_memory/index_dart.py`: deterministic, standard-library-only lexical index generator and verifier.
- `docs/generated/jet_vpn_code_index.json`: committed index of import/export/part directives and declaration-like symbols in `lib/main.dart`.
- `.github/workflows/project-memory-audit.yml`: runs the verification on relevant pull requests and uploads the JSON index as a 30-day artifact.
- `docs/CURRENT_STATUS.md`: records the verified source blob SHA and exact source size metrics.

## Local workflow

After changing `lib/main.dart`:

```bash
python tools/project_memory/index_dart.py --write
python tools/project_memory/index_dart.py --check --check-status
```

Commit the regenerated JSON and updated `CURRENT_STATUS.md` in the same pull request as the source change.

## Dart AST navigation layer (merged in PR #16)

- An isolated Dart tooling package lives under `tools/project_memory/semantic/`; it pins `analyzer: 6.11.0`, commits a package lockfile for reproducible transitive dependencies, and does not modify the application's `pubspec.yaml`.
- It parses `lib/main.dart` into AST declarations and syntactic invocation sites, then emits caller-to-name-candidate edges, source locations, and ambiguous/unresolved counts. This candidate index remains a single-file comparison aid.
- The project-memory workflow runs focused tests, regenerates the AST index twice to verify deterministic output, and uploads the detailed JSON plus the tooling lockfile as a 30-day artifact. Its required PR check now runs for every pull request targeting main (not only selected paths), preventing a required status from remaining pending when a PR changes validation tooling. The recovery regression branch also runs the application package's `flutter test` suite after root dependency resolution.
- The detailed graph is generated in CI rather than committed: it is substantially larger than the lexical index and is reproducible from the tracked source and generator. Re-run the workflow to obtain a fresh artifact for the exact PR/source SHA.

### Semantic precision boundary

This is an AST-derived **syntactic** call-site graph, not resolved analyzer elements. Name-based candidate matching is not proof of semantic binding; methods with the same name in unrelated classes can remain ambiguous. Calls into Flutter/dependencies and dynamic/function-valued calls are often unresolved. It does not prove runtime reachability.

## Analyzer-resolved call graph (merged tooling; static-analysis boundary)

- The merged semantic tooling includes `resolved_indexer.dart` and `bin/resolve.dart`, using `AnalysisContextCollection` and `AnalysisSession.getResolvedUnit`.
- The visitor reads the resolved Element attached to each supported invocation node. Calls are labeled `resolved_element` only when the analyzer provides a target Element; unresolved dynamic/function-valued calls remain unresolved rather than being guessed by name.
- Stable target identifiers are derived from the Element source URI, name, and name offset. The output records caller/target IDs, target source, repository-vs-external classification, source line, analyzer diagnostics, and unresolved counts.
- CI first runs `flutter pub get` at the app root to provide the package configuration needed to resolve Flutter and application imports. It then runs the isolated tooling package with its enforced lockfile, focused resolver tests, and deterministic generation checks.
- The resolved index discovers every tracked `lib/**/*.dart` file with `git ls-files`, resolves each unit in the application package context, and records per-file blob fingerprints, diagnostics, declarations, and call sites. Cross-file internal calls are linked by analyzer Element IDs. The AST candidate graph remains a single-file comparison aid.
- `docs/critical_paths.json` defines curated entrypoints for VPN connection/recovery, app lifecycle, purchase/payment, and profile/account workflows. `bin/critical_paths.dart` traverses only resolved internal edges from those anchors and emits a traceable report with source paths/lines, unresolved calls, external calls, and missing/ambiguous anchors.
- The connection/recovery report also lists the repository's Java patch files and relevant symbols as explicit native integration boundaries. Those Java sources are referenced, not analyzed by the Dart analyzer.
- The AST indexer, analyzer-resolved multi-file index, and critical-path tooling were consolidated into main by PR #16. PR #17 then added the push-to-main audit trigger.

### Semantic precision boundary

An analyzer Element is a statically resolved symbol, not proof of runtime execution. Virtual dispatch can select a runtime override different from the statically referenced declaration; dynamic calls, unresolved imports, reflection, generated code, callbacks, and native behavior may remain unresolved or outside this graph. Analyzer diagnostics must be reported alongside counts; unresolved calls are not automatically defects.

## Main-branch automation

- PR #17 added a `push` trigger for `main` when relevant application, test, dependency, documentation, project-memory tooling, or audit-workflow paths change.
- The push-triggered run [#45029689706](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45029689706) completed successfully on main commit `eae477a89816a5cfd475c596e166d5cb2575884a`. After PR #19, the final-head audit [#45065541236](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541236) also passed; the paired non-production validation run [#45065541255](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541255) passed.
- The required ruleset status-check context is `Verify generated code index and memory freshness`. This is the workflow job name, not the workflow display title. The pull_request trigger intentionally has no path filter because a path-filtered required check can remain pending for otherwise valid PRs.

## What the audit guarantees

- The lexical index is byte-for-byte reproducible from `lib/main.dart` using the committed generator.
- The resolved index fingerprints every tracked Dart file under `lib/` with its Git blob SHA, line count, and UTF-8 byte count.
- The critical-path report is reproducible from the resolved index plus the curated `docs/critical_paths.json` manifest.
- CI regenerates the AST, resolved index, and critical-path report twice and compares the outputs byte-for-byte.
- Relevant pull requests receive a CI result and a machine-readable JSON artifact.

## What it does not guarantee

- It is not a Dart AST or a semantic dependency/call graph.
- Token occurrence counts are not proof of call sites or runtime reachability.
- It does not validate application behavior, VPN connectivity, payment correctness, Android lifecycle behavior, or test coverage.
- It does not inspect backend code outside this repository.

The application regression suite, static semantic tooling, and local task-execution orchestrator are now present. PR #20 merged the orchestrator, contract validation, context selection, and fixture-only read-only adapter. PRs #38–#44 added the content-addressed patch, ingestion, live review gate, and end-to-end review-only tests. The next maturity step is a provider-neutral sandbox lifecycle contract and fake-adapter failure tests; no untrusted code execution is enabled. Cross-language/runtime evidence for the native VPN boundary remains a separate future improvement.



## Sandbox acceptance evidence verifier

The independent report verifier and adversarial tests are part of the orchestrator tooling. This is not a source-index input and does not alter the application source fingerprint. The test suite runs through the existing Task Orchestrator workflow.


## Project-scoped source-index provenance and context selection

The `project-memory-audit.yml` workflow first runs `tools.task_orchestrator.workflow_artifact_names`. It matches the live immutable GitHub repository ID/name to exactly one checked-in project manifest, reads the manifest from its canonical `docs/projects/<project_id>/manifest.json` location without following a symlink or accepting duplicate JSON keys, validates the manifest, and requires the checked-out `git rev-parse HEAD` to equal `github.sha`. No matching manifest selects only the historical v1 compatibility paths/names; an invalid, duplicate, retired, or mismatched manifest fails closed.

In project mode the workflow passes that exact manifest and `github.sha` to **both** `bin/resolve.dart` and `bin/critical_paths.dart`. Both generators independently bind output JSON to the project identity, canonical manifest digest, and exact source revision; the critical-path generator also verifies it read the matching resolved index. Their files are written at the two paths emitted by the shared helper under `docs/generated/projects/<project_id>/<repository_id>/<manifest_sha256>/<source_revision>/indexes/`. Deterministic regeneration repeats the same arguments and byte-compares those exact paths. Project-mode upload contains this resolved-index/report pair; v1 continues using its fixed compatibility paths. The project-bound artifact name is generated from the same identity tuple, but **an artifact name by itself is not evidence of provenance**: consumers must parse and validate the JSON content.

`tools.task_orchestrator.context_selector.select_context` checks the provenance of each JSON independently against `task_record.github_project_binding` and `repository.base_sha`, including project ID, immutable repository ID, manifest SHA-256, and source revision; it also requires the two artifact bindings/revisions to agree. Legacy tasks reject artifacts carrying project-binding or source-revision fields. In either mode, the selector still requires the two exact source-file manifests to match, verifies every Git blob SHA from the pinned tree, limits candidate files to safe tracked `lib/**/*.dart`, and applies explicit allowed/excluded task scope before ranking. The suggestion JSON records the verified artifact mode, binding/revision (or explicit legacy nulls), and the SHA-256 of both input artifacts.

Suggestions remain advisory and do not change task context. `accept-context` requires the suggestion schema and provenance to match the task, requires the user-selected paths to exist in that suggestion, rechecks each file's Git blob SHA at the pinned base, and passes paths through the existing context builder/scope checks. The accepted `context_selection` audit stores the suggestion artifact hash, selected paths, and verified source-artifact provenance. This does not retrieve artifacts automatically, connect to a live handoff, invoke a model, or transfer source to an external service; retrieval remains a separately gated workflow dependent on the exact approved #110 inputs.

Calling either Dart CLI without project options retains the genuine legacy v1 output paths and does not fabricate project provenance. The legacy selector path still verifies source blob fingerprints against the task's pinned base and labels its provenance `legacy_blob_only`, with no project source revision claim.

The fixture-only dispatch audit writer continues to use its existing v2 audit namespace and rejects output overrides that escape it. The v1 command continues to require and honor its explicit output path.
