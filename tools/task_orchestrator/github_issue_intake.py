"""Convert a GitHub Issues event into a validated, provider-neutral task artifact.

This is an intake bridge only: it never claims a lease, invokes a model, runs
commands, edits repository files, or dispatches an implementation agent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .github_task_protocol import GitHubTaskError, validate_issue_body
    from .project_registry import (
        ProjectRegistryError,
        ensure_implementation_eligible,
        loads_unique_json,
        validate_project_manifest,
    )
except ImportError:
    from github_task_protocol import GitHubTaskError, validate_issue_body
    from project_registry import (
        ProjectRegistryError,
        ensure_implementation_eligible,
        loads_unique_json,
        validate_project_manifest,
    )

INTAKE_SCHEMA = 2
TASK_LABEL = "agent-task"
AVAILABLE_PROFILES = frozenset({
    "python-tooling-tests", "flutter-analysis", "flutter-tests", "lexical-memory-audit",
})


class IntakeError(ValueError):
    """An Issues event is not eligible for task intake."""


def load_project_configuration(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load only bounded, checked-in declarative manifests from the trusted checkout."""
    schema_path = root / "docs" / "PROJECT_MANIFEST_SCHEMA.json"
    if schema_path.is_symlink() or not schema_path.is_file() or schema_path.stat().st_size > 512_000:
        raise IntakeError("Trusted project manifest schema is missing or unsafe.")
    try:
        schema = loads_unique_json(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ProjectRegistryError) as exc:
        raise IntakeError("Trusted project manifest schema is unreadable.") from exc
    if not isinstance(schema, dict):
        raise IntakeError("Trusted project manifest schema must be an object.")

    directory = root / "docs" / "projects"
    if directory.is_symlink():
        raise IntakeError("Trusted project manifest directory must not be a symlink.")
    if not directory.exists():
        return schema, []
    if not directory.is_dir():
        raise IntakeError("Trusted project manifest path is not a directory.")

    manifests = []
    for project_dir in sorted(directory.iterdir(), key=lambda item: item.name):
        if project_dir.is_symlink() or not project_dir.is_dir():
            raise IntakeError("Trusted project manifest entries must be regular directories.")
        path = project_dir / "manifest.json"
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 256_000:
            raise IntakeError("Trusted project manifest must be a bounded regular file.")
        try:
            manifest = loads_unique_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProjectRegistryError) as exc:
            raise IntakeError("A trusted project manifest is unreadable.") from exc
        if not isinstance(manifest, dict):
            raise IntakeError("Every trusted project manifest must be a JSON object.")
        manifests.append(manifest)

    project_ids = [item.get("project_id") for item in manifests]
    repository_ids = [
        item.get("repository", {}).get("repository_id")
        if isinstance(item.get("repository"), dict) else None
        for item in manifests
    ]
    if len(project_ids) != len(set(project_ids)) or len(repository_ids) != len(set(repository_ids)):
        raise IntakeError("Trusted project manifests contain duplicate project or repository identities.")
    return schema, manifests


