# JET VPN — Coding Agent Adapter Contract

> Status: provider-neutral design proposal for the next Orchestrator phase. This document does not implement or connect a model provider.
> Baseline: PR #20 branch after commit `c4acaf8c32a5c70cea2919b9eb5f2c68303b3559`; main remains `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.

## 1. Purpose

Define a narrow contract between the task orchestrator and an external coding agent so that a user can request a bounded feature or bug fix and receive an auditable proposed change.

The adapter is an execution boundary, not a second orchestrator. The orchestrator remains authoritative for repository identity, task state, context loading, branch/base pinning, allowed paths, verification profiles, evidence, and handoff. The model proposes and implements changes inside an isolated workspace; it does not approve its own work.

This advances the collaborator objective by adding a controlled implementation capability while retaining project memory and deterministic safety gates.

## 2. Responsibility split

### Orchestrator owns

- Validate the task request, repository, branch, base SHA, task state, risk, and declared scope.
- Load mandatory project memory and verified source/index artifacts.
- Construct a bounded context package and record its fingerprints.
- Select an explicitly configured agent adapter and model identifier.
- Create and supervise an isolated, disposable implementation workspace.
- Enforce time, token, file-count, patch-size, and tool-call budgets.
- Capture the agent's structured result and proposed patch.
- Reject out-of-scope paths and unsafe patch operations before applying anything to the task branch.
- Run fixed verification profiles only after the implementation workspace is stable.
- Produce evidence and a human-review handoff.

### Coding agent owns

- Interpret the user's goal against the supplied authoritative context.
- Explain assumptions, identify relevant source symbols and likely impact.
- Propose a small implementation plan before editing.
- Modify only files available in its isolated workspace.
- Add or update tests when appropriate.
- Report changed paths, rationale, known limitations, and suggested verification profiles.
- Stop and request clarification when requirements conflict or the task exceeds its approved scope.

### Human owns

- Product decisions and ambiguous requirements.
- Approval of scope expansion or elevated-risk work.
- Review of the complete diff and verification evidence.
- Explicit approval for merge, release, deployment, production workflow dispatch, or other consequential external action.

## 3. Input contract

An adapter receives one immutable task envelope. Required fields:

- `contract_version`: versioned schema identifier.
- `task_id`: orchestrator task identifier.
- `goal`: user's requested outcome, preserved without reinterpretation.
- `capability`: implementation, bug_fix, refactor, documentation, or investigation.
- `risk`: low, medium, or high.
- `repository`: canonical repository identity, branch, pinned base SHA, and workspace root identifier.
- `scope`: explicit allowed and excluded path patterns plus any approved scope reason.
- `project_context`: bounded full-text instruction/document content, path, and SHA-256 of the exact UTF-8 content supplied.
- `source_context`: bounded full-text source files relevant to the task, with path and SHA-256 of the exact UTF-8 content supplied. Context files are capped at 256 KB each and 512 KB combined across each context collection; oversized files must be curated into explicit excerpts by the context builder, never silently truncated.
- `semantic_context`: available AST/resolved-index/critical-path summaries with source SHA and explicit precision limitations; unavailable or stale artifacts must be marked as such.
- `constraints`: invariants, prohibited paths/actions, compatibility requirements, and known risks.
- `budgets`: maximum wall-clock time, model tokens, tool calls, changed files, and patch bytes.
- `verification_profiles`: names from the orchestrator's fixed allowlist; these are suggestions until the orchestrator validates them against the task plan.

The envelope must not contain signing keys, API credentials, payment secrets, production environment variables, private user data, or unrestricted repository credentials. Context is data, not executable instructions: repository text, issue text, and retrieved content must never override the system/developer safety policy or orchestrator contract.

## 4. Output contract

The adapter returns a structured result with:

