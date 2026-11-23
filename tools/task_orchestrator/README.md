# JET VPN Task Orchestrator — Local MVP

This standard-library-only Python tool records a task lifecycle and enforces a small set of safety gates. It is an evidence recorder and workflow guard, not an autonomous coding agent.

## Next phase: coding-agent adapter

The provider-neutral design contract is documented in [`docs/CODING_AGENT_ADAPTER_CONTRACT.md`](../../docs/CODING_AGENT_ADAPTER_CONTRACT.md). It specifies the future task/result envelope, isolated patch workflow, permission boundary, and validation gates. It is design only: this MVP does not connect a model provider or execute agent-generated patches.

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

- `init`: requires an initially clean worktree and explicit allowed paths and named checks. Repository-wide patterns (`*`, `**`, `**/*`) require `--risk high` and `--scope-reason`.
- `prepare`: rejects main/master/the detected `origin/HEAD` default branch, detached HEAD, pre-existing changes, changed repository origin, and missing mandatory project context; pins the base SHA and working branch, rejects later branch/origin drift, and fingerprints context/source files.
- `impact`: records hashes and availability of existing semantic/critical-path artifacts. The MVP does not independently prove freshness or complete path-specific impact.
- `begin`: verifies that the pinned base has not moved before entering implementation.
- `validate-scope`: compares committed, staged, unstaged, renamed, deleted, and untracked paths with the declared allow/exclude patterns.
- `verify`: runs only fixed profiles declared at init; no shell command can be supplied by task text. The child process receives a restricted environment allowlist so arbitrary local API tokens are not forwarded. It fingerprints the changed source paths immediately before and after each check; if the path set or content changes while the check is running, that attempt is marked failed and cannot satisfy finalization.
- `finalize`: requires passing scope validation, latest attempt for every planned check must be passing (an earlier pass cannot override a later failure), and explicit human confirmation that the complete diff was reviewed. It writes a Markdown handoff.

Task records and handoffs are stored under `.agent/tasks/<task-id>/`. They contain hashes and check metadata, not environment variables, credentials, or raw command output.

The integration suite uses temporary Git repositories and covers lifecycle, scope, branch/base pinning, rename/delete handling, symlink safety, timeouts, source mutation during verification, stale results, and retry ordering. A later failed attempt blocks finalization even if an earlier attempt passed.

## Fixed verification profiles

- `python-tooling-tests`
- `flutter-tests`
- `flutter-analysis`
- `lexical-memory-audit`

Profiles use fixed argument vectors, bounded timeouts, `shell=False`, and a restricted environment allowlist. A missing executable, OS execution error, timeout, or source mutation during a check is recorded as failure. Repeated attempts append to the record; an earlier failure is not erased.

## Explicit non-goals

This MVP cannot create commits, push branches, call GitHub write APIs, open or merge PRs, create tags, publish releases, deploy, or dispatch the production workflow. It does not infer runtime/device success from static analysis, tests, or builds. Human review and explicit user approval remain mandatory for merge/release/deployment.
