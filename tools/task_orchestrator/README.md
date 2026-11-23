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
  --context "lib/features.dart" \
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
- `prepare`: rejects main/master/the detected `origin/HEAD` default branch, detached HEAD, pre-existing changes, and changed repository origin; pins the base SHA and working branch, then builds context from that exact Git revision. Required project documents are automatic; source files are explicitly selected with repeatable `--context REPO_PATH` options at `init`. Each selected source file must match the task allowlist and avoid exclusions.
- `impact`: records hashes and availability of existing semantic/critical-path artifacts. The MVP does not independently prove freshness or complete path-specific impact.
- `begin`: verifies that the pinned base has not moved before entering implementation.
- `validate-scope`: compares committed, staged, unstaged, renamed, deleted, and untracked paths with the declared allow/exclude patterns.
- `verify`: runs only fixed profiles declared at init; no shell command can be supplied by task text. The child process receives a restricted environment allowlist so arbitrary local API tokens are not forwarded. It fingerprints the changed source paths immediately before and after each check; if the path set or content changes while the check is running, that attempt is marked failed and cannot satisfy finalization.
- `finalize`: requires passing scope validation, latest attempt for every planned check must be passing (an earlier pass cannot override a later failure), and explicit human confirmation that the complete diff was reviewed. It writes a Markdown handoff.

Task records and handoffs are stored under `.agent/tasks/<task-id>/`. The task record includes a bounded full-text context package (256 KB per file, 512 KB combined), package SHA-256, and pinned source revision. It contains no environment variables, credentials, or raw command output.

## Deterministic Context Builder

- `context_builder.py` reads required project documents and explicitly selected source files from the pinned Git commit, never from mutable working-tree contents.
- Source selection is explicit via repeatable `--context`; this avoids copying the entire repository into the agent context by default.
- Rejects path traversal, protected paths, missing or untracked paths, symlinks, submodules, non-UTF-8/binary content, and size overflow. It never silently truncates.
- Produces reproducible full-text documents with per-file SHA-256 and a canonical package SHA-256. The package is persisted in the task record for future agent-envelope construction.
- Repository text is untrusted data and cannot override the agent's safety or permission boundaries.
- Local-only and provider-neutral: no source upload, model call, API key, or sandbox is involved.


The integration suite uses temporary Git repositories and covers lifecycle, scope, branch/base pinning, rename/delete handling, symlink safety, timeouts, source mutation during verification, stale results, and retry ordering. A later failed attempt blocks finalization even if an earlier attempt passed.

## Coding-agent contract validation (provider-neutral)

- `agent_contract.py` validates task envelopes and structured results against contract version `1.1`; it is data validation only and does not connect a provider, execute commands, fetch artifacts, or apply patches.
- Rejects unknown/missing fields, duplicate JSON keys, malformed/oversized JSON, invalid enums/types, unsafe or protected paths, out-of-scope/excluded changes, unknown verification profiles, arbitrary URL/shell patch references, invalid budgets/usage, and stale or mismatched context fingerprints, missing context text, content/hash mismatches, and per-file/total context-size limits.
- Patch references are opaque `artifact:sha256:<64-hex>` identifiers only. The artifact itself still requires independent patch parsing and acceptance gates before any future application.
- Agent status and assertions are not verification evidence. Non-completed statuses cannot carry a patch; only the orchestrator may later record actual check outcomes or advance task state.
- Run the fixture suite with `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py'`.

## Read-only adapter prototype

- `readonly_adapter.py` defines a minimal provider protocol: a provider receives only a deeply immutable, validated task envelope and returns structured data that is validated against the same task contract.
- Project and source context are passed as bounded full-text documents, not just hashes; each document's SHA-256 is checked before the provider is called. The result echoes only path/hash fingerprints.
- A deterministic fixture provider supports local tests. No model SDK, API key, network client, shell, Git, filesystem handle, patch fetcher, or patch applier is included.
- The boundary rejects invalid envelopes before calling the provider and rejects malformed or contract-invalid provider output. Provider exception text is not copied into diagnostics.
- Important limitation: this Python interface is not an OS-level sandbox. It only constrains the capabilities passed through this interface; any real provider implementation must be separately trusted, permission-limited, and reviewed. No live provider is connected.
- Run all orchestrator tests with `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py'`.

## Fixed verification profiles

- `python-tooling-tests`
- `flutter-tests`
- `flutter-analysis`
- `lexical-memory-audit`

Profiles use fixed argument vectors, bounded timeouts, `shell=False`, and a restricted environment allowlist. A missing executable, OS execution error, timeout, or source mutation during a check is recorded as failure. Repeated attempts append to the record; an earlier failure is not erased.

## Explicit non-goals

This MVP cannot create commits, push branches, call GitHub write APIs, open or merge PRs, create tags, publish releases, deploy, or dispatch the production workflow. It does not infer runtime/device success from static analysis, tests, or builds. Human review and explicit user approval remain mandatory for merge/release/deployment.
