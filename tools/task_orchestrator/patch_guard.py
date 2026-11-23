"""Fail-closed validation for proposed unified-diff artifacts.

This module inspects patch text only. It never applies a patch, writes files,
runs commands, or fetches an artifact.
"""
from __future__ import annotations

import fnmatch
import re
from typing import Any

from tools.task_orchestrator.agent_contract import (
    ContractValidationError,
    _path,
    validate_envelope,
)

_DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")
_MODE_HEADER = re.compile(r"^(?:new file mode|deleted file mode) (\d{6})$")
_MAX_PATCH_BYTES_HARD = 2_000_000


class PatchValidationError(ValueError):
    """A proposed patch failed a fail-closed acceptance rule."""


def _reject(message: str) -> None:
    raise PatchValidationError(message)


def _safe_patch_path(raw: str, envelope: dict) -> str:
    try:
        path = _path(raw, "patch path")
    except ContractValidationError as exc:
        raise PatchValidationError(str(exc)) from exc

    scope = envelope["scope"]
    if not any(fnmatch.fnmatchcase(path, pattern) for pattern in scope["allowed_paths"]):
        _reject(f"patch path is outside allowed scope: {path}")
    if any(fnmatch.fnmatchcase(path, pattern) for pattern in scope["excluded_paths"]):
        _reject(f"patch path is explicitly excluded: {path}")
    return path


def validate_patch_text(patch_text: Any, envelope: dict, declared_paths: list[str]) -> dict:
    """Validate a unified diff against its immutable task envelope.

    Returns a compact summary only. File contents are never applied or
    interpreted as executable instructions.
    """
    validate_envelope(envelope)
    if not isinstance(patch_text, str):
        _reject("patch must be UTF-8 text")
    try:
        encoded = patch_text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise PatchValidationError("patch is not valid UTF-8 text") from exc

    limit = min(envelope["budgets"]["max_patch_bytes"], _MAX_PATCH_BYTES_HARD)
    if not encoded or len(encoded) > limit:
        _reject(f"patch size must be between 1 and {limit} bytes")
    if "\x00" in patch_text:
        _reject("patch contains a NUL byte")

    if not isinstance(declared_paths, list) or any(not isinstance(item, str) for item in declared_paths):
        _reject("declared_paths must be a list of repository-relative paths")

    lines = patch_text.splitlines()
    paths: list[str] = []
    current: tuple[str, str] | None = None
    current_headers: set[str] = set()
    current_null_headers: set[str] = set()
    current_hunk = False

    for line in lines:
        if line.startswith("GIT binary patch") or line.startswith("Binary files "):
            _reject("binary patches are not accepted")
        if line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            _reject("rename and copy patches are not accepted in this phase")
        if line.startswith(("old mode ", "new mode ")):
            _reject("file mode changes are not accepted")
        if line.startswith("index ") and " 160000" in line:
            _reject("submodule changes are not accepted")
        if line.startswith(("--- ", "+++ ")) and not current_hunk:
            if current is None:
                _reject("file header appeared without a diff header")
            marker = "---" if line.startswith("--- ") else "+++"
            if marker in current_headers:
                _reject("duplicate file header")
            raw = line[4:].split("\t", 1)[0]
            if raw == "/dev/null":
                current_null_headers.add(marker)
                current_headers.add(marker)
                continue
            prefix = "a/" if marker == "---" else "b/"
            if not raw.startswith(prefix):
                _reject("file header path does not use the expected side prefix")
            path = _safe_patch_path(raw[len(prefix):], envelope)
            expected = current[0] if marker == "---" else current[1]
            if path != expected:
                _reject("file header path does not match its diff side")
            current_headers.add(marker)
        elif line.startswith("diff --git "):
            match = _DIFF_HEADER.fullmatch(line)
            if not match:
                _reject("malformed or unsupported diff header")
            left = _safe_patch_path(match.group(1), envelope)
            right = _safe_patch_path(match.group(2), envelope)
            if current is not None and (
                current_headers != {"---", "+++"}
                or current_null_headers == {"---", "+++"}
                or not current_hunk
            ):
                _reject("each file diff must contain valid headers and at least one hunk")
            if left != right:
                _reject("renames are not accepted in this phase")
            if left in paths:
                _reject(f"duplicate patch path: {left}")
            paths.append(left)
            current = (left, right)
            current_headers = set()
            current_null_headers = set()
            current_hunk = False
        elif line.startswith("@@@"):
            _reject("combined diff hunks are not accepted")
        elif line.startswith("@@"):
            if current is None:
                _reject("hunk appeared without a diff header")
            if not re.fullmatch(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(?: .*)?", line):
                _reject("malformed unified-diff hunk header")
            current_hunk = True
        elif line.startswith("new file mode ") or line.startswith("deleted file mode "):
            match = _MODE_HEADER.fullmatch(line)
            if not match or match.group(1) != "100644":
                _reject("only regular non-executable text files are accepted")
        elif line.startswith("Submodule "):
            _reject("submodule changes are not accepted")

    if not paths:
        _reject("patch contains no file changes")
    if current_headers != {"---", "+++"} or current_null_headers == {"---", "+++"}:
        _reject("each file diff must contain valid, matching --- and +++ headers")
    if not current_hunk:
        _reject("each file diff must contain a text hunk")
    if len(paths) > envelope["budgets"]["max_changed_files"]:
        _reject("patch exceeds the declared changed-file budget")

    normalized_declared = [_safe_patch_path(item, envelope) for item in declared_paths]
    if len(set(normalized_declared)) != len(normalized_declared) or set(normalized_declared) != set(paths):
        _reject("parsed patch paths do not exactly match the agent-declared changed_paths")

    return {
        "changed_paths": paths,
        "file_count": len(paths),
        "patch_bytes": len(encoded),
    }
