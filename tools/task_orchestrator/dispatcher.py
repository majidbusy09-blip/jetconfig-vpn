"""Provider-neutral, fail-closed dispatcher for bounded coding-agent tasks.

The dispatcher coordinates a trusted in-process adapter supplied by the host.
It does not discover providers, make network calls, launch processes, grant
workspace access, apply patches, or write to GitHub. A production host must
register only explicitly configured adapters and run them inside an approved
isolated runtime.
"""
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from .agent_contract import ContractValidationError, validate_envelope
from .readonly_adapter import ReadOnlyAdapterError, run_readonly


class DispatcherError(RuntimeError):
    """A dispatch request was rejected or its adapter failed."""


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def dispatch_task(
    envelope: Mapping[str, Any],
    *,
    provider_name: str,
    providers: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Dispatch one validated envelope to an explicitly registered adapter.

    The provider registry is supplied by trusted host code, never by task data.
    The returned audit record contains metadata only; it deliberately excludes
    raw prompts, project/source text, secrets, and provider transcripts.
    """
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise DispatcherError("An explicit provider name is required.")
    if not isinstance(providers, Mapping) or provider_name not in providers:
        raise DispatcherError("Requested provider is not explicitly registered.")

    canonical = copy.deepcopy(dict(envelope)) if isinstance(envelope, Mapping) else envelope
    try:
        validate_envelope(canonical)
    except (ContractValidationError, TypeError, ValueError) as exc:
        raise DispatcherError("Task envelope failed contract validation.") from exc

    adapter = providers[provider_name]
    if not callable(getattr(adapter, "complete", None)):
        raise DispatcherError("Registered provider does not implement complete(envelope).")

    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    envelope_digest = _canonical_digest(canonical)
    context = canonical["project_context"] + canonical["source_context"]
    context_fingerprints = [
        {"path": item["path"], "sha256": item["sha256"]} for item in context
    ]

    try:
        result = run_readonly(canonical, adapter)
    except ReadOnlyAdapterError as exc:
        failed_at = datetime.now(timezone.utc)
        return {
            "dispatch_id": str(uuid.uuid4()),
            "task_id": canonical["task_id"],
            "provider": provider_name,
            "envelope_sha256": envelope_digest,
            "context_fingerprints": context_fingerprints,
            "status": "failed",
            "started_at": started.isoformat(),
            "finished_at": failed_at.isoformat(),
            "provider_invoked": True,
            "result_validated": False,
            "patch_validation": "not-run",
            "patch_applied": False,
            "error_type": type(exc).__name__,
        }

    if result["provider"] != provider_name:
        raise DispatcherError("Provider result identity does not match the registered adapter.")

    finished = datetime.now(timezone.utc)
    return {
        "dispatch_id": str(uuid.uuid4()),
        "task_id": canonical["task_id"],
        "provider": provider_name,
        "model": result["model"],
        "envelope_sha256": envelope_digest,
        "context_fingerprints": context_fingerprints,
        "status": result["status"],
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "provider_invoked": True,
        "result_validated": True,
        "changed_paths": result["changed_paths"],
        "patch_ref": result["patch_ref"],
        "patch_validation": "pending-artifact-validation" if result["patch_ref"] else "not-applicable",
        "patch_applied": False,
        "verification_requests": result["verification_requests"],
        "risks": result["risks"],
    }


def validate_dispatch_record(record: Any) -> dict[str, Any]:
    """Validate the stable, metadata-only dispatch audit record."""
    required = {
        "dispatch_id", "task_id", "provider", "envelope_sha256",
        "context_fingerprints", "status", "started_at", "finished_at",
        "provider_invoked", "result_validated", "patch_validation",
        "patch_applied",
    }
    optional = {
        "model", "changed_paths", "patch_ref", "verification_requests",
        "risks", "error_type",
    }
    if not isinstance(record, dict) or not required.issubset(record) or record.keys() - required - optional:
        raise DispatcherError("Dispatch audit record has unexpected or missing fields.")
    try:
        uuid.UUID(record["dispatch_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise DispatcherError("Dispatch ID is invalid.") from exc
    if not isinstance(record["task_id"], str) or not isinstance(record["provider"], str):
        raise DispatcherError("Dispatch identity fields must be text.")
    if not isinstance(record["envelope_sha256"], str) or len(record["envelope_sha256"]) != 64:
        raise DispatcherError("Envelope digest is invalid.")
    if record["status"] not in {"completed", "needs_clarification", "blocked", "failed"}:
        raise DispatcherError("Dispatch status is invalid.")
    if type(record["provider_invoked"]) is not bool or type(record["result_validated"]) is not bool:
        raise DispatcherError("Dispatch evidence flags must be booleans.")
    if record["patch_applied"] is not False:
        raise DispatcherError("Dispatcher must never claim to apply a patch.")
    if record["status"] == "failed" and record["result_validated"] is not False:
        raise DispatcherError("Failed dispatch cannot claim a validated result.")
    if record["status"] != "failed" and record["result_validated"] is not True:
        raise DispatcherError("Successful adapter response must be validated.")
    return copy.deepcopy(record)
