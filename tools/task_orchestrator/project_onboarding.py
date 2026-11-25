"""Read-only project onboarding readiness assessment.

The module consumes already-fetched repository metadata and inventories. It does
not access the network or filesystem, execute repository code, persist registry
state, activate projects, or perform GitHub mutations.
"""
from __future__ import annotations

import re
from typing import Any

from tools.task_orchestrator.project_registry import (
    ProjectRegistryError,
    manifest_digest,
    validate_project_manifest,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_READY = "READY_FOR_REGISTRATION"
_REVIEW = "NEEDS_REVIEW"
_BLOCKED = "BLOCKED"


def _append_unique(items: list[str], message: str) -> None:
    if message not in items:
        items.append(message)


def _valid_inventory_entry(entry: Any, pinned_sha: str) -> bool:
    return (
        isinstance(entry, dict)
        and entry.get("tracked") is True
        and entry.get("regular_file") is True
        and isinstance(entry.get("blob_sha"), str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", entry["blob_sha"]))
        and entry.get("source_sha") == pinned_sha
        and isinstance(entry.get("size_bytes"), int)
        and not isinstance(entry.get("size_bytes"), bool)
        and entry["size_bytes"] >= 0
    )


def build_readiness_report(
    *,
    manifest: dict[str, Any],
    schema: dict[str, Any],
    repository_metadata: dict[str, Any],
    base_sha: str,
    existing_manifests: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    available_profiles: set[str] | frozenset[str],
    runner_results: dict[str, str],
    memory_inventory: dict[str, dict[str, Any]],
    toolchain_evidence: dict[str, dict[str, Any]],
    source_index_assessment: dict[str, Any],
    target_memory_pr_merged: bool,
    dependency_lockfile_present: bool,
) -> dict[str, Any]:
    """Build a deterministic readiness report from trusted, read-only evidence.

    runner_results values are limited to success, pending, failure, or skipped.
    memory_inventory entries must prove tracked regular files at the exact
    pinned source revision. The caller is responsible for obtaining evidence.
    """
    blockers: list[str] = []
    human_decisions: list[str] = []
    identity_verified = False
    manifest_validation: dict[str, Any] | None = None

    if not isinstance(base_sha, str) or not _SHA_RE.fullmatch(base_sha):
        _append_unique(blockers, "Pinned repository base SHA is missing or malformed.")

    try:
        manifest_validation = validate_project_manifest(
            manifest,
            schema=schema,
            repository_metadata=repository_metadata,
            existing_manifests=existing_manifests,
            available_profiles=available_profiles,
        )
        identity_verified = True
    except ProjectRegistryError as exc:
        _append_unique(blockers, f"Manifest or repository identity validation failed: {exc}")

    repository = {
        "provider": "github",
        "repository_id": str(repository_metadata.get("id", "")) if isinstance(repository_metadata, dict) else "",
        "full_name": repository_metadata.get("full_name", "") if isinstance(repository_metadata, dict) else "",
        "url": repository_metadata.get("html_url", "") if isinstance(repository_metadata, dict) else "",
        "default_branch": repository_metadata.get("default_branch", "") if isinstance(repository_metadata, dict) else "",
        "base_sha": base_sha if isinstance(base_sha, str) else "",
        "identity_verified": identity_verified,
    }

    memory = manifest.get("memory", {}) if isinstance(manifest, dict) else {}
    required_documents = memory.get("required_documents", []) if isinstance(memory, dict) else []
    max_total_bytes = memory.get("max_total_bytes", 0) if isinstance(memory, dict) else 0
    found_documents: list[str] = []
    missing_documents: list[str] = []
    invalid_documents: list[str] = []
    total_bytes = 0

    for path in required_documents if isinstance(required_documents, list) else []:
        entry = memory_inventory.get(path) if isinstance(memory_inventory, dict) else None
        if entry is None:
            missing_documents.append(path)
        elif not _valid_inventory_entry(entry, base_sha):
            invalid_documents.append(path)
        else:
            found_documents.append(path)
            total_bytes += entry["size_bytes"]

    if missing_documents:
        _append_unique(
            blockers,
            "Required project-memory document(s) are missing at the pinned revision: "
            + ", ".join(missing_documents),
        )
    if invalid_documents:
        _append_unique(
            blockers,
            "Required project-memory document(s) are not verified tracked regular files at the exact pinned revision: "
            + ", ".join(invalid_documents),
        )
    if isinstance(max_total_bytes, int) and total_bytes > max_total_bytes:
        _append_unique(blockers, "Required project-memory documents exceed the manifest byte limit.")

    toolchains = manifest.get("toolchains", []) if isinstance(manifest, dict) else []
    toolchain_report: list[dict[str, Any]] = []
    for toolchain in toolchains if isinstance(toolchains, list) else []:
        if not isinstance(toolchain, dict):
            continue
        toolchain_id = toolchain.get("id")
        evidence = toolchain_evidence.get(toolchain_id) if isinstance(toolchain_evidence, dict) else None
        expected_version = toolchain.get("version")
        verified = isinstance(evidence, dict) and evidence.get("verified") is True
        observed_version = evidence.get("version") if isinstance(evidence, dict) else None
        toolchain_report.append({
            "id": toolchain_id,
            "required": toolchain.get("required") is True,
            "expected_version": expected_version,
            "observed_version": observed_version,
            "verified": verified and (expected_version is None or observed_version == expected_version),
            "evidence_source": evidence.get("source") if isinstance(evidence, dict) else None,
        })
        if toolchain.get("required") is True:
            if not verified:
                _append_unique(human_decisions, f"Confirm the required {toolchain_id} toolchain from an exact successful CI run.")
            elif expected_version is not None and observed_version != expected_version:
                _append_unique(blockers, f"Observed {toolchain_id} version does not match the manifest pin.")

    verification = manifest.get("verification", {}) if isinstance(manifest, dict) else {}
    required_profiles = verification.get("required_profiles", []) if isinstance(verification, dict) else []
    profile_report: list[dict[str, str]] = []
    for profile in required_profiles if isinstance(required_profiles, list) else []:
        status = runner_results.get(profile, "missing") if isinstance(runner_results, dict) else "missing"
        profile_report.append({"profile": profile, "status": status})
        if profile not in available_profiles:
            _append_unique(blockers, f"Required verification runner is not implemented: {profile}.")
        elif status in {"failure", "skipped", "missing"}:
            _append_unique(blockers, f"Required verification profile did not pass: {profile} ({status}).")
        elif status == "pending":
            _append_unique(human_decisions, f"Wait for an exact successful run of required profile: {profile}.")
        elif status != "success":
            _append_unique(blockers, f"Required verification profile has an unknown status: {profile}.")

    index_status = (
        source_index_assessment.get("status")
        if isinstance(source_index_assessment, dict)
        else "unknown"
    )
    if index_status in {"adapter_required", "not_reusable_as_is", "unknown"}:
        _append_unique(
            human_decisions,
            "Dart semantic indexing needs a project-neutral CLI/output adapter; the existing JET VPN entrypoints and artifact names are repository-specific.",
        )
    elif index_status not in {"supported", "not_required"}:
        _append_unique(human_decisions, "Review the source-index compatibility assessment before activation.")

    if not target_memory_pr_merged:
        _append_unique(human_decisions, "Merge the separately reviewed target-repository memory/CI PR before registration readiness.")
    if not dependency_lockfile_present:
        _append_unique(human_decisions, "Commit and review pubspec.lock to make Flutter dependency resolution reproducible.")

    if blockers:
        overall = _BLOCKED
    elif human_decisions:
        overall = _REVIEW
    else:
        overall = _READY

    manifest_sha = None
    try:
        manifest_sha = manifest_digest(manifest)
    except ProjectRegistryError as exc:
        _append_unique(blockers, f"Manifest digest could not be computed: {exc}")
        overall = _BLOCKED

    return {
        "report_schema_version": 1,
        "mode": "dry_run_read_only",
        "project_id_candidate": manifest.get("project_id") if isinstance(manifest, dict) else None,
        "manifest_sha256": manifest_sha,
        "repository": repository,
        "discovery": {
            "project_type": manifest.get("project_type") if isinstance(manifest, dict) else None,
            "languages": manifest.get("languages", []) if isinstance(manifest, dict) else [],
            "toolchains": toolchain_report,
            "memory": {
                "required_documents_found": found_documents,
                "missing_documents": missing_documents,
                "invalid_documents": invalid_documents,
                "total_bytes": total_bytes,
                "max_total_bytes": max_total_bytes,
            },
            "source_index": source_index_assessment,
            "verification": {
                "required_profiles": profile_report,
                "available_profiles": sorted(available_profiles),
            },
            "protected_paths": manifest.get("protected_paths", []) if isinstance(manifest, dict) else [],
        },
        "blockers": blockers,
        "human_decisions": human_decisions,
        "writes_performed": False,
        "overall_readiness": overall,
        "implementation_eligible": False,
        "manifest_validation": manifest_validation,
    }
