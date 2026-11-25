"""Pure project-scoped namespace derivation for leases and workspaces."""
from __future__ import annotations

import hashlib
import re
from typing import Any

TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")
REPOSITORY_ID_RE = re.compile(r"^[0-9]{1,20}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
PROJECT_BINDING_FIELDS = {
    "project_id", "repository_id", "repository_full_name", "default_branch",
    "manifest_schema_version", "manifest_sha256",
}


class ProjectNamespaceError(ValueError):
    """Project identity cannot be used for a deterministic namespace."""


def validate_project_binding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != PROJECT_BINDING_FIELDS:
        raise ProjectNamespaceError("Project binding must contain exactly the documented identity fields.")
    if not isinstance(value["project_id"], str) or not PROJECT_ID_RE.fullmatch(value["project_id"]):
        raise ProjectNamespaceError("Invalid project_id.")
    if not isinstance(value["repository_id"], str) or not REPOSITORY_ID_RE.fullmatch(value["repository_id"]):
        raise ProjectNamespaceError("Invalid immutable repository_id.")
    if not isinstance(value["repository_full_name"], str) or not REPOSITORY_RE.fullmatch(value["repository_full_name"]):
        raise ProjectNamespaceError("Invalid canonical repository_full_name.")
    branch = value["default_branch"]
    if not isinstance(branch, str) or not branch or len(branch) > 255 or branch.startswith("/") or ".." in branch.split("/"):
        raise ProjectNamespaceError("Invalid configured default_branch.")
    version = value["manifest_schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ProjectNamespaceError("manifest_schema_version must be a positive integer.")
    if not isinstance(value["manifest_sha256"], str) or not SHA_RE.fullmatch(value["manifest_sha256"]):
        raise ProjectNamespaceError("manifest_sha256 must be a full lowercase SHA-256 digest.")
    return dict(value)


def namespace_key(project_binding: Any) -> str:
    binding = validate_project_binding(project_binding)
    return binding["project_id"] + "/" + binding["repository_id"]


def lease_branch(task_id: str, project_binding: Any = None) -> str:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise ProjectNamespaceError("Invalid task_id.")
    if project_binding is None:
        return "agent-locks/" + task_id
    return "agent-locks/projects/" + namespace_key(project_binding) + "/" + task_id


def lease_record_path(task_id: str, project_binding: Any = None) -> str:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise ProjectNamespaceError("Invalid task_id.")
    if project_binding is None:
        return ".agent-locks/lease.json"
    return ".agent-locks/projects/" + namespace_key(project_binding) + "/" + task_id + ".json"


def workspace_id(task_id: str, base_sha: str, project_binding: Any = None) -> str:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise ProjectNamespaceError("Invalid task_id.")
    if not isinstance(base_sha, str) or not GIT_SHA_RE.fullmatch(base_sha):
        raise ProjectNamespaceError("Invalid pinned base SHA.")
    if project_binding is None:
        material = task_id + ":" + base_sha
    else:
        binding = validate_project_binding(project_binding)
        material = ":".join((
            binding["project_id"], binding["repository_id"],
            binding["manifest_sha256"], task_id, base_sha,
        ))
    return "workspace_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
