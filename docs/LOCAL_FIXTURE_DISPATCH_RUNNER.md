# Local Fixture Dispatch Runner

The `local_dispatch_runner` command connects an already accepted
`.agent/tasks/<task-id>/agent_input.json` envelope to the provider-neutral
dispatcher using a locally supplied fixture result.

Example:

```sh
python -m tools.task_orchestrator.local_dispatch_runner \
  --envelope-file .agent/tasks/<task-id>/agent_input.json \
  --fixture-result-file ./fixture-result.json \
  --output .agent/tasks/<task-id>/dispatch-audit.json
```

The command currently allows only `fixture-provider`. It is an end-to-end
plumbing test, not an actual model call. Inputs are bounded regular files;
output is created exclusively and is never overwritten. The audit record
contains metadata and fingerprints, not the task's raw goal or source text.

The resulting `patch_ref` is still only a digest reference. A separate trusted
artifact transport must retrieve the exact patch bytes and pass them through
`validate_completed_patch`. No patch is applied and no verification command
is executed by this runner.
