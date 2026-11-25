"""Provider-neutral validation for versioned GitHub Issue agent tasks.

Version 1 is a narrowly bounded compatibility format for the original JET VPN
repository. Version 2 requires an explicit project binding; callers must compare
that binding with a trusted manifest and live GitHub repository metadata.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

MARKERS = {
    1: "<!-- jet-agent-task:v1 -->",
    2: "<!-- jet-agent-task:v2 -->",
}
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
REPOSITORY_ID_RE = re.compile(r"^[0-9]{1,20}$")
REPOSITORY_NAME_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$"
)
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
CAPABILITIES = {"implementation", "bug_fix", "refactor", "documentation", "investigation"}
RISKS = {"low", "medium", "high"}
AGENTS = {"any", "chatgpt", "grok"}
PROFILES = {"python-tooling-tests", "flutter-tests", "flutter-analysis", "lexical-memory-audit"}
MAX_BODY, MAX_GOAL, MAX_ITEMS = 32_000, 8_000, 50
PROTECTED_PARTS = {
    ".git", ".agent", ".secrets", "secrets", "credentials",
    "keystore", "signing", "release-assets",
}

# This tuple is a migration exception, not a project registry. It exists only
# to keep pre-v2 tasks working in the original JET VPN repository.
LEGACY_JET_VPN_IDENTITY = {
    "repository_id": "1349356614",
    "repository_full_name": "majidbusy09-blip/jetconfig-vpn",
    "default_branch": "main",
    "html_url": "https://github.com/majidbusy09-blip/jetconfig-vpn",
}


class GitHubTaskError(ValueError):
    """A GitHub task issue failed closed validation."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise GitHubTaskError("Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def _text(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise GitHubTaskError(f"{name} must be non-empty text of at most {limit} characters.")
    return value.strip()


def _paths(value: Any, name: str, *, required: bool, task_id: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS or (required and not value):
        raise GitHubTaskError(
            f"{name} must be {'a non-empty ' if required else 'an '}array of at most {MAX_ITEMS} paths."
        )
    result = []
    for raw in value:
        path = _text(raw, f"{name}[]", 256)
        if path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
            raise GitHubTaskError(f"{name} contains a non-repository-relative path.")
        parts = path.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise GitHubTaskError(f"{name} contains an unsafe path segment.")
        if any(part.lower() in PROTECTED_PARTS for part in parts):
            raise GitHubTaskError(f"{name} targets a protected path")
        if path.startswith(".github/workflows/") and not (
            path == WORKFLOW_POLICY_PATH and task_id == WORKFLOW_POLICY_TASK_ID
        ):
            raise GitHubTaskError(f"{name} targets a protected workflow path")
        if path in result:
            raise GitHubTaskError(f"{name} contains duplicate entries.")
        result.append(path)
    return result


def _repository_identity(repository_metadata: Any) -> dict[str, str]:
    if not isinstance(repository_metadata, dict):
        raise GitHubTaskError("Trusted GitHub repository metadata is required.")
    raw_id = repository_metadata.get("id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, (int, str)):
        raise GitHubTaskError("GitHub repository metadata has no immutable numeric ID.")
    repository_id = str(raw_id)
    full_name = repository_metadata.get("full_name")
    default_branch = repository_metadata.get("default_branch")
    html_url = repository_metadata.get("html_url")
    if not REPOSITORY_ID_RE.fullmatch(repository_id):
        raise GitHubTaskError("GitHub repository ID is malformed.")
    if not isinstance(full_name, str) or not REPOSITORY_NAME_RE.fullmatch(full_name):
        raise GitHubTaskError("GitHub canonical repository name is malformed.")
    if not isinstance(default_branch, str) or not default_branch.strip() or len(default_branch) > 255:
        raise GitHubTaskError("GitHub default branch is missing or malformed.")
    expected_url = "https://github.com/" + full_name
    if html_url != expected_url:
        raise GitHubTaskError("GitHub repository HTTPS URL is not canonical.")
    return {
        "repository_id": repository_id,
        "repository_full_name": full_name,
        "default_branch": default_branch,
        "html_url": html_url,
    }


def validate_legacy_jet_vpn_identity(repository_metadata: Any) -> dict[str, str]:
    """Accept v1 only when trusted metadata matches the one legacy JET VPN tuple."""
    identity = _repository_identity(repository_metadata)
    if identity != LEGACY_JET_VPN_IDENTITY:
        raise GitHubTaskError(
            "Legacy v1 tasks are accepted only for the explicitly configured JET VPN repository identity."
        )
    return identity


def _validate_project_binding(value: Any) -> dict[str, Any]:
    fields = {
        "project_id", "repository_id", "repository_full_name",
        "default_branch", "manifest_schema_version", "manifest_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise GitHubTaskError("v2 project_binding must contain exactly the documented identity fields.")
    project_id = _text(value["project_id"], "project_binding.project_id", 64)
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise GitHubTaskError("project_binding.project_id is malformed.")
    repository_id = _text(value["repository_id"], "project_binding.repository_id", 20)
    if not REPOSITORY_ID_RE.fullmatch(repository_id):
        raise GitHubTaskError("project_binding.repository_id must be an immutable numeric ID.")
    repository_full_name = _text(value["repository_full_name"], "project_binding.repository_full_name", 200)
    if not REPOSITORY_NAME_RE.fullmatch(repository_full_name):
        raise GitHubTaskError("project_binding.repository_full_name is malformed.")
    default_branch = _text(value["default_branch"], "project_binding.default_branch", 255)
    schema_version = value["manifest_schema_version"]
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version < 1:
        raise GitHubTaskError("project_binding.manifest_schema_version must be a positive integer.")
    digest = _text(value["manifest_sha256"], "project_binding.manifest_sha256", 64)
    if not DIGEST_RE.fullmatch(digest):
        raise GitHubTaskError("project_binding.manifest_sha256 must be a lowercase SHA-256 digest.")
    return {
        "project_id": project_id,
        "repository_id": repository_id,
        "repository_full_name": repository_full_name,
        "default_branch": default_branch,
        "manifest_schema_version": schema_version,
        "manifest_sha256": digest,
    }


def validate_task_payload(
    value: Any,
    *,
    repository_metadata: Any = None,
    allow_legacy_jet_vpn: bool = False,
) -> dict[str, Any]:
    common = {
        "task_id", "goal", "capability", "risk", "assigned_agent",
        "allow", "exclude", "scope_reason", "verification_profiles",
    }
    if not isinstance(value, dict):
        raise GitHubTaskError("Task payload must be a JSON object.")
    version = value.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version not in {1, 2}:
        raise GitHubTaskError("Unsupported GitHub task schema_version.")
    required = common | {"schema_version"}
    if version == 2:
        required.add("project_binding")
    if set(value) != required:
        raise GitHubTaskError("Task payload must contain exactly the documented fields.")
    if version == 1:
        if not allow_legacy_jet_vpn:
            raise GitHubTaskError("Legacy v1 task compatibility is disabled for this intake path.")
        validate_legacy_jet_vpn_identity(repository_metadata)

    task_id = _text(value["task_id"], "task_id", 64)
    if not TASK_ID_RE.fullmatch(task_id):
        raise GitHubTaskError("task_id must be 3-64 lowercase letters, digits, or hyphens.")
    for key, allowed in (
        ("capability", CAPABILITIES), ("risk", RISKS), ("assigned_agent", AGENTS)
    ):
        if not isinstance(value[key], str) or value[key] not in allowed:
            raise GitHubTaskError(f"Unsupported {key}.")
    profiles = value["verification_profiles"]
    if (
        not isinstance(profiles, list) or not profiles or len(profiles) > 12
        or not all(isinstance(item, str) and item in PROFILES for item in profiles)
    ):
        raise GitHubTaskError("verification_profiles must contain only supported fixed profiles.")
    if len(set(profiles)) != len(profiles):
        raise GitHubTaskError("verification_profiles must not contain duplicates.")

    result = {
        "schema_version": version,
        "task_id": task_id,
        "goal": _text(value["goal"], "goal", MAX_GOAL),
        "capability": value["capability"],
        "risk": value["risk"],
        "assigned_agent": value["assigned_agent"],
        "allow": _paths(value["allow"], "allow", required=True, task_id=task_id),
        "exclude": _paths(value["exclude"], "exclude", required=False, task_id=task_id),
        "scope_reason": _text(value["scope_reason"], "scope_reason", 2_000),
        "verification_profiles": profiles,
    }
    if version == 2:
        result["project_binding"] = _validate_project_binding(value["project_binding"])
    return result


def validate_issue_body(
    body: str,
    *,
    repository_metadata: Any = None,
    allow_legacy_jet_vpn: bool = False,
) -> dict[str, Any]:
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BODY:
        raise GitHubTaskError("Issue body is missing or exceeds the configured size limit.")
    found = [(version, marker) for version, marker in MARKERS.items() if marker in body]
    if len(found) != 1 or body.count(found[0][1]) != 1:
        raise GitHubTaskError("Issue body must contain exactly one versioned GitHub task marker.")
    marker_version, marker = found[0]
    marked = body.split(marker, 1)[1]
    fence = re.escape(chr(96) * 3)
    blocks = re.findall(fence + r"json\s*\n(.*?)\n" + fence, marked, flags=re.DOTALL | re.IGNORECASE)
    if len(blocks) != 1:
        raise GitHubTaskError("Issue body must contain exactly one fenced JSON task payload after the marker.")
    try:
        payload = json.loads(blocks[0], object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, GitHubTaskError) as exc:
        raise GitHubTaskError("Issue task payload is not valid unique-key JSON.") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != marker_version:
        raise GitHubTaskError("Task marker version does not match the payload schema_version.")
    return validate_task_payload(
        payload,
        repository_metadata=repository_metadata,
        allow_legacy_jet_vpn=allow_legacy_jet_vpn,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, help="UTF-8 file containing the GitHub Issue body.")
    parser.add_argument("--repository-metadata-file", help="Trusted repository metadata JSON for legacy v1 validation.")
    parser.add_argument("--allow-legacy-jet-vpn", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.body_file, "r", encoding="utf-8") as handle:
            body = handle.read()
        metadata = None
        if args.repository_metadata_file:
            with open(args.repository_metadata_file, "r", encoding="utf-8") as handle:
                metadata = json.load(handle, object_pairs_hook=_unique_object)
        result = validate_issue_body(
            body, repository_metadata=metadata,
            allow_legacy_jet_vpn=args.allow_legacy_jet_vpn,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, GitHubTaskError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