def validate_task_project_binding(
    task: dict[str, Any],
    repository_metadata: dict[str, Any],
    *,
    schema: dict[str, Any],
    project_manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind a v2 task to one checked-in manifest and trusted live repository metadata."""
    if task.get("schema_version") != 2:
        raise IntakeError("Project binding validation is only applicable to v2 tasks.")
    binding = task.get("project_binding")
    if not isinstance(binding, dict):
        raise IntakeError("v2 task is missing its explicit project binding.")
    matches = [item for item in project_manifests if item.get("project_id") == binding["project_id"]]
    if len(matches) != 1:
        raise IntakeError("v2 project_id must resolve to exactly one trusted checked-in manifest.")
    manifest = matches[0]
    existing = [item for item in project_manifests if item is not manifest]
    try:
        validated = validate_project_manifest(
            manifest,
            schema=schema,
            repository_metadata=repository_metadata,
            existing_manifests=existing,
            available_profiles=AVAILABLE_PROFILES,
        )
        ensure_implementation_eligible(manifest)
    except ProjectRegistryError as exc:
        raise IntakeError("v2 project manifest or repository binding failed validation.") from exc

    repository = manifest.get("repository", {})
    expected = {
        "project_id": manifest.get("project_id"),
        "repository_id": repository.get("repository_id"),
        "repository_full_name": repository.get("full_name"),
        "default_branch": repository.get("default_branch"),
        "manifest_schema_version": manifest.get("schema_version"),
        "manifest_sha256": validated["manifest_sha256"],
    }
    if binding != expected:
        raise IntakeError("v2 task project binding is stale or differs from its trusted manifest.")
    return dict(expected)


def build_intake(
    event: Any,
    *,
    project_schema: dict[str, Any] | None = None,
    project_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise IntakeError("GitHub event must be a JSON object.")
    action = event.get("action")
    if action not in {"opened", "labeled", "edited"}:
        raise IntakeError("Only opened, labeled, or edited Issues events are accepted.")
    issue = event.get("issue")
    if not isinstance(issue, dict) or issue.get("pull_request") is not None:
        raise IntakeError("Event must reference a GitHub Issue, not a pull request.")
    if issue.get("state") != "open":
        raise IntakeError("Closed Issues cannot enter the task inbox.")
    labels = issue.get("labels")
    if not isinstance(labels, list) or not any(
        isinstance(label, dict) and label.get("name") == TASK_LABEL for label in labels
    ):
        raise IntakeError("Issue must carry the agent-task label.")
    number = issue.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise IntakeError("Issue number is invalid.")
    title = issue.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 300:
        raise IntakeError("Issue title is invalid.")
    body = issue.get("body")
    if not isinstance(body, str):
        raise IntakeError("Issue body is missing.")
    repository = event.get("repository")
    if not isinstance(repository, dict):
        raise IntakeError("Trusted GitHub repository metadata is missing.")
    try:
        task = validate_issue_body(
            body,
            repository_metadata=repository,
            allow_legacy_jet_vpn=True,
        )
    except GitHubTaskError as exc:
        raise IntakeError(f"Task payload rejected: {exc}") from exc

    binding = None
    if task["schema_version"] == 2:
        if not isinstance(project_schema, dict) or not isinstance(project_manifests, list):
            raise IntakeError("Trusted project manifest configuration is unavailable for v2 intake.")
        binding = validate_task_project_binding(
            task, repository, schema=project_schema, project_manifests=project_manifests
        )

    full_name = repository.get("full_name")
    if not isinstance(full_name, str) or "/" not in full_name or len(full_name) > 200:
        raise IntakeError("Repository identity is invalid.")
    html_url = issue.get("html_url")
    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        raise IntakeError("Issue URL is invalid.")
    result = {
        "intake_schema": INTAKE_SCHEMA,
        "source": "github-issue",
        "repository": full_name,
        "issue_number": number,
        "issue_url": html_url,
        "issue_title": title.strip(),
        "issue_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "task": task,
        "execution": {
            "status": "validated-awaiting-claim",
            "lease_claimed": False,
            "agent_dispatched": False,
            "model_called": False,
            "source_uploaded": False,
        },
    }
    if binding is not None:
        result["project_binding"] = binding
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        event = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        root = Path(__file__).resolve().parents[2]
        schema, manifests = load_project_configuration(root)
        result = build_intake(event, project_schema=schema, project_manifests=manifests)
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != encoded:
            raise IntakeError("Refusing to overwrite a different intake artifact.")
        target.write_text(encoded, encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, IntakeError) as exc:
        parser.error(str(exc))
    print(f"Validated Issue #{result['issue_number']} as task {result['task']['task_id']}.")
    print("No lease claimed; no model or implementation agent was invoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
