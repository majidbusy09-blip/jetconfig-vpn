"""Bind a completed agent result to the exact patch bytes before review.

This module validates artifact identity and patch scope. It never fetches,
writes, applies, or executes an artifact.
"""
from __future__ import annotations

import hashlib
from typing import Any

from tools.task_orchestrator.agent_contract import (
    ContractValidationError,
    validate_result,
)
from tools.task_orchestrator.patch_guard import (
    PatchValidationError,
    validate_patch_text,
)


class PatchPipelineError(ValueError):
    """The agent result and supplied patch artifact do not agree."""


def validate_completed_patch(
    result: Any, envelope: dict, patch_text: str
) -> dict:
    """Validate result schema, artifact digest/size, and every changed path.

    The caller must obtain patch_text through a separately trusted artifact
    transport. This function deliberately accepts bytes as an argument only;
    it does not resolve artifact references or access the network/filesystem.
    """
    try:
        validated = validate_result(result, envelope)
        if validated["status"] != "completed":
            raise PatchPipelineError("Only completed results may carry a patch.")
        if not isinstance(patch_text, str):
            raise PatchPipelineError("Patch artifact must be UTF-8 text.")
        try:
            encoded = patch_text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise PatchPipelineError("Patch artifact is not valid UTF-8.") from exc

        digest = hashlib.sha256(encoded).hexdigest()
        expected_ref = f"artifact:sha256:{digest}"
        if validated["patch_ref"] != expected_ref:
            raise PatchPipelineError("Patch bytes do not match the agent's artifact digest.")
        if validated["usage"]["patch_bytes"] != len(encoded):
            raise PatchPipelineError("Patch byte count does not match the reported usage.")

        summary = validate_patch_text(
            patch_text, envelope, validated["changed_paths"]
        )
        return {
            "task_id": validated["task_id"],
            "patch_ref": expected_ref,
            "patch_validation": summary,
            "status": "validated_for_human_review",
            "applied": False,
        }
    except (ContractValidationError, PatchValidationError) as exc:
        raise PatchPipelineError(str(exc)) from exc
