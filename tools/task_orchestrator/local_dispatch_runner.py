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

MAX_INPUT_BYTES = 2_000_000


class LocalDispatchRunnerError(ValueError):
    """A local fixture dispatch input or output is unsafe."""


def _read_object(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if path.is_symlink() or not path.is_file():
        raise LocalDispatchRunnerError("Input must be a regular non-symlink file.")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise LocalDispatchRunnerError("Input exceeds the 2 MB size limit.")
    try:
        return parse_json_object(path.read_bytes(), max_bytes=MAX_INPUT_BYTES)
    except (OSError, ValueError) as exc:
        raise LocalDispatchRunnerError("Input JSON is invalid or unreadable.") from exc


def _write_new_json(path_text: str, value: dict[str, Any]) -> None:
    path = Path(path_text)
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or path.exists() or path.is_symlink():
        raise LocalDispatchRunnerError("Output parent must exist and output must not already exist.")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


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
    parser.add_argument("--output", required=True)
    parser.add_argument("--provider", choices=("fixture-provider",), default="fixture-provider")
    args = parser.parse_args(argv)
    try:
        envelope = _read_object(args.envelope_file)
        fixture_result = _read_object(args.fixture_result_file)
        record = run_fixture_dispatch(envelope, fixture_result)
        _write_new_json(args.output, record)
    except (LocalDispatchRunnerError, DispatcherError, OSError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print("Fixture dispatch validated. No live model was called and no patch was applied.")
    print("Audit record: " + args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