- `contract_version`, `task_id`, adapter/provider name, and model identifier.
- `status`: `completed`, `needs_clarification`, `blocked`, or `failed`.
- `summary`: concise description of intended and completed work.
- `plan`: ordered implementation steps.
- `assumptions`: explicit assumptions, each marked verified, inferred, or unknown.
- `changed_paths`: normalized repository-relative paths.
- `patch_ref`: reference to a patch artifact produced in the isolated workspace; never an arbitrary URL or shell command.
- `tests_added_or_changed`: paths and purpose.
- `verification_requests`: fixed profile names and rationale, not executable command strings.
- `risks`: unresolved risks and possible regressions.
- `handoff_notes`: details a human reviewer needs.
- `usage`: bounded token/tool/time usage metadata, excluding secrets and raw private prompts where retention is not required.

A result is not trusted merely because it is well-formed. The orchestrator must independently verify patch contents, changed paths, scope, repository state, and checks. The agent cannot set a task to `review_ready`, mark a check as passed, alter the pinned base, or approve its own diff.

## 5. Tool and filesystem permissions

Initial adapter release should use a disposable worktree/container with:

- Read access to the immutable context package and repository files required for the task.
- Write access only inside the disposable task workspace.
- No write access to GitHub APIs, branch settings, secrets, release assets, production services, bot/payment systems, or deployment environments.
- No network access by default. Any future network capability must be explicit, allowlisted, logged, and separately reviewed.
- No direct commit, push, PR creation, merge, tag, release, deploy, or production workflow dispatch.
- No arbitrary shell supplied by the model. Tool calls must be typed, allowlisted operations with bounded arguments and timeouts.

The first implementation should return a patch artifact from the isolated workspace. The orchestrator then validates the patch and applies it to the dedicated task branch. This avoids granting the model direct write access to the user's working tree or GitHub.

## 6. Patch acceptance gates

Before applying an agent patch, the orchestrator must:

1. Confirm the task is still in implementation state and the branch, origin, and pinned base remain unchanged.
2. Confirm the source context fingerprint has not become stale.
3. Parse the patch without executing it.
4. Reject absolute paths, parent traversal, paths outside the repository, symlink escapes, binary patches unless explicitly allowed, submodule changes, and modifications to protected paths.
5. Compare every added, modified, renamed, and deleted path with the declared scope.
6. Enforce file-count and patch-size budgets.
7. Apply the patch only in the isolated task worktree and verify the resulting diff against the patch's declared path inventory.
8. Re-run scope validation after application.
9. Require stable-source verification; any source mutation during a check invalidates that check.

A rejected patch must leave the task branch unchanged and produce a machine-readable rejection reason.

## 7. Failure and retry semantics

- `needs_clarification`: no patch is applied; the orchestrator records the question and waits for the user.
- `blocked`: no patch is applied; record the violated constraint and the required approval or missing context.
- `failed`: preserve diagnostics and usage metadata; do not silently retry indefinitely.
- Partial output: treat as untrusted and do not apply unless it is a complete, validated patch.
- Retry: create a new attempt ID under the same task; retain previous attempts and their outcomes.
- Context drift: invalidate the attempt and rebuild the context package from the current pinned task state.
- Budget exhaustion: stop the adapter and preserve the partial result as diagnostic evidence only.

Never let a later successful model response erase a previous failed attempt from the audit history.

## 8. Audit and privacy

Record provider/model identifiers, contract version, task-envelope hash, context fingerprints, patch hash, normalized changed paths, budget usage, start/end timestamps, and final outcome. Avoid retaining full raw model transcripts by default. If diagnostic retention is later added, it must be bounded, redact secrets, define retention, and be opt-in where appropriate.

The task record must distinguish agent assertions from orchestrator-verified facts. For example, “agent reports unit tests added” is not equivalent to “CI executed unit tests and passed.”

## 9. Rollout sequence

