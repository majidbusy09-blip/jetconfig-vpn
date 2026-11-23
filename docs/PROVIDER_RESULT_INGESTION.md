# Provider Result Ingestion

## Purpose

This local step closes the handoff between a provider-neutral result and the
read-only patch review command. It accepts a structured result plus the exact
UTF-8 unified-diff bytes, validates their digest and task contract, stores the
patch by SHA-256, and creates the task-local `agent_result.json`.

## Usage

Place the provider output files inside the accepted task directory:

- `provider_result.json`: complete provider-neutral result contract
- `provider_patch.diff`: exact patch bytes referenced by `patch_ref`

Then run from the repository root:

```sh
python -m tools.task_orchestrator.provider_result_ingestion --task-id <task-id>
python -m tools.task_orchestrator.patch_review_command --task-id <task-id>
```

Optional flags can change the task-relative input/output names:
`--provider-result-file`, `--patch-file`, `--result-file`, and
`--artifact-dir`. Paths must remain inside the task directory.

## Safety and semantics

- The result contract, task ID, scope, verification requests, context
  fingerprints, exact patch SHA-256, and reported patch byte count are checked.
- The exact patch bytes are stored under `patch-artifacts/<sha256>.patch`.
- Existing final result files are never overwritten; symlinks and path escapes
  are rejected.
- The patch pipeline validates diff structure and allowed changed paths before
  writing `agent_result.json`.
- A successful outcome is `validated_for_human_review`, with `applied: false`.
- This command does not call a provider, upload source, execute code, run
  verification profiles, apply a patch, commit, push, or write to GitHub.

The provider must have been invoked separately by a trusted host. This command
only ingests its local output; it is not evidence that a live model ran.
