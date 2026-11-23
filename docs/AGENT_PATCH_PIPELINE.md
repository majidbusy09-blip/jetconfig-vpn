# Agent patch validation pipeline

## Purpose

Bind an agent's structured completion claim to the exact patch bytes supplied by a separately trusted artifact transport. The pipeline is a validation gate only; it does not download, write, apply, execute, commit, or push a patch.

## Current implementation

- `tools/task_orchestrator/agent_contract.py` validates the task envelope and structured result.
- `tools/task_orchestrator/patch_guard.py` parses unified-diff text and rejects unsafe paths, out-of-scope/excluded files, binary patches, renames/copies, mode changes, symlinks, submodules, malformed headers, changed-file budget overflow, and disagreement with the declared changed-path list.
- `tools/task_orchestrator/patch_pipeline.py` connects the two validators. It recomputes SHA-256 from the supplied UTF-8 patch bytes, checks the opaque `patch_ref`, checks the exact reported byte count, then validates every parsed path against the immutable task envelope.
- A successful response is labelled `validated_for_human_review` and explicitly reports `applied: false`.

## Required trust boundary

The caller is responsible for obtaining the artifact bytes from a trusted, authenticated artifact store and associating them with the task. This module intentionally does not resolve `artifact:sha256:...` references or make network/filesystem calls. The digest binds the bytes to the agent's claim; it does not prove who created the artifact or that the provider is trustworthy.

## Not implemented

- No patch application or workspace mutation.
- No automatic provider connection or artifact download.
- No OS/container sandbox.
- No GitHub write permissions, commits, pushes, PR creation, merge, release, or deployment.
- No claim that a validated patch is correct; a human must inspect the complete diff and then run the task's fixed verification profiles.

## Tests

Run:

```sh
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py'
```

The pipeline fixtures cover matching digest/size, tampered bytes, incorrect size, out-of-scope paths, disagreement with declared paths, and non-completed results.
