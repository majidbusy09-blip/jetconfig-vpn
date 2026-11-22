# JET VPN Task Orchestrator — Local MVP

This standard-library-only Python tool records a task lifecycle and enforces a small set of safety gates. It is an evidence recorder and workflow guard, not an autonomous coding agent.

## Requirements

- Python 3.10 or newer (CI currently uses Python 3.12).
- Git.
- Run commands from inside a clean working tree on a dedicated non-main branch.

## Lifecycle

```sh
python tools/task_orchestrator/task_orchestrator.py init \
  --task-id smart-routing-audit \
  --goal "Trace and verify Smart Routing behavior" \
  --capability "source analysis and verification" \
  --risk medium \
  --allow "lib/**" \
  --allow "test/**" \
  --exclude "lib/generated/**" \
  --check python-tooling-tests \
  --check flutter-analysis \
  --check flutter-tests

python tools/task_orchestrator/task_orchestrator.py prepare --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py impact --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py begin --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py validate-scope --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile python-tooling-tests
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile flutter-analysis
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile flutter-tests
python tools/task_orchestrator/task_orchestrator.py validate-scope --task-id smart-routing-audit
# Review the complete tracked, staged, and untracked diff yourself before confirming:
python tools/task_orchestrator/task_orchestrator.py finalize --task-id smart-routing-audit --reviewed-diff
```

The example is illustrative: choose only checks appropriate to the actual task. A check is not successful until its fixed command has actually run and returned zero.

## Commands

- `init`: requires an initially clean worktree and explicit allowed paths and named checks.
- `prepare`: rejects main/master, detached HEAD, pre-existing changes, and missing mandatory project context; pins the base SHA and fingerprints context/source files.
- `impact`: records hashes and availability of existing semantic/critical-path artifacts. The MVP does not independently prove freshness or complete path-specific impact.
- `begin`: verifies that the pinned base has not moved before entering implementation.
- `validate-scope`: compares committed, staged, unstaged, renamed, deleted, and untracked paths with the declared allow/exclude patterns.
- `verify`: runs only fixed profiles declared at init; no shell command can be supplied by task text.
- `finalize`: requires passing scope validation, latest passing attempt for every planned check, and explicit human confirmation that the complete diff was reviewed. It writes a Markdown handoff.

Task records and handoffs are stored under `.agent/tasks/<task-id>/`. They contain hashes and check metadata, not environment variables, credentials, or raw command output.

## Fixed verification profiles

- `python-tooling-tests`
- `flutter-tests`
- `flutter-analysis`
- `lexical-memory-audit`

Profiles use fixed argument vectors, bounded timeouts, and `shell=False`. A missing executable or timeout is recorded as failure. Repeated attempts append to the record; an earlier failure is not erased.

## Explicit non-goals

This MVP cannot create commits, push branches, call GitHub write APIs, open or merge PRs, create tags, publish releases, deploy, or dispatch the production workflow. It does not infer runtime/device success from static analysis, tests, or builds. Human review and explicit user approval remain mandatory for merge/release/deployment.
