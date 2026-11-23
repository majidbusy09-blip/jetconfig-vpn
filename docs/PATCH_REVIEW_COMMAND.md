# Patch Review Command

## Usage
After a provider result and its patch bytes have been placed in task-local files, create the task-local patch store and run:

```sh
mkdir -p .agent/tasks/<task-id>/patch-artifacts
python -m tools.task_orchestrator.patch_review_command --task-id <task-id>
```

The default inputs are:
- `.agent/tasks/<task-id>/agent_input.json` — the accepted agent envelope.
- `.agent/tasks/<task-id>/agent_result.json` — the provider-neutral result contract.
- `.agent/tasks/<task-id>/patch-artifacts/` — content-addressed patch bytes referenced by the result.

The result file may be overridden with `--result-file`, and the artifact directory with `--artifact-dir`; both must resolve inside the task directory. The artifact directory must already exist.

## Live checks
The command reads the current GitHub Issue and lock-ref lease using the existing read-only GitHub adapters, checks that the lock ref did not move during the lease read, and inspects the current local branch, HEAD, pinned-base ancestry, and worktree cleanliness. It then invokes the live patch review gate and exact SHA-256/diff/scope validation.

Set `GITHUB_TOKEN` or `GH_TOKEN` to a token with read-only repository access. The token is not written to task files or passed to child Git commands.

## Safety
This command is read-only. It does not apply patches, run verification profiles, execute provider code, commit, push, merge, upload source, or change GitHub state. Success means `ready_for_human_review` only and must still be reviewed by a human.
