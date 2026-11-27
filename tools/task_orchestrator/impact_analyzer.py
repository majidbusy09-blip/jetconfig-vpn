"""Verified, deterministic impact mapping over the existing semantic artifacts.

This is static evidence, not a proof of runtime behavior. Changed files absent
from the pinned index are reported as unknown rather than assumed unaffected.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .context_selector import (ContextSelectionError, REVISION_RE, _git_blob_sha, _read_json, _safe_index_path, _verified_artifact_provenance)
except ImportError:
    from context_selector import (ContextSelectionError, REVISION_RE, _git_blob_sha, _read_json, _safe_index_path, _verified_artifact_provenance)

MAX_CHANGED_PATHS = 500
MAX_GRAPH_ENTRIES = 250_000


class ImpactAnalysisError(ValueError):
    """Semantic evidence cannot safely support an impact report."""


def _verified_read(path: Path, label: str):
    try:
        return _read_json(path, label)
    except ContextSelectionError as exc:
        raise ImpactAnalysisError(str(exc)) from exc


def _verified_path(value: Any) -> str:
    try:
        return _safe_index_path(value)
    except ContextSelectionError as exc:
        raise ImpactAnalysisError(str(exc)) from exc


def _verified_blob(root: Path, revision: str, path: str) -> str:
    try:
        return _git_blob_sha(root, revision, path)
    except ContextSelectionError as exc:
        raise ImpactAnalysisError(str(exc)) from exc


def _valid_changed_path(value: Any) -> str:
    if (not isinstance(value, str) or not value or len(value) > 512
            or value.startswith("/") or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or any(ord(ch) < 32 for ch in value)):
        raise ImpactAnalysisError("Changed-path list contains an unsafe repository path.")
    return value


def analyze_impact(*, root: Path, task_record: dict[str, Any],
                   changed_paths: list[str], resolved_index_path: Path,
                   critical_paths_path: Path) -> dict[str, Any]:
    """Map changed paths to verified declarations, call sites, and critical paths."""
    if not isinstance(task_record, dict):
        raise ImpactAnalysisError("Task record must be an object.")
    task_id, repository, scope = (task_record.get("task_id"),
                                  task_record.get("repository"),
                                  task_record.get("scope"))
    if not isinstance(task_id, str) or not isinstance(repository, dict) or not isinstance(scope, dict):
        raise ImpactAnalysisError("Task identity, repository, or scope metadata is missing.")
    base_sha = repository.get("base_sha")
    if not isinstance(base_sha, str) or not REVISION_RE.fullmatch(base_sha):
        raise ImpactAnalysisError("Task has no full pinned Git base SHA.")
    if not isinstance(changed_paths, list) or len(changed_paths) > MAX_CHANGED_PATHS:
        raise ImpactAnalysisError("Changed-path list is invalid or exceeds the 500-path limit.")
    paths = sorted({_valid_changed_path(item) for item in changed_paths})
    allowed, excluded = scope.get("allowed"), scope.get("excluded")
    if (not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed)
            or not isinstance(excluded, list) or not all(isinstance(x, str) for x in excluded)):
        raise ImpactAnalysisError("Task scope metadata is malformed.")

    index, index_raw = _verified_read(resolved_index_path, "Resolved semantic index")
    report, report_raw = _verified_read(critical_paths_path, "Critical-path report")
    if (index.get("schema_version") != 2
            or index.get("analysis_mode") != "dart_analyzer_resolved_elements_multi_file"):
        raise ImpactAnalysisError("Unsupported or non-resolved semantic-index schema.")
    if (report.get("schema_version") != 1
            or report.get("analysis_mode") != "static_reachability_from_curated_entrypoints"):
        raise ImpactAnalysisError("Unsupported critical-path report schema.")
    try:
        artifact_provenance = _verified_artifact_provenance(
            root, task_record, base_sha, index, report, index_raw, report_raw,
        )
    except ContextSelectionError as exc:
        raise ImpactAnalysisError(str(exc)) from exc
    source = index.get("source")
    files = source.get("files") if isinstance(source, dict) else None
    if (not isinstance(files, list) or not files or len(files) > 5_000
            or source.get("file_count") != len(files)
            or report.get("source_files") != files
            or report.get("source_file_count") != len(files)):
        raise ImpactAnalysisError("Resolved index and critical-path report do not share one valid source manifest.")

    by_path: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict):
            raise ImpactAnalysisError("Resolved index contains a malformed file entry.")
        path = _verified_path(item.get("path"))
        digest = item.get("git_blob_sha")
        if not isinstance(digest, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", digest):
            raise ImpactAnalysisError(f"Invalid source fingerprint for {path}.")
        if path in by_path:
            raise ImpactAnalysisError(f"Duplicate source path in semantic index: {path}")
        error_count = item.get("error_count", 0)
        if not isinstance(error_count, int) or isinstance(error_count, bool) or error_count < 0:
            raise ImpactAnalysisError(f"Invalid analyzer error count for {path}.")
        by_path[path] = item

    declarations, call_sites, critical = index.get("declarations"), index.get("call_sites"), report.get("paths")
    if (not isinstance(declarations, list) or not isinstance(call_sites, list)
            or not isinstance(critical, list)
            or len(declarations) + len(call_sites) + len(critical) > MAX_GRAPH_ENTRIES):
        raise ImpactAnalysisError("Semantic graph collections are missing or exceed safety limits.")
    for collection in (declarations, call_sites):
        for entry in collection:
            if not isinstance(entry, dict) or entry.get("source_path") not in by_path:
                raise ImpactAnalysisError("Semantic graph references a path outside its verified manifest.")

    indexed_changed, unknown, scope_violations = [], [], []
    for path in paths:
        if (not any(fnmatch.fnmatchcase(path, pattern) for pattern in allowed)
                or any(fnmatch.fnmatchcase(path, pattern) for pattern in excluded)):
            scope_violations.append(path)
        if path not in by_path:
            reason = "not_present_in_semantic_index"
            if not path.startswith("lib/") or not path.endswith(".dart"):
                reason = "outside_indexed_dart_source"
            unknown.append({"path": path, "reason": reason})
            continue
        if _verified_blob(root, base_sha, path) != by_path[path]["git_blob_sha"]:
            raise ImpactAnalysisError(f"Semantic index is stale for changed source at pinned base: {path}")
        indexed_changed.append(path)

    changed_set = set(indexed_changed)
    impacted_declarations, declaration_ids_by_path = [], {}
    for entry in declarations:
        path = entry["source_path"]
        if path not in changed_set:
            continue
        identifier = entry.get("id") or entry.get("element_id") or entry.get("element")
        if isinstance(identifier, str):
            declaration_ids_by_path.setdefault(path, set()).add(identifier)
        impacted_declarations.append({
            "path": path, "name": entry.get("name"),
            "display_name": entry.get("display_name"), "kind": entry.get("kind"),
            "owner": entry.get("owner"),
        })

    related_calls, incoming_calls = [], []
    changed_ids = set().union(*declaration_ids_by_path.values()) if declaration_ids_by_path else set()
    for entry in call_sites:
        source_path = entry["source_path"]
        target_path = entry.get("target_source_path") or entry.get("target_path") or entry.get("target_file")
        target_id = entry.get("target_id") or entry.get("target_element_id") or entry.get("target_element")
        item = {
            "source_path": source_path, "target_name": entry.get("target_name"),
            "target_display_name": entry.get("target_display_name"),
            "target_source_path": target_path if isinstance(target_path, str) else None,
        }
        if source_path in changed_set:
            related_calls.append(item)
        if target_path in changed_set or (isinstance(target_id, str) and target_id in changed_ids):
            incoming_calls.append(item)

    impacted_paths = []
    for entry in critical:
        if not isinstance(entry, dict):
            raise ImpactAnalysisError("Critical-path report contains a malformed path entry.")
        reachable = entry.get("reachable_declarations", [])
        if not isinstance(reachable, list):
            raise ImpactAnalysisError("Critical path has malformed reachable declarations.")
        hit = []
        for declaration in reachable:
            if not isinstance(declaration, dict):
                raise ImpactAnalysisError("Critical path has malformed declaration metadata.")
            source_path = _verified_path(declaration.get("source_path"))
            if source_path not in by_path:
                raise ImpactAnalysisError(f"Critical path references an unindexed source: {source_path}")
            if source_path in changed_set:
                hit.append(source_path)
        if hit:
            impacted_paths.append({
                "id": entry.get("id"), "title": entry.get("title"),
                "description": entry.get("description") or entry.get("summary"),
                "changed_reachable_files": sorted(set(hit)),
            })

    profiles = set()
    if any(path.startswith("lib/") and path.endswith(".dart") for path in paths):
        profiles.update({"flutter-analysis", "flutter-tests", "lexical-memory-audit"})
    if any(path.startswith("tools/task_orchestrator/") for path in paths):
        profiles.add("python-tooling-tests")
    if any(path.startswith("tools/project_memory/") for path in paths):
        profiles.update({"python-tooling-tests", "lexical-memory-audit"})
    if any(path.startswith(".github/workflows/") for path in paths):
        profiles.add("non-production-pr-validation-workflow-review")
    risk_flags = []
    if impacted_paths:
        risk_flags.append("changed_code_reachable_from_curated_critical_path")
    if unknown:
        risk_flags.append("semantic_coverage_incomplete_for_one_or_more_changed_paths")
    if scope_violations:
        risk_flags.append("changed_paths_outside_declared_task_scope")
    if any(int(by_path[p].get("error_count", 0) or 0) > 0 for p in indexed_changed):
        risk_flags.append("pinned_semantic_index_reports_analyzer_errors_for_changed_source")
    return {
        "schema_version": 1, "task_id": task_id, "source_revision": base_sha,
        "changed_paths": paths, "indexed_changed_paths": indexed_changed,
        "not_indexed_or_unknown": unknown, "scope_violations": scope_violations,
        "impacted_critical_paths": sorted(impacted_paths, key=lambda x: str(x.get("id") or "")),
        "changed_declarations": sorted(impacted_declarations, key=lambda x: (x["path"], str(x.get("name") or ""))),
        "call_sites_in_changed_files": sorted(related_calls, key=lambda x: (x["source_path"], str(x.get("target_name") or ""))),
        "call_sites_targeting_changed_declarations": sorted(incoming_calls, key=lambda x: (x["source_path"], str(x.get("target_name") or ""))),
        "recommended_verification_profiles": sorted(profiles), "risk_flags": sorted(set(risk_flags)),
        "artifact_provenance": artifact_provenance,
        "semantic_index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "critical_paths_sha256": hashlib.sha256(report_raw).hexdigest(),
        "analysis_method": "pinned_git_blob_verified_resolved_declarations_and_curated_static_reachability",
        "limitations": [
            "Static reachability is not proof of runtime behavior or complete dependency coverage.",
            "Incoming call-site mapping is reported only when the index explicitly carries target source paths or declaration identifiers.",
            "Dynamic dispatch, reflection, callback/event wiring, UI state dependencies, generated code, and native Java/Kotlin behavior may be absent.",
            "Changed paths absent from the pinned semantic index are unknown, never classified as unaffected.",
            "Recommended verification profiles are advisory; task-declared required checks remain authoritative.",
        ],
    }
