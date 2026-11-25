"""Strict, provider-neutral validation for coding-agent contract payloads.

This module validates data only. It never executes commands, fetches artifacts,
applies patches, or treats agent claims as verified facts.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any

CONTRACT_VERSION = "1.1"
ALLOWED_CAPABILITIES = {"implementation", "bug_fix", "refactor", "documentation", "investigation"}
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_STATUSES = {"completed", "needs_clarification", "blocked", "failed"}
ALLOWED_ASSUMPTIONS = {"verified", "inferred", "unknown"}
ALLOWED_PROFILES = {
    "python-tooling-tests", "flutter-tests", "flutter-analysis", "lexical-memory-audit"
}
MAX_JSON_BYTES = 1_000_000
MAX_CONTEXT_FILE_BYTES = 256_000
MAX_CONTEXT_TOTAL_BYTES = 512_000
MAX_TEXT = 12_000
MAX_ITEMS = 200
MAX_FILES = 100
MAX_PATCH_BYTES = 2_000_000
MAX_WALL_SECONDS = 7_200
MAX_TOKENS = 500_000
MAX_TOOL_CALLS = 2_000
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PATCH_RE = re.compile(r"^artifact:sha256:([0-9a-f]{64})$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
REPOSITORY_ID_RE = re.compile(r"^[0-9]{1,20}$")

PROTECTED_EXACT = {
    ".env", ".env.local", ".env.production", "key.properties",
    "android/key.properties", "android/app/google-services.json",
    "android/app/src/main/AndroidManifest.xml",
    ".github/workflows/build.yml",
}
PROTECTED_PARTS = {
    ".git", ".agent", ".secrets", "secrets", "credentials",
    "keystore", "signing", "release-assets",
}


class ContractValidationError(ValueError):
    """A contract payload failed a fail-closed validation rule."""


def _path_matches(path: str, pattern: str) -> bool:
    """Match repository paths without allowing '*' to cross '/' boundaries.

    A complete '**' segment matches zero or more path segments.
    """
    path_parts = path.split("/")
    pattern_parts = pattern.split("/")
    memo: dict[tuple[int, int], bool] = {}

    def match(path_index: int, pattern_index: int) -> bool:
        key = (path_index, pattern_index)
        if key in memo:
            return memo[key]
        if pattern_index == len(pattern_parts):
            result = path_index == len(path_parts)
        elif pattern_parts[pattern_index] == "**":
            result = match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        else:
            result = (
                path_index < len(path_parts)
                and fnmatch.fnmatchcase(path_parts[path_index], pattern_parts[pattern_index])
                and match(path_index + 1, pattern_index + 1)
            )
        memo[key] = result
        return result

    return match(0, 0)


def _fail(message: str) -> None:
    raise ContractValidationError(message)


def _object(value: Any, name: str, required: set[str], optional: set[str] = set()) -> dict:
    if not isinstance(value, dict):
        _fail(f"{name} must be an object")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        _fail(f"{name} missing fields: {', '.join(sorted(missing))}")
    if extra:
        _fail(f"{name} has unexpected fields: {', '.join(sorted(extra))}")
    return value


def _enum(value: Any, allowed: set[str], name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        _fail(f"{name} must be one of the allowed string values")
    return value


def _text(value: Any, name: str, limit: int = MAX_TEXT, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        _fail(f"{name} must be a {'possibly empty ' if empty else ''}string of at most {limit} characters")
    if "\x00" in value:
        _fail(f"{name} contains a NUL character")
    return value


def _strings(value: Any, name: str, *, maximum: int = MAX_ITEMS) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        _fail(f"{name} must be a list with at most {maximum} entries")
    result = [_text(item, f"{name}[]", 512) for item in value]
    if len(set(result)) != len(result):
        _fail(f"{name} must not contain duplicates")
    return result


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        _fail(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _git_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value):
        _fail(f"{name} must be a 40- or 64-character lowercase Git object ID")
    return value


def _path(value: Any, name: str, *, pattern: bool = False) -> str:
    raw = _text(value, name, 512)
    if raw.startswith("/") or "\\" in raw or re.match(r"^[A-Za-z]:", raw):
        _fail(f"{name} must be a repository-relative POSIX path")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail(f"{name} contains an unsafe path segment")
    if not pattern and any(char in raw for char in "*?[]"):
        _fail(f"{name} must be a concrete path, not a glob")
    if pattern and any(part == "**" for part in parts[:-1]):
        # ** is allowed only as a complete path segment.
        pass
    if any(part.lower() in PROTECTED_PARTS for part in parts) or PurePosixPath(raw).name.lower() in {"key.properties", "upload-keystore.jks", "release.keystore"}:
        _fail(f"{name} targets a protected path")
    normalized = PurePosixPath(raw).as_posix()
    if normalized in PROTECTED_EXACT or normalized.startswith(".github/workflows/"):
        _fail(f"{name} targets a protected path")
    return normalized


def _path_list(value: Any, name: str, *, patterns: bool = False, maximum: int = MAX_ITEMS) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        _fail(f"{name} must be a non-empty list with at most {maximum} entries")
    items = [_path(item, f"{name}[]", pattern=patterns) for item in value]
    if len(set(items)) != len(items):
        _fail(f"{name} must not contain duplicates")
    return items


def _records(value: Any, name: str, *, max_items: int = MAX_ITEMS) -> list[dict]:
    if not isinstance(value, list) or len(value) > max_items:
        _fail(f"{name} must be a list with at most {max_items} entries")
    if any(not isinstance(item, dict) for item in value):
        _fail(f"{name} entries must be objects")
    return value


def _fingerprints(value: Any, name: str) -> list[dict]:
    entries = _records(value, name)
    seen = set()
    for item in entries:
        _object(item, f"{name} entry", {"path", "sha256"})
        path = _path(item["path"], f"{name}.path")
        _sha(item["sha256"], f"{name}.sha256")
        if path in seen:
            _fail(f"{name} contains duplicate paths")
        seen.add(path)
    return entries


def _context_documents(value: Any, name: str) -> list[dict]:
    """Validate bounded full-text context documents and their exact content hashes."""
    entries = _records(value, name, max_items=MAX_FILES)
    seen: set[str] = set()
    total_bytes = 0
    for item in entries:
        _object(item, f"{name} entry", {"path", "sha256", "content"})
        path = _path(item["path"], f"{name}.path")
        digest = _sha(item["sha256"], f"{name}.sha256")
        content = _text(item["content"], f"{name}.content", MAX_CONTEXT_FILE_BYTES)
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_CONTEXT_FILE_BYTES:
            _fail(f"{name}.content exceeds the per-file byte limit")
        total_bytes += len(encoded)
        if total_bytes > MAX_CONTEXT_TOTAL_BYTES:
            _fail(f"{name} exceeds the total context byte limit")
        if hashlib.sha256(encoded).hexdigest() != digest:
            _fail(f"{name} content hash does not match its fingerprint")
        if path in seen:
            _fail(f"{name} contains duplicate paths")
        seen.add(path)
    return entries


def _budget(value: Any) -> dict:
    limits = {
        "max_wall_seconds": MAX_WALL_SECONDS,
        "max_tokens": MAX_TOKENS,
        "max_tool_calls": MAX_TOOL_CALLS,
        "max_changed_files": MAX_FILES,
        "max_patch_bytes": MAX_PATCH_BYTES,
    }
    _object(value, "budgets", set(limits))
    for key, ceiling in limits.items():
        number = value[key]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1 or number > ceiling:
            _fail(f"budgets.{key} must be an integer from 1 to {ceiling}")
    return value


def validate_envelope(data: Any) -> dict:
    required = {
        "contract_version", "task_id", "goal", "capability", "risk", "repository",
        "scope", "project_context", "source_context", "semantic_context",
        "constraints", "budgets", "verification_profiles",
    }
    obj = _object(data, "task envelope", required, {"project_binding", "memory_manifest"})
    if obj["contract_version"] != CONTRACT_VERSION:
        _fail("unsupported contract_version")
    if not isinstance(obj["task_id"], str) or not TASK_ID_RE.fullmatch(obj["task_id"]):
        _fail("invalid task_id")
    _text(obj["goal"], "goal", 8_000)
    _enum(obj["capability"], ALLOWED_CAPABILITIES, "capability")
    _enum(obj["risk"], ALLOWED_RISKS, "risk")

    repo = _object(obj["repository"], "repository",
                   {"name", "branch", "base_sha", "workspace_id"})
    if not isinstance(repo["name"], str) or not REPO_RE.fullmatch(repo["name"]):
        _fail("repository.name must be owner/repository")
    _text(repo["branch"], "repository.branch", 255)
    if repo["branch"] in {"main", "master"}:
        _fail("agent workspace cannot target a protected branch")
    _git_sha(repo["base_sha"], "repository.base_sha")
    if not isinstance(repo["workspace_id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", repo["workspace_id"]):
        _fail("invalid repository.workspace_id")

    scope = _object(obj["scope"], "scope",
                    {"allowed_paths", "excluded_paths", "scope_reason"})
    _path_list(scope["allowed_paths"], "scope.allowed_paths", patterns=True)
    if not isinstance(scope["excluded_paths"], list) or len(scope["excluded_paths"]) > MAX_ITEMS:
        _fail("scope.excluded_paths must be a list")
    for item in scope["excluded_paths"]:
        _path(item, "scope.excluded_paths[]", pattern=True)
    _text(scope["scope_reason"], "scope.scope_reason", 2_000, empty=True)

    project_documents = _context_documents(obj["project_context"], "project_context")
    _context_documents(obj["source_context"], "source_context")
    has_binding = "project_binding" in obj
    has_memory = "memory_manifest" in obj
    if has_binding != has_memory:
        _fail("project_binding and memory_manifest must be supplied together")
    if has_binding:
        binding = _object(obj["project_binding"], "project_binding", {
            "project_id", "repository_id", "repository_full_name", "default_branch",
            "manifest_schema_version", "manifest_sha256", "base_sha",
        })
        if not isinstance(binding["project_id"], str) or not PROJECT_ID_RE.fullmatch(binding["project_id"]):
            _fail("project_binding.project_id is malformed")
        if not isinstance(binding["repository_id"], str) or not REPOSITORY_ID_RE.fullmatch(binding["repository_id"]):
            _fail("project_binding.repository_id is malformed")
        if not isinstance(binding["repository_full_name"], str) or not REPO_RE.fullmatch(binding["repository_full_name"]):
            _fail("project_binding.repository_full_name is malformed")
        _text(binding["default_branch"], "project_binding.default_branch", 255)
        version = binding["manifest_schema_version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            _fail("project_binding.manifest_schema_version must be a positive integer")
        _sha(binding["manifest_sha256"], "project_binding.manifest_sha256")
        _git_sha(binding["base_sha"], "project_binding.base_sha")
        if binding["repository_full_name"] != repo["name"] or binding["base_sha"] != repo["base_sha"]:
            _fail("project_binding repository or base SHA differs from the envelope repository")
        memory = _object(obj["memory_manifest"], "memory_manifest", {"version", "required_documents", "max_total_bytes"})
        memory_version = memory["version"]
        if isinstance(memory_version, bool) or not isinstance(memory_version, int) or memory_version < 1:
            _fail("memory_manifest.version must be a positive integer")
        required_documents = _strings(memory["required_documents"], "memory_manifest.required_documents", maximum=MAX_FILES)
        if not required_documents or required_documents != [item["path"] for item in project_documents]:
            _fail("memory_manifest.required_documents must exactly match the ordered project_context documents")
        memory_limit = memory["max_total_bytes"]
        if isinstance(memory_limit, bool) or not isinstance(memory_limit, int) or memory_limit < 1024:
            _fail("memory_manifest.max_total_bytes must be an integer of at least 1024")
        project_bytes = sum(len(item["content"].encode("utf-8")) for item in project_documents)
        if project_bytes > memory_limit:
            _fail("project_context exceeds memory_manifest.max_total_bytes")
    semantic = _object(obj["semantic_context"], "semantic_context",
                       {"status", "source_sha", "summary", "limitations"})
    _enum(semantic["status"], {"current", "stale", "unavailable"}, "semantic_context.status")
    if semantic["source_sha"] is not None:
        _git_sha(semantic["source_sha"], "semantic_context.source_sha")
    _text(semantic["summary"], "semantic_context.summary", 8_000, empty=True)
    _strings(semantic["limitations"], "semantic_context.limitations")

    constraints = _object(obj["constraints"], "constraints",
                          {"invariants", "prohibited_paths", "compatibility", "known_risks"})
    for key in ("invariants", "compatibility", "known_risks"):
        _strings(constraints[key], f"constraints.{key}")
    if not isinstance(constraints["prohibited_paths"], list) or len(constraints["prohibited_paths"]) > MAX_ITEMS:
        _fail("constraints.prohibited_paths must be a list")
    for item in constraints["prohibited_paths"]:
        _path(item, "constraints.prohibited_paths[]", pattern=True)
    _budget(obj["budgets"])
    profiles = _strings(obj["verification_profiles"], "verification_profiles", maximum=len(ALLOWED_PROFILES))
    if any(profile not in ALLOWED_PROFILES for profile in profiles):
        _fail("verification_profiles contains a profile outside the fixed allowlist")
    return obj


def validate_result(data: Any, envelope: dict) -> dict:
    validate_envelope(envelope)
    required = {
        "contract_version", "task_id", "provider", "model", "status", "summary",
        "plan", "assumptions", "changed_paths", "patch_ref", "tests_added_or_changed",
        "verification_requests", "risks", "handoff_notes", "usage", "context_fingerprints",
    }
    obj = _object(data, "agent result", required)
    if obj["contract_version"] != CONTRACT_VERSION or obj["task_id"] != envelope["task_id"]:
        _fail("result contract version or task_id does not match the envelope")
    _text(obj["provider"], "provider", 128)
    _text(obj["model"], "model", 256)
    _enum(obj["status"], ALLOWED_STATUSES, "result status")
    _text(obj["summary"], "summary", 8_000)
    _strings(obj["plan"], "plan", maximum=100)

    assumptions = _records(obj["assumptions"], "assumptions")
    for item in assumptions:
        _object(item, "assumption", {"text", "confidence"})
        _text(item["text"], "assumption.text", 2_000)
        _enum(item["confidence"], ALLOWED_ASSUMPTIONS, "assumption confidence")

    paths = obj["changed_paths"]
    if not isinstance(paths, list) or len(paths) > envelope["budgets"]["max_changed_files"]:
        _fail("changed_paths exceeds the declared file budget")
    normalized = [_path(path, "changed_paths[]") for path in paths]
    if len(set(normalized)) != len(normalized):
        _fail("changed_paths contains duplicates")
    scope = envelope["scope"]
    for path in normalized:
        if not any(_path_matches(path, pattern) for pattern in scope["allowed_paths"]):
            _fail(f"changed path is outside allowed scope: {path}")
        if any(_path_matches(path, pattern) for pattern in scope["excluded_paths"]):
            _fail(f"changed path is explicitly excluded: {path}")

    patch_ref = obj["patch_ref"]
    if patch_ref is not None:
        _text(patch_ref, "patch_ref", 100)
        if not PATCH_RE.fullmatch(patch_ref):
            _fail("patch_ref must be an opaque artifact:sha256:<digest> reference")
    if obj["status"] == "completed":
        if patch_ref is None:
            _fail("completed result requires a patch artifact reference")
        if not normalized:
            _fail("completed result must declare changed paths")
    elif patch_ref is not None or normalized:
        _fail("non-completed results cannot provide a patch or changed paths")

    tests = _records(obj["tests_added_or_changed"], "tests_added_or_changed")
    for item in tests:
        _object(item, "test entry", {"path", "purpose"})
        _path(item["path"], "test path")
        _text(item["purpose"], "test purpose", 2_000)

    requests = _records(obj["verification_requests"], "verification_requests")
    for item in requests:
        _object(item, "verification request", {"profile", "rationale"})
        profile = _enum(item["profile"], ALLOWED_PROFILES, "verification request profile")
        if profile not in envelope["verification_profiles"]:
            _fail("verification request is not in the task's fixed profile allowlist")
        _text(item["rationale"], "verification rationale", 2_000)

    _strings(obj["risks"], "risks")
    _text(obj["handoff_notes"], "handoff_notes", 8_000, empty=True)

    usage = _object(obj["usage"], "usage",
                    {"wall_seconds", "tokens", "tool_calls", "patch_bytes"})
    caps = {
        "wall_seconds": envelope["budgets"]["max_wall_seconds"],
        "tokens": envelope["budgets"]["max_tokens"],
        "tool_calls": envelope["budgets"]["max_tool_calls"],
        "patch_bytes": envelope["budgets"]["max_patch_bytes"],
    }
    for key, cap in caps.items():
        val = usage[key]
        if isinstance(val, bool) or not isinstance(val, int) or val < 0 or val > cap:
            _fail(f"usage.{key} exceeds its declared budget or is invalid")

    expected = {(item["path"], item["sha256"]) for item in envelope["project_context"] + envelope["source_context"]}
    echoed = _fingerprints(obj["context_fingerprints"], "context_fingerprints")
    actual = {(item["path"], item["sha256"]) for item in echoed}
    if actual != expected:
        _fail("context fingerprints are stale or do not exactly match the task envelope")
    return obj


def parse_json_object(raw: str | bytes, *, max_bytes: int = MAX_JSON_BYTES) -> dict:
    if isinstance(raw, bytes):
        if len(raw) > max_bytes:
            _fail("JSON payload exceeds size limit")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractValidationError("JSON payload must be UTF-8") from exc
    elif not isinstance(raw, str) or len(raw.encode("utf-8")) > max_bytes:
        _fail("JSON payload exceeds size limit or is not text")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_pairs)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractValidationError(f"malformed JSON: {exc}") from exc
    if not isinstance(value, dict):
        _fail("JSON root must be an object")
    return value
