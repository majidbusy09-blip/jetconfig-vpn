"""Local fixture-only runner for a previously prepared agent envelope.

This command proves the handoff-to-dispatch path without contacting a model.
It intentionally supports only a fixture result supplied by the operator.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .agent_contract import parse_json_object
from .dispatcher import DispatcherError, dispatch_task, validate_dispatch_record
from .readonly_adapter import FixtureReadOnlyProvider
from .project_artifact_namespace import audit_record_path, ensure_namespace_directory

MAX_INPUT_BYTES = 2_000_000


class LocalDispatchRunnerError(ValueError):
    """A local fixture dispatch input or output is unsafe."""


def _open_parent_directory(path: Path) -> tuple[int, str]:
    """Open every parent component without following symlinks; return dirfd and leaf."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise LocalDispatchRunnerError("Safe no-follow directory operations are unavailable.")
    if os.open not in getattr(os, "supports_dir_fd", set()):
        raise LocalDispatchRunnerError("Descriptor-relative file operations are unavailable.")
    parts = path.parts
    if not parts:
        raise LocalDispatchRunnerError("A file path is required.")
    if path.is_absolute():
        anchor, segments = os.sep, parts[1:]
    else:
        anchor, segments = ".", parts
    if not segments or any(part in {"", ".", ".."} for part in segments):
        raise LocalDispatchRunnerError("File paths must not contain empty or parent-traversal components.")
    leaf = segments[-1]
    if leaf in {"", ".", ".."}:
        raise LocalDispatchRunnerError("File name is invalid.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(anchor, flags)
        for segment in segments[:-1]:
            child = os.open(segment, flags, dir_fd=current)
            metadata = os.fstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise LocalDispatchRunnerError("Every parent path component must be a real directory.")
            os.close(current)
            current = child
        return current, leaf
    except Exception:
        try:
            os.close(current)
        except (OSError, UnboundLocalError):
            pass
        raise


def _read_object(path_text: str) -> dict[str, Any]:
    parent_fd = None
    descriptor = None
    try:
        parent_fd, leaf = _open_parent_directory(Path(path_text))
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LocalDispatchRunnerError("Input must be a regular non-symlink file.")
        if metadata.st_size > MAX_INPUT_BYTES:
            raise LocalDispatchRunnerError("Input exceeds the 2 MB size limit.")
        raw = bytearray()
        while len(raw) <= MAX_INPUT_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_INPUT_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > MAX_INPUT_BYTES or len(raw) != metadata.st_size:
            raise LocalDispatchRunnerError("Input changed while being read or exceeds the 2 MB size limit.")
        return parse_json_object(bytes(raw), max_bytes=MAX_INPUT_BYTES)
    except LocalDispatchRunnerError:
        raise
    except (OSError, ValueError) as exc:
        raise LocalDispatchRunnerError("Input JSON is invalid, unsafe, or unreadable.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_fd is not None:
            os.close(parent_fd)


def _write_new_json(path_text: str, value: dict[str, Any]) -> None:
    parent_fd = None
    descriptor = None
    leaf = None
    created = False
    try:
        parent_fd, leaf = _open_parent_directory(Path(path_text))
        try:
            payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        except UnicodeEncodeError as exc:
            raise LocalDispatchRunnerError("Audit output contains invalid Unicode.") from exc
        descriptor = os.open(
            leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=parent_fd,
        )
        created = True
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise LocalDispatchRunnerError("Audit output write made no progress.")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.fsync(parent_fd)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if created and parent_fd is not None and leaf is not None:
            try:
                os.unlink(leaf, dir_fd=parent_fd)
            except OSError:
                pass
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)


def run_fixture_dispatch(envelope: dict, fixture_result: dict) -> dict:
    provider = FixtureReadOnlyProvider(fixture_result)
    record = dispatch_task(
        envelope,
        provider_name="fixture-provider",
        providers={"fixture-provider": provider},
    )
    validate_dispatch_record(record)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a local fixture-only dispatch against a prepared agent envelope."
    )
    parser.add_argument("--envelope-file", required=True)
    parser.add_argument("--fixture-result-file", required=True)
    parser.add_argument("--output", help="Legacy v1 output path; v2 output is derived from trusted project identity.")
    parser.add_argument("--repository-root", default=".", help="Repository root used for project-scoped v2 audit output.")
    parser.add_argument("--provider", choices=("fixture-provider",), default="fixture-provider")
    args = parser.parse_args(argv)
    try:
        envelope = _read_object(args.envelope_file)
        fixture_result = _read_object(args.fixture_result_file)
        record = run_fixture_dispatch(envelope, fixture_result)
        project_binding = envelope.get("project_binding")
        if project_binding is None:
            if not args.output:
                raise LocalDispatchRunnerError("Legacy v1 dispatch requires an explicit --output path.")
            output_path = Path(args.output)
        else:
            repository = envelope.get("repository")
            source_revision = repository.get("base_sha") if isinstance(repository, dict) else None
            if not isinstance(source_revision, str):
                raise LocalDispatchRunnerError("Project-scoped dispatch has no pinned source revision.")
            root = Path(args.repository_root).resolve(strict=True)
            expected_relative = audit_record_path(
                "dispatch-audit.json", project_binding=project_binding,
                source_revision=source_revision,
            )
            expected_path = root / expected_relative
            if args.output:
                supplied = Path(args.output)
                supplied_path = supplied.resolve(strict=False) if supplied.is_absolute() else (root / supplied).resolve(strict=False)
                if supplied_path != expected_path.resolve(strict=False):
                    raise LocalDispatchRunnerError("Project-scoped audit output must use the derived project/revision namespace.")
            try:
                audit_directory = ensure_namespace_directory(
                    root / "docs/generated", "audit",
                    project_binding=project_binding, source_revision=source_revision,
                )
            except ValueError as exc:
                raise LocalDispatchRunnerError("Project-scoped audit directory is unsafe.") from exc
            output_path = audit_directory / "dispatch-audit.json"
        _write_new_json(str(output_path), record)
    except (LocalDispatchRunnerError, DispatcherError, OSError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print("Fixture dispatch validated. No live model was called and no patch was applied.")
    print("Audit record: " + str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
