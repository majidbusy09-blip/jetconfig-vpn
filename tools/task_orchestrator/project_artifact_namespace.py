"""Deterministic project-scoped paths and identities for generated artifacts.

V1 callers intentionally retain their historical paths and identifiers. V2
callers must provide a validated project binding and exact pinned source SHA.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from .project_namespace import (
        PROJECT_BINDING_FIELDS,
        ProjectNamespaceError,
        validate_project_binding,
    )
except ImportError:
    from project_namespace import (
        PROJECT_BINDING_FIELDS,
        ProjectNamespaceError,
        validate_project_binding,
    )

GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
CATEGORY_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
ARTIFACT_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LEGACY_INDEX_PATHS = {
    "resolved": "docs/generated/jet_vpn_resolved_index.json",
    "critical_paths": "docs/generated/jet_vpn_critical_paths.json",
    "semantic": "docs/generated/jet_vpn_semantic_index.json",
}


class ProjectArtifactNamespaceError(ValueError):
    """A generated artifact identity or path is missing, unsafe, or inconsistent."""


def _identity(project_binding: Any, source_revision: str) -> dict[str, Any]:
    if not isinstance(project_binding, dict):
        raise ProjectArtifactNamespaceError("A project binding object is required.")
    allowed = PROJECT_BINDING_FIELDS | {"base_sha"}
    if frozenset(project_binding) not in {frozenset(PROJECT_BINDING_FIELDS), frozenset(allowed)}:
        raise ProjectArtifactNamespaceError("Project binding has unexpected or missing identity fields.")
    if not isinstance(source_revision, str) or not GIT_SHA_RE.fullmatch(source_revision):
        raise ProjectArtifactNamespaceError("Pinned source revision must be a full lowercase Git SHA.")
    if "base_sha" in project_binding and project_binding["base_sha"] != source_revision:
        raise ProjectArtifactNamespaceError("Project binding base_sha differs from the pinned source revision.")
    identity = {key: value for key, value in project_binding.items() if key != "base_sha"}
    try:
        return validate_project_binding(identity)
    except ProjectNamespaceError as exc:
        raise ProjectArtifactNamespaceError(str(exc)) from exc


def namespace_segments(project_binding: Any, source_revision: str) -> tuple[str, ...]:
    """Return stable path segments bound to project, repo, manifest, and source."""
    identity = _identity(project_binding, source_revision)
    return (
        identity["project_id"],
        identity["repository_id"],
        identity["manifest_sha256"],
        source_revision,
    )


def _safe_relative(value: str, label: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise ProjectArtifactNamespaceError(f"{label} must be a non-empty relative POSIX path.")
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ProjectArtifactNamespaceError(f"{label} contains an unsafe path segment.")
    if any(part.startswith(".") for part in parts):
        raise ProjectArtifactNamespaceError(f"{label} may not contain hidden path segments.")
    return tuple(parts)


def namespaced_relative_path(
    category: str,
    relative_path: str,
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> str:
    """Build a deterministic repository-relative output path.

    Passing no project binding returns the exact legacy relative path.
    """
    if project_binding is None:
        if source_revision is not None:
            raise ProjectArtifactNamespaceError("A source revision cannot be supplied without a project binding.")
        return PurePosixPath(*_safe_relative(relative_path, "Artifact relative path")).as_posix()
    if not isinstance(category, str) or not CATEGORY_RE.fullmatch(category):
        raise ProjectArtifactNamespaceError("Artifact category is invalid.")
    if source_revision is None:
        raise ProjectArtifactNamespaceError("A project-scoped artifact requires a pinned source revision.")
    parts = namespace_segments(project_binding, source_revision)
    tail = _safe_relative(relative_path, "Artifact relative path")
    return PurePosixPath("docs/generated/projects", *parts, category, *tail).as_posix()


def index_output_paths(
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> dict[str, str]:
    """Return all index outputs; v1 paths remain byte-for-byte stable."""
    if project_binding is None:
        if source_revision is not None:
            raise ProjectArtifactNamespaceError("A source revision cannot be supplied without a project binding.")
        return dict(LEGACY_INDEX_PATHS)
    return {
        key: namespaced_relative_path(
            "indexes", filename,
            project_binding=project_binding,
            source_revision=source_revision,
        )
        for key, filename in {
            "resolved": "resolved_index.json",
            "critical_paths": "critical_paths.json",
            "semantic": "semantic_index.json",
        }.items()
    }


def cache_relative_path(
    cache_name: str,
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> str:
    """Return the exact legacy cache name or a source-bound v2 cache path."""
    if not isinstance(cache_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", cache_name):
        raise ProjectArtifactNamespaceError("Cache name is invalid.")
    return namespaced_relative_path("cache", cache_name, project_binding=project_binding, source_revision=source_revision)


def audit_record_path(
    record_name: str,
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> str:
    """Return a project/source-bound audit record path."""
    return namespaced_relative_path("audit", record_name, project_binding=project_binding, source_revision=source_revision)


def cache_key(
    cache_name: str,
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> str:
    """Return the legacy key unchanged or a collision-resistant v2 cache key."""
    if not isinstance(cache_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", cache_name):
        raise ProjectArtifactNamespaceError("Cache name is invalid.")
    if project_binding is None:
        if source_revision is not None:
            raise ProjectArtifactNamespaceError("A source revision cannot be supplied without a project binding.")
        return cache_name
    identity = _identity(project_binding, source_revision or "")
    material = {
        "project_id": identity["project_id"],
        "repository_id": identity["repository_id"],
        "manifest_sha256": identity["manifest_sha256"],
        "source_revision": source_revision,
        "cache_name": cache_name,
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "v2:" + hashlib.sha256(canonical).hexdigest()


def workflow_artifact_name(
    prefix: str,
    *,
    project_binding: dict[str, Any] | None = None,
    source_revision: str | None = None,
) -> str:
    """Create a future workflow artifact name; v1 names are unchanged."""
    if not isinstance(prefix, str) or not ARTIFACT_PREFIX_RE.fullmatch(prefix):
        raise ProjectArtifactNamespaceError("Workflow artifact prefix is invalid.")
    if project_binding is None:
        if source_revision is not None:
            raise ProjectArtifactNamespaceError("A source revision cannot be supplied without a project binding.")
        return prefix
    identity = _identity(project_binding, source_revision or "")
    name = "-".join((
        prefix,
        identity["project_id"],
        identity["repository_id"],
        identity["manifest_sha256"],
        source_revision,
    ))
    if len(name) > 256:
        raise ProjectArtifactNamespaceError("Workflow artifact name exceeds the 256-character platform limit.")
    return name


def ensure_namespace_directory(
    root: str | os.PathLike[str],
    category: str,
    *,
    project_binding: dict[str, Any],
    source_revision: str,
    relative_directory: str | None = None,
) -> Path:
    """Create and verify a project-scoped directory without following symlinks."""
    if not isinstance(category, str) or not CATEGORY_RE.fullmatch(category):
        raise ProjectArtifactNamespaceError("Artifact category is invalid.")
    supplied = Path(root)
    if supplied.is_symlink() or not supplied.is_dir():
        raise ProjectArtifactNamespaceError("Artifact root must be an existing regular directory.")
    resolved_root = supplied.resolve(strict=True)
    segments = ("projects",) + namespace_segments(project_binding, source_revision) + (category,)
    if relative_directory is not None:
        segments += _safe_relative(relative_directory, "Artifact namespace subdirectory")
    current = resolved_root
    for segment in segments:
        current = current / segment
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise ProjectArtifactNamespaceError("Could not create the project artifact namespace safely.") from exc
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise ProjectArtifactNamespaceError("Project artifact namespace cannot be inspected.") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ProjectArtifactNamespaceError("Project artifact namespace contains a symlink or non-directory.")
        try:
            current.resolve(strict=True).relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise ProjectArtifactNamespaceError("Project artifact namespace escaped its root.") from exc
    return current


def verify_store_namespace(
    store_binding: dict[str, Any] | None,
    store_revision: str | None,
    project_binding: dict[str, Any] | None,
    source_revision: str,
) -> None:
    """Fail closed when a reader is handed a store for another task/project."""
    if project_binding is None:
        if store_binding is not None or store_revision is not None:
            raise ProjectArtifactNamespaceError("A legacy task cannot read a project-scoped artifact store.")
        return
    if store_binding is None or store_revision is None:
        raise ProjectArtifactNamespaceError("A project-scoped task requires a project-scoped artifact store.")
    expected = namespace_segments(project_binding, source_revision)
    actual = namespace_segments(store_binding, store_revision)
    if actual != expected:
        raise ProjectArtifactNamespaceError("Artifact store namespace differs from the task project or source revision.")
