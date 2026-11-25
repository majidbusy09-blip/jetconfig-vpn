"""Deterministic, local-only builder for bounded coding-agent context packages."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import PurePosixPath
from typing import Any

MAX_CONTEXT_FILE_BYTES = 256_000
MAX_CONTEXT_TOTAL_BYTES = 512_000
MAX_CONTEXT_FILES = 100
REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
PROTECTED_PARTS = {".git", ".agent", ".secrets", "secrets", "credentials", "keystore", "signing", "release-assets"}
PROTECTED_NAMES = {".env", ".env.local", ".env.production", ".npmrc", ".pypirc", "key.properties", "upload-keystore.jks", "release.keystore", "google-services.json", "credentials.json", "id_rsa", "id_ed25519"}
PROTECTED_SUFFIXES = {".pem", ".p12", ".pfx", ".jks", ".keystore", ".mobileprovision"}


class ContextBuildError(ValueError):
    """Context construction failed a fail-closed validation rule."""


def _safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ContextBuildError("Context paths must be non-empty repository-relative paths.")
    if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise ContextBuildError(f"Unsafe context path: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ContextBuildError(f"Unsafe path segment in context path: {value!r}")
    if any(part.lower() in PROTECTED_PARTS for part in parts):
        raise ContextBuildError(f"Protected path cannot enter agent context: {value}")
    filename = PurePosixPath(value).name.lower()
    if filename in PROTECTED_NAMES or filename.startswith(".env") or PurePosixPath(filename).suffix in PROTECTED_SUFFIXES:
        raise ContextBuildError(f"Protected file cannot enter agent context: {value}")
    if any(ord(char) < 32 for char in value):
        raise ContextBuildError("Control characters are not allowed in context paths.")
    return PurePosixPath(value).as_posix()


def _git(root, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False, shell=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ContextBuildError(f"Git could not read pinned context ({detail or 'unknown error'}).")
    return result.stdout


def _read_pinned_blob(root, revision: str, relative: str) -> bytes:
    listing = _git(root, "ls-tree", "-z", revision, "--", f":(literal){relative}")
    entries = [item for item in listing.split(b"\0") if item]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ContextBuildError(f"Context file is missing at pinned revision: {relative}")
    metadata, returned_path = entries[0].split(b"\t", 1)
    fields = metadata.decode("ascii", errors="strict").split()
    if len(fields) != 3 or returned_path.decode("utf-8", errors="strict") != relative:
        raise ContextBuildError(f"Git returned an unexpected tree entry for: {relative}")
    mode, object_type, object_sha = fields
    if mode not in {"100644", "100755"} or object_type != "blob":
        raise ContextBuildError(f"Context file must be a regular tracked file; symlinks and submodules are blocked: {relative}")
    raw = _git(root, "cat-file", "blob", object_sha)
    if len(raw) > MAX_CONTEXT_FILE_BYTES:
        raise ContextBuildError(f"Context file exceeds {MAX_CONTEXT_FILE_BYTES} bytes: {relative}")
    try:
        content = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ContextBuildError(f"Context file is not valid UTF-8 text: {relative}") from exc
    if "\x00" in content:
        raise ContextBuildError(f"Context file contains a NUL byte: {relative}")
    return raw


def _document(root, revision: str, relative: str) -> dict[str, str]:
    raw = _read_pinned_blob(root, revision, relative)
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "content": raw.decode("utf-8")}


def build_context(*, root, task_id: str, source_revision: str, required_paths: list[str],
                  source_paths: list[str], allowed_patterns: list[str],
                  excluded_patterns: list[str], project_binding: dict[str, Any] | None = None,
                  memory_manifest_version: int | None = None,
                  memory_manifest_max_total_bytes: int | None = None) -> dict[str, Any]:
    if not REVISION_RE.fullmatch(source_revision or ""):
        raise ContextBuildError("Source revision must be a full Git commit SHA.")
    if not task_id or len(task_id) > 64:
        raise ContextBuildError("Task ID is invalid.")
    project_paths = [_safe_path(item) for item in required_paths]
    selected_paths = [_safe_path(item) for item in source_paths]
    if len(set(project_paths)) != len(project_paths) or len(set(selected_paths)) != len(selected_paths):
        raise ContextBuildError("Context paths must not contain duplicates.")
    if len(project_paths) + len(selected_paths) > MAX_CONTEXT_FILES:
        raise ContextBuildError(f"Context package cannot contain more than {MAX_CONTEXT_FILES} files.")
    overlap = set(project_paths) & set(selected_paths)
    if overlap:
        raise ContextBuildError("Path cannot be both project and source context: " + ", ".join(sorted(overlap)))
    for relative in selected_paths:
        if any(fnmatch.fnmatchcase(relative, pattern) for pattern in excluded_patterns):
            raise ContextBuildError(f"Explicit source context is excluded by task scope: {relative}")
        if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in allowed_patterns):
            raise ContextBuildError(f"Explicit source context is outside task allowlist: {relative}")
    project_documents = [_document(root, source_revision, item) for item in project_paths]
    source_documents = [_document(root, source_revision, item) for item in selected_paths]
    total_bytes = sum(len(item["content"].encode("utf-8")) for item in project_documents + source_documents)
    if total_bytes > MAX_CONTEXT_TOTAL_BYTES:
        raise ContextBuildError(f"Combined context exceeds {MAX_CONTEXT_TOTAL_BYTES} bytes ({total_bytes} selected); narrow --context. No content was truncated.")
    if project_binding is None:
        if memory_manifest_version is not None or memory_manifest_max_total_bytes is not None:
            raise ContextBuildError("Memory manifest metadata requires a validated project binding.")
        package: dict[str, Any] = {
            "schema_version": 1, "task_id": task_id, "source_revision": source_revision,
            "project_context": project_documents, "source_context": source_documents,
            "total_bytes": total_bytes,
        }
    else:
        expected_binding_fields = {
            "project_id", "repository_id", "repository_full_name", "default_branch",
            "manifest_schema_version", "manifest_sha256", "base_sha",
        }
        if not isinstance(project_binding, dict) or set(project_binding) != expected_binding_fields:
            raise ContextBuildError("Project context binding is malformed.")
        if (not isinstance(project_binding.get("project_id"), str)
                or not re.fullmatch(r"[a-z][a-z0-9-]*[a-z0-9]", project_binding["project_id"])
                or not isinstance(project_binding.get("repository_id"), str)
                or not re.fullmatch(r"[0-9]{1,20}", project_binding["repository_id"])
                or not isinstance(project_binding.get("repository_full_name"), str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", project_binding["repository_full_name"])
                or not isinstance(project_binding.get("default_branch"), str)
                or not project_binding["default_branch"].strip()
                or isinstance(project_binding.get("manifest_schema_version"), bool)
                or not isinstance(project_binding.get("manifest_schema_version"), int)
                or project_binding["manifest_schema_version"] < 1
                or not isinstance(project_binding.get("manifest_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", project_binding["manifest_sha256"])
                or project_binding.get("base_sha") != source_revision):
            raise ContextBuildError("Project context binding does not match the pinned source revision or valid identity fields.")
        if (isinstance(memory_manifest_version, bool) or not isinstance(memory_manifest_version, int)
                or memory_manifest_version < 1 or not project_paths
                or isinstance(memory_manifest_max_total_bytes, bool)
                or not isinstance(memory_manifest_max_total_bytes, int)
                or memory_manifest_max_total_bytes < 1024):
            raise ContextBuildError("A project context requires a valid memory manifest version, byte limit, and required documents.")
        project_memory_bytes = sum(len(item["content"].encode("utf-8")) for item in project_documents)
        if project_memory_bytes > memory_manifest_max_total_bytes:
            raise ContextBuildError("Project memory documents exceed the manifest's max_total_bytes limit.")
        package = {
            "schema_version": 2, "task_id": task_id, "source_revision": source_revision,
            "project_binding": dict(project_binding),
            "memory_manifest": {"version": memory_manifest_version, "required_documents": project_paths,
                                "max_total_bytes": memory_manifest_max_total_bytes},
            "project_context": project_documents, "source_context": source_documents,
            "total_bytes": total_bytes,
        }
    canonical = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package["context_sha256"] = hashlib.sha256(canonical).hexdigest()
    return package
