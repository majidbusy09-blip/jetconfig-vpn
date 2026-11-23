# Local Content-Addressed Patch Artifact Store

## Purpose
The patch artifact store closes the gap between an agent result's
`artifact:sha256:<digest>` reference and the exact patch bytes that must be
reviewed. It is a local filesystem component; it does not fetch remote objects,
upload repository data, apply patches, or run verification commands.

## Storage contract
- The host supplies an existing artifact directory explicitly.
- Artifacts are immutable, named by their lowercase SHA-256 digest, and created
  with exclusive file creation (no overwrite).
- Reads reject missing files, symlinks, non-regular files, size changes,
  oversized content, invalid UTF-8, and digest mismatches.
- The default maximum artifact size is 2 MB; a caller may choose a lower limit.
- Re-storing identical bytes is idempotent. A digest path containing different
  bytes is rejected.
- The store should live outside the checked-out source tree and should be
  writable only by the trusted local host process.

## Example
```python
from tools.task_orchestrator.patch_artifacts import LocalPatchArtifactStore

store = LocalPatchArtifactStore("/var/lib/jet-agent/artifacts")
patch_ref = store.store_patch(patch_text)

# After receiving a completed result, resolve only its exact digest reference.
review = store.validate_result_patch(agent_result, accepted_envelope)
assert review["status"] == "validated_for_human_review"
assert review["applied"] is False
```

The artifact reference is derived from the exact UTF-8 patch bytes. The result
validator independently checks the result schema, byte count, digest, task
scope, changed-path declaration, and unified-diff safety rules.

## Explicit non-capabilities
- No GitHub Actions artifact download or upload is implemented.
- No remote URL or arbitrary path can be supplied by task content.
- No patch is applied, staged, committed, pushed, or merged.
- No verification profile is executed by this module.
- A successful result means only `validated_for_human_review`, not that the
  proposed code is correct or safe to merge.

A production artifact transport still needs a separately reviewed identity,
authorization, retention, and integrity boundary. Until then, use only the
local content-addressed store inside a trusted host-controlled workspace.
