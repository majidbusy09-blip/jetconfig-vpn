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

