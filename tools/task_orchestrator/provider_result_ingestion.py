"""Safely ingest a provider-neutral result and exact patch bytes into a task.

This is a local handoff step only. It never invokes a provider, transfers source,
applies a patch, executes verification commands, or writes to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from . import task_orchestrator as orchestrator
from .agent_contract import ContractValidationError, parse_json_object, validate_result
from .patch_artifacts import LocalPatchArtifactStore, PatchArtifactError

MAX_RESULT_BYTES = 1_000_000
MAX_PATCH_BYTES = 2_000_000


class ProviderResultIngestionError(ValueError):
    """A provider result or patch could not be safely ingested."""


def _task_path(task_dir: Path, supplied: str | Path, *, must_exist: bool) -> Path:
    raw = Path(supplied)
    if raw.is_absolute() or not raw.parts or any(part in {"", ".", ".."} for part in raw.parts):
        raise ProviderResultIngestionError("All input and output paths must be task-relative safe paths.")
    root = task_dir.resolve(strict=True)
    candidate = root / raw
    current = root
    for part in raw.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if must_exist or current != candidate:
                raise ProviderResultIngestionError("A required task path component does not exist.")
            continue
        except OSError as exc:
            raise ProviderResultIngestionError("A task path component cannot be inspected safely.") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ProviderResultIngestionError("Symlinks are not allowed in task input or output paths.")
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ProviderResultIngestionError("A task path escapes the task directory or cannot be resolved.") from exc
    return resolved


def _read_regular_file(path: Path, *, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProviderResultIngestionError(label + " is missing or unsafe.") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size < 1 or metadata.st_size > limit:
            raise ProviderResultIngestionError(label + " must be a non-empty regular file within its size limit.")
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(limit + 1)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    if len(raw) != metadata.st_size or len(raw) > limit:
        raise ProviderResultIngestionError(label + " changed while being read or exceeded its size limit.")
    return raw


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ProviderResultIngestionError("The final agent_result.json already exists; refusing to overwrite it.") from exc
    except OSError as exc:
        raise ProviderResultIngestionError("Could not create the final result file safely.") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def ingest_provider_result(
    task_dir: Path,
    envelope: dict[str, Any],
    *,
    provider_result_path: str | Path = "provider_result.json",
    patch_path: str | Path = "provider_patch.diff",
    result_path: str | Path = "agent_result.json",
    artifact_dir: str | Path = "patch-artifacts",
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> dict[str, Any]:
    """Validate, content-address, and persist one result without overwriting."""
    root = task_dir.resolve(strict=True)
    if not root.is_dir() or task_dir.is_symlink():
        raise ProviderResultIngestionError("Task directory must be an existing regular directory.")
    result_input = _task_path(root, provider_result_path, must_exist=True)
    patch_input = _task_path(root, patch_path, must_exist=True)
    final_result = _task_path(root, result_path, must_exist=False)
    artifact_root = _task_path(root, artifact_dir, must_exist=False)
    if len({result_input, patch_input, final_result, artifact_root}) != 4:
        raise ProviderResultIngestionError("Input, output, and artifact paths must be distinct.")

    raw_result = _read_regular_file(result_input, limit=MAX_RESULT_BYTES, label="Provider result")
    raw_patch = _read_regular_file(patch_input, limit=MAX_PATCH_BYTES, label="Provider patch")
    try:
        provider_result = parse_json_object(raw_result, max_bytes=MAX_RESULT_BYTES)
        patch_text = raw_patch.decode("utf-8", errors="strict")
    except (ContractValidationError, UnicodeDecodeError) as exc:
        raise ProviderResultIngestionError("Provider result JSON or patch UTF-8 is invalid.") from exc

    try:
        validated_result = validate_result(provider_result, envelope)
    except ContractValidationError as exc:
        raise ProviderResultIngestionError("Provider result failed the task contract.") from exc

    digest = hashlib.sha256(raw_patch).hexdigest()
    expected_ref = "artifact:sha256:" + digest
    if validated_result["patch_ref"] != expected_ref:
        raise ProviderResultIngestionError("Provider result patch_ref does not match the exact patch bytes.")
    if validated_result["usage"]["patch_bytes"] != len(raw_patch):
        raise ProviderResultIngestionError("Provider result patch_bytes does not match the exact patch length.")

    if not artifact_root.exists():
        try:
            artifact_root.mkdir(mode=0o700)
        except FileExistsError:
            pass
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise ProviderResultIngestionError("Artifact directory must be a regular non-symlink directory.")

    try:
        store = LocalPatchArtifactStore(
            artifact_root,
            project_binding=project_binding,
            source_revision=source_revision,
        )
        stored_ref = store.store_patch(patch_text)
        if stored_ref != expected_ref:
            raise ProviderResultIngestionError("Stored patch reference differs from the validated digest.")
        validation = store.validate_result_patch(validated_result, envelope)
    except PatchArtifactError as exc:
        raise ProviderResultIngestionError("Patch artifact failed local integrity or scope validation.") from exc

    _write_new_json(final_result, validated_result)
    return {
        "task_id": validated_result["task_id"],
        "provider": validated_result["provider"],
        "patch_ref": stored_ref,
        "patch_validation": validation,
        "result_file": final_result.relative_to(root).as_posix(),
        "artifact_directory": store.root.relative_to(root).as_posix(),
        "status": "validated_for_human_review",
        "applied": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a local provider result and patch into a prepared task."
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--provider-result-file", default="provider_result.json")
    parser.add_argument("--patch-file", default="provider_patch.diff")
    parser.add_argument("--result-file", default="agent_result.json")
    parser.add_argument("--artifact-dir", default="patch-artifacts")
    args = parser.parse_args(argv)
    try:
        if not orchestrator.TASK_ID_RE.fullmatch(args.task_id):
            raise ProviderResultIngestionError("Invalid task ID.")
        root = orchestrator.repository_root()
        record, record_path = orchestrator.load_record(root, args.task_id)
        task_dir = record_path.parent
        envelope_path = _task_path(task_dir, "agent_input.json", must_exist=True)
        envelope_raw = _read_regular_file(envelope_path, limit=MAX_RESULT_BYTES, label="Accepted agent envelope")
        envelope = parse_json_object(envelope_raw, max_bytes=MAX_RESULT_BYTES)
        outcome = ingest_provider_result(
            task_dir,
            envelope,
            provider_result_path=args.provider_result_file,
            patch_path=args.patch_file,
            result_path=args.result_file,
            artifact_dir=args.artifact_dir,
            project_binding=record.get("github_project_binding"),
            source_revision=(record.get("repository", {}).get("base_sha")
                             if record.get("github_project_binding") is not None else None),
        )
    except (ProviderResultIngestionError, ContractValidationError, OSError, ValueError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    print("No provider was called, no patch was applied, and no source was uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
