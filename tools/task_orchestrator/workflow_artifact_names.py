"""Resolve trusted, source-bound GitHub Actions artifact names.

This module reads declarative manifests only. It never executes project code or
performs network access. A missing manifest preserves the legacy v1 names;
an ambiguous or invalid matching manifest fails closed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from .github_issue_intake import (
        AVAILABLE_PROFILES, IntakeError, load_project_configuration,
    )
    from .project_artifact_namespace import (
        ProjectArtifactNamespaceError,
        index_output_paths,
        workflow_artifact_name,
    )
    from .project_registry import (
        ProjectRegistryError, loads_unique_json, validate_project_manifest,
    )
except ImportError:
    from github_issue_intake import (
        AVAILABLE_PROFILES, IntakeError, load_project_configuration,
    )
    from project_artifact_namespace import (
        ProjectArtifactNamespaceError, index_output_paths, workflow_artifact_name,
    )
    from project_registry import (
        ProjectRegistryError, loads_unique_json, validate_project_manifest,
    )

LEGACY_SEMANTIC_AST_NAME = "jet-vpn-semantic-ast-index"
LEGACY_CODE_INDEX_NAME = "jet-vpn-code-index"
GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$"
)


class WorkflowArtifactNameError(ValueError):
    """Trusted project identity or source revision could not be established."""


def resolve_artifact_names(
    root: str | os.PathLike[str],
    *,
    repository_metadata: dict[str, Any],
    expected_source_revision: str,
    checked_out_revision: str,
) -> dict[str, str]:
    """Return v1-compatible names or names bound to one validated project."""
    if not isinstance(repository_metadata, dict):
        raise WorkflowArtifactNameError("Live repository metadata must be an object.")
    repository_id = repository_metadata.get("id")
    full_name = repository_metadata.get("full_name")
    default_branch = repository_metadata.get("default_branch")
    html_url = repository_metadata.get("html_url")
    if (isinstance(repository_id, bool) or not isinstance(repository_id, int)
            or repository_id < 1):
        raise WorkflowArtifactNameError("Live immutable repository ID is invalid.")
    if not isinstance(full_name, str) or not REPOSITORY_RE.fullmatch(full_name):
        raise WorkflowArtifactNameError("Live canonical repository name is invalid.")
    if not isinstance(default_branch, str) or not default_branch or len(default_branch) > 255:
        raise WorkflowArtifactNameError("Live default branch is invalid.")
    if html_url != "https://github.com/" + full_name:
        raise WorkflowArtifactNameError("Live repository URL is not canonical.")
    if (not isinstance(expected_source_revision, str)
            or not GIT_SHA_RE.fullmatch(expected_source_revision)
            or not isinstance(checked_out_revision, str)
            or not GIT_SHA_RE.fullmatch(checked_out_revision)):
        raise WorkflowArtifactNameError("Expected and checked-out source revisions must be full Git SHAs.")
    if expected_source_revision != checked_out_revision:
        raise WorkflowArtifactNameError("Checked-out source revision differs from the GitHub event SHA.")

    try:
        schema, manifests = load_project_configuration(Path(root))
    except (IntakeError, OSError, UnicodeError) as exc:
        raise WorkflowArtifactNameError("Trusted project manifest inventory is invalid.") from exc

    repository_id_text = str(repository_id)
    candidates = []
    for manifest in manifests:
        repository = manifest.get("repository")
        if not isinstance(repository, dict):
            raise WorkflowArtifactNameError("A trusted manifest has malformed repository metadata.")
        manifest_full_name = repository.get("full_name")
        if (repository.get("repository_id") == repository_id_text
                or (isinstance(manifest_full_name, str)
                    and manifest_full_name.casefold() == full_name.casefold())):
            candidates.append(manifest)

    if not candidates:
        paths = index_output_paths()
        return {
            "semantic_ast": LEGACY_SEMANTIC_AST_NAME,
            "code_index": LEGACY_CODE_INDEX_NAME,
            "identity_mode": "v1",
            "project_manifest": "",
            "resolved_index": paths["resolved"],
            "critical_paths": paths["critical_paths"],
        }
    if len(candidates) != 1:
        raise WorkflowArtifactNameError("More than one trusted manifest matches this repository identity.")

    manifest = candidates[0]
    try:
        validated = validate_project_manifest(
            manifest,
            schema=schema,
            repository_metadata=repository_metadata,
            existing_manifests=[item for item in manifests if item is not manifest],
            available_profiles=AVAILABLE_PROFILES,
        )
        if validated["lifecycle"] == "retired":
            raise ProjectRegistryError("Retired projects cannot publish workflow artifacts.")
        binding = {
            "project_id": validated["project_id"],
            "repository_id": str(validated["repository_id"]),
            "repository_full_name": full_name,
            "default_branch": default_branch,
            "manifest_schema_version": manifest["schema_version"],
            "manifest_sha256": validated["manifest_sha256"],
        }
        trusted_root = Path(root).resolve(strict=True)
        manifest_parts = ("docs", "projects", validated["project_id"], "manifest.json")
        project_manifest = trusted_root.joinpath(*manifest_parts)
        cursor = trusted_root
        unsafe_component = False
        for part in manifest_parts:
            cursor = cursor / part
            if cursor.is_symlink():
                unsafe_component = True
                break
        if unsafe_component or not project_manifest.is_file():
            raise WorkflowArtifactNameError("Matching trusted manifest has no safe project-id path.")
        try:
            manifest_at_path = loads_unique_json(project_manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProjectRegistryError) as exc:
            raise WorkflowArtifactNameError("Matching trusted manifest path is unreadable.") from exc
        if manifest_at_path != manifest:
            raise WorkflowArtifactNameError("Project-id manifest path differs from the validated manifest.")
        paths = index_output_paths(
            project_binding=binding,
            source_revision=checked_out_revision,
        )
        semantic_name = workflow_artifact_name(
            "jet-vpn-semantic-ast-index",
            project_binding=binding,
            source_revision=checked_out_revision,
        )
        code_name = workflow_artifact_name(
            "jet-vpn-code-index",
            project_binding=binding,
            source_revision=checked_out_revision,
        )
    except (ProjectRegistryError, ProjectArtifactNamespaceError, KeyError, TypeError) as exc:
        raise WorkflowArtifactNameError("Matching trusted manifest failed repository or namespace validation.") from exc

    return {
        "semantic_ast": semantic_name,
        "code_index": code_name,
        "identity_mode": "v2",
        "project_manifest": project_manifest.relative_to(trusted_root).as_posix(),
        "resolved_index": paths["resolved"],
        "critical_paths": paths["critical_paths"],
    }


def write_github_output(output_path: str | os.PathLike[str], names: dict[str, str]) -> None:
    """Append a fixed set of validated single-line outputs to the runner file."""
    expected = {
        "semantic_ast", "code_index", "identity_mode", "project_manifest",
        "resolved_index", "critical_paths",
    }
    if not isinstance(names, dict) or set(names) != expected:
        raise WorkflowArtifactNameError("Artifact output fields are malformed.")
    string_fields = expected - {"identity_mode"}
    if (names["identity_mode"] not in {"v1", "v2"}
            or not all(isinstance(names[key], str)
                       and "\n" not in names[key] and "\r" not in names[key]
                       for key in string_fields)
            or not all(names[key] for key in string_fields - {"project_manifest"})
            or (names["identity_mode"] == "v1" and names["project_manifest"])
            or (names["identity_mode"] == "v2" and not names["project_manifest"])):
        raise WorkflowArtifactNameError("Artifact output values are unsafe.")
    if names["identity_mode"] == "v1":
        if (names["semantic_ast"] != LEGACY_SEMANTIC_AST_NAME
                or names["code_index"] != LEGACY_CODE_INDEX_NAME
                or names["resolved_index"] != "docs/generated/jet_vpn_resolved_index.json"
                or names["critical_paths"] != "docs/generated/jet_vpn_critical_paths.json"):
            raise WorkflowArtifactNameError("Legacy artifact output must use the exact compatibility names and paths.")
    else:
        manifest_match = re.fullmatch(
            r"docs/projects/([a-z][a-z0-9-]*[a-z0-9])/manifest\.json",
            names["project_manifest"],
        )
        resolved_match = re.fullmatch(
            r"docs/generated/projects/([a-z][a-z0-9-]*[a-z0-9])/([0-9]{1,20})/"
            r"([0-9a-f]{64})/((?:[0-9a-f]{40}|[0-9a-f]{64}))/indexes/resolved_index\.json",
            names["resolved_index"],
        )
        critical_match = re.fullmatch(
            r"docs/generated/projects/([a-z][a-z0-9-]*[a-z0-9])/([0-9]{1,20})/"
            r"([0-9a-f]{64})/((?:[0-9a-f]{40}|[0-9a-f]{64}))/indexes/critical_paths\.json",
            names["critical_paths"],
        )
        if (manifest_match is None or resolved_match is None or critical_match is None
                or resolved_match.groups() != critical_match.groups()
                or manifest_match.group(1) != resolved_match.group(1)):
            raise WorkflowArtifactNameError("Project artifact paths do not share one valid identity namespace.")
        suffix = "-".join(resolved_match.groups())
        expected_semantic = re.fullmatch(
            r"jet-vpn-semantic-ast-index-" + re.escape(suffix), names["semantic_ast"],
        )
        expected_code = re.fullmatch(
            r"jet-vpn-code-index-" + re.escape(suffix), names["code_index"],
        )
        if expected_semantic is None or expected_code is None:
            raise WorkflowArtifactNameError("Project artifact names differ from their content paths.")
    path = Path(output_path)
    try:
        if path.is_symlink() or not path.is_file():
            raise WorkflowArtifactNameError("GitHub output target must be an existing regular file.")
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(
                "semantic_ast=" + names["semantic_ast"] + "\n"
                + "code_index=" + names["code_index"] + "\n"
                + "identity_mode=" + names["identity_mode"] + "\n"
                + "project_manifest=" + names["project_manifest"] + "\n"
                + "resolved_index=" + names["resolved_index"] + "\n"
                + "critical_paths=" + names["critical_paths"] + "\n"
            )
    except WorkflowArtifactNameError:
        raise
    except OSError as exc:
        raise WorkflowArtifactNameError("Could not safely write GitHub Actions outputs.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT"))
    args = parser.parse_args(argv)
    try:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        repository_id = int(os.environ.get("GITHUB_REPOSITORY_ID", ""))
        default_branch = os.environ.get("GITHUB_REPOSITORY_DEFAULT_BRANCH", "")
        expected_sha = os.environ.get("GITHUB_SHA", "")
        if not args.output:
            raise WorkflowArtifactNameError("GITHUB_OUTPUT is required.")
        if not REPOSITORY_RE.fullmatch(repository):
            raise WorkflowArtifactNameError("GITHUB_REPOSITORY is missing or invalid.")
        checked_out_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(args.root),
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        ).stdout.strip()
        names = resolve_artifact_names(
            args.root,
            repository_metadata={
                "id": repository_id,
                "full_name": repository,
                "html_url": "https://github.com/" + repository,
                "default_branch": default_branch,
            },
            expected_source_revision=expected_sha,
            checked_out_revision=checked_out_sha,
        )
        write_github_output(args.output, names)
    except (WorkflowArtifactNameError, OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps(names, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
