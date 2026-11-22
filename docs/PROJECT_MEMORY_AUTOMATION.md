# JET VPN — Project Memory Automation

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

## Dart AST navigation layer (proposed in PR #8)

- An isolated Dart tooling package lives under `tools/project_memory/semantic/`; it pins `analyzer: 6.11.0`, commits a package lockfile for reproducible transitive dependencies, and does not modify the application's `pubspec.yaml`.
- It parses `lib/main.dart` into AST declarations and syntactic invocation sites, then emits caller-to-name-candidate edges, source locations, and ambiguous/unresolved counts.
- The project-memory workflow runs focused tests, regenerates the AST index twice to verify deterministic output, and uploads the detailed JSON plus the tooling lockfile as a 30-day artifact.
- The detailed graph is generated in CI rather than committed: it is substantially larger than the lexical index and is reproducible from the tracked source and generator. Re-run the workflow to obtain a fresh artifact for the exact PR/source SHA.

### Semantic precision boundary

This is an AST-derived **syntactic** call-site graph, not resolved analyzer elements. Name-based candidate matching is not proof of semantic binding; methods with the same name in unrelated classes can remain ambiguous. Calls into Flutter/dependencies and dynamic/function-valued calls are often unresolved. It does not prove runtime reachability.

## Analyzer-resolved call graph (experimental follow-up)

- The follow-up branch `tools/dart-semantic-resolution-20261122` adds `resolved_indexer.dart` and `bin/resolve.dart` using `AnalysisContextCollection` and `AnalysisSession.getResolvedUnit`.
- The visitor reads the resolved Element attached to each supported invocation node. Calls are labeled `resolved_element` only when the analyzer provides a target Element; unresolved dynamic/function-valued calls remain unresolved rather than being guessed by name.
- Stable target identifiers are derived from the Element source URI, name, and name offset. The output records caller/target IDs, target source, repository-vs-external classification, source line, analyzer diagnostics, and unresolved counts.
- CI first runs `flutter pub get` at the app root to provide the package configuration needed to resolve Flutter and application imports. It then runs the isolated tooling package with its enforced lockfile, focused resolver tests, and deterministic generation checks.
- The resolved graph remains scoped to `lib/main.dart`; the AST candidate graph remains available for side-by-side comparison. The follow-up PR targets the AST-tooling branch and depends on PR #8; neither PR is merged by this work.

### Semantic precision boundary

An analyzer Element is a statically resolved symbol, not proof of runtime execution. Virtual dispatch can select a runtime override different from the statically referenced declaration; dynamic calls, unresolved imports, reflection, generated code, callbacks, and native behavior may remain unresolved or outside this graph. Analyzer diagnostics must be reported alongside counts; unresolved calls are not automatically defects.

## What the audit guarantees

- The generated index is byte-for-byte reproducible from the checked-out source using the committed generator.
- The recorded `lib/main.dart` Git blob SHA matches the checked-out file.
- The recorded line count, UTF-8 byte count, and Unicode code-point count match the source.
- Relevant pull requests receive a CI result and a machine-readable JSON artifact.

## What it does not guarantee

- It is not a Dart AST or a semantic dependency/call graph.
- Token occurrence counts are not proof of call sites or runtime reachability.
- It does not validate application behavior, VPN connectivity, payment correctness, Android lifecycle behavior, or test coverage.
- It does not inspect backend code outside this repository.

The next maturity step is to compare this lexical index with Dart analyzer data and, only then, add semantic caller/callee relationships.

