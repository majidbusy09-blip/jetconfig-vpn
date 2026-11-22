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