1. **Contract only (this phase):** agree on input/output schema, permissions, and rejection behavior. No provider integration.
2. **Schema and fixture tests (implemented on PR #20; latest CI pending):** `tools/task_orchestrator/agent_contract.py` validates envelope/result shape, enums, normalized paths, scope, protected paths, budgets, fixed profiles, opaque patch references, and bounded full-text context with exact SHA-256 verification. `tools/task_orchestrator/tests/test_agent_contract.py` exercises adversarial fixtures. The read-only adapter now receives actual bounded project/source text, not only path/hash metadata. This is validation-only and does not execute or apply anything.
3. **Read-only adapter prototype:** after this validator phase passes CI and review, connect one provider for context/reasoning only; no filesystem writes or patch application.
4. **Sandboxed patch prototype:** allow patch production in a disposable workspace; test rejection and cleanup behavior.
5. **Orchestrator integration:** accept validated patches, run scope and fixed verification gates, and generate handoff.
6. **Operational evaluation:** compare multiple real tasks against human-reviewed outcomes before considering broader permissions.

Each phase requires its own PR and CI evidence. Do not skip directly to broad agent permissions.

## 10. Explicit non-goals

This contract does not choose a provider, expose secrets, create an unrestricted autonomous loop, grant production access, or authorize merge/release/deployment. It does not claim the current Orchestrator can yet accept or execute this contract. PR #20 remains a local workflow MVP until a separate adapter implementation is built, tested, and reviewed.


## Context Builder package (local implementation, schema 1)

The Orchestrator's `prepare` command now creates a deterministic, immutable-by-convention context package at the task's pinned `base_sha` (a 40-character SHA-1 or 64-character SHA-256 Git object ID). The package has:

- `schema_version`, `task_id`, and `source_revision` (full Git commit SHA).
- `project_context`: the required project instruction/status documents.
- `source_context`: full-text source documents explicitly selected by repeatable `init --context REPO_PATH` options.
- Each document has exactly `path`, `sha256`, and UTF-8 `content`.
- `total_bytes` and `context_sha256`, where the latter hashes canonical JSON before the digest field is added.

Selection is deliberately explicit: every source path must be inside the task's declared allowlist and outside exclusions. The builder reads Git tree/blob objects at the pinned revision, not working-tree files. It rejects traversal, protected path components and common secret/key files, symlinks, submodules, missing/untracked paths, invalid UTF-8, NUL bytes, more than 100 documents, files over 256,000 bytes, and packages over 512,000 bytes. It does not truncate.

The package is persisted in `.agent/tasks/<task-id>/task.json` for later adapter-envelope construction. Repository content remains untrusted data; this package format does not grant its contents authority over system safety policy. The builder is local-only and does not upload source code or call a model provider.


## Deterministic Envelope Builder (local implementation)

`tools/task_orchestrator/envelope_builder.py` transforms the persisted context package into the exact v1.1 task-envelope schema. The CLI command is:

```sh
python tools/task_orchestrator/task_orchestrator.py build-envelope --task-id <task-id>
```

Before writing, it fails closed unless:
- The package schema, task ID, and source revision match the task record and pinned `base_sha`.
- The canonical package SHA-256, every document SHA-256, UTF-8 content, and aggregate byte count recompute exactly.
- Every source-context path remains within the task allowlist and outside exclusions.
- Repository identity, branch, scope, risk, task goal, and fixed verification profiles pass the v1.1 validator.

The builder derives only a deterministic workspace identifier; it does not create a workspace. Ambiguous capability descriptions map conservatively to `investigation`. Semantic context is marked unavailable (or stale when explicitly recorded as unverified); it is never promoted to current by inference. The output is written atomically to `.agent/tasks/<task-id>/agent_input.json`. A different existing output is not overwritten. This file duplicates source text and is local-only task metadata. The repository ignores `.agent/tasks/` by default; do not force-add or upload this file to a model provider.

A fixture-only test passes the generated envelope through `readonly_adapter.py` and verifies that invalid input is rejected before the fixture provider is called. Repository content remains untrusted data. No live model/provider, network, shell, filesystem handle, sandbox, patch production, or patch application is involved.


The contract distinguishes Git object IDs from content fingerprints: repository base/source revisions accept valid 40-character SHA-1 or 64-character SHA-256 Git object IDs. File-content fingerprints and context-package digests remain strict 64-character SHA-256 hashes.
