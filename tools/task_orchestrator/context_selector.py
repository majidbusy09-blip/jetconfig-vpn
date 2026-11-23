"""Deterministic, local-only source-context suggestions from existing semantic artifacts.

This is a ranking aid, not a Dart parser, proof of runtime impact, or permission
to expand a task's declared scope. Suggestions never modify task context.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

MAX_ARTIFACT_BYTES = 25_000_000
MAX_INDEXED_FILES = 5_000
MAX_CRITICAL_PATHS = 1_000
MAX_SUGGESTIONS = 25
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "the", "this", "that", "to",
    "with", "please", "help", "and",
    "و", "از", "به", "در", "برای", "با", "را", "که", "این", "آن",
    "یک", "لطفا", "لطفاً", "کن", "کنید", "شود", "شده",
}
REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class ContextSelectionError(ValueError):
    """Semantic artifacts or task scope cannot safely support context ranking."""


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContextSelectionError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ContextSelectionError(f"{label} must be an existing regular file, not a symlink.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ContextSelectionError(f"Unable to read {label}.") from exc
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ContextSelectionError(f"{label} exceeds the {MAX_ARTIFACT_BYTES}-byte limit.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextSelectionError(f"{label} is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise ContextSelectionError(f"{label} root must be a JSON object.")
    return value, raw


def _safe_index_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ContextSelectionError("Semantic index contains an invalid source path.")
    parts = value.split("/")
    protected = {".git", ".agent", ".secrets", "secrets", "credentials", "keystore", "signing", "release-assets"}
    if parts[-1].casefold() in {"secrets.dart", "credentials.dart", "private_keys.dart"}:
        raise ContextSelectionError(f"Protected source filename cannot enter agent context: {value}")
    if (value.startswith("/") or "\\" in value or any(p in {"", ".", ".."} for p in parts)
            or any(p.lower() in protected for p in parts)
            or any(ord(ch) < 32 for ch in value)):
        raise ContextSelectionError(f"Unsafe source path in semantic index: {value!r}")
    if not value.startswith("lib/") or not value.endswith(".dart"):
        raise ContextSelectionError("Only indexed application Dart source under lib/ may be suggested.")
    return value


def _git_blob_sha(root: Path, revision: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "ls-tree", "-z", revision, "--", f":(literal){relative}"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False,
    )
    if result.returncode:
        raise ContextSelectionError("Git could not verify semantic-index provenance at the pinned revision.")
    entries = [entry for entry in result.stdout.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ContextSelectionError(f"Indexed source is missing or ambiguous at pinned revision: {relative}")
    metadata, returned_path = entries[0].split(b"\t", 1)
    fields = metadata.decode("ascii", errors="strict").split()
    if len(fields) != 3 or returned_path.decode("utf-8", errors="strict") != relative:
        raise ContextSelectionError(f"Git returned an unexpected tree entry for: {relative}")
    mode, object_type, object_sha = fields
    if mode not in {"100644", "100755"} or object_type != "blob":
        raise ContextSelectionError(f"Indexed source must be a regular tracked file: {relative}")
    return object_sha


def _tokens(value: str) -> set[str]:
    normalized = value.casefold().replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
    return {token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
            if len(token) >= 2 and token not in STOP_WORDS}


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def select_context(*, root: Path, task_record: dict[str, Any], query: str,
                   resolved_index_path: Path, critical_paths_path: Path,
                   limit: int = 12) -> dict[str, Any]:
    """Rank in-scope indexed files using names, declarations, calls, and curated paths."""
    if not isinstance(task_record, dict):
        raise ContextSelectionError("Task record must be an object.")
    task_id = task_record.get("task_id")
    repository = task_record.get("repository")
    scope = task_record.get("scope")
    if not isinstance(task_id, str) or not isinstance(repository, dict) or not isinstance(scope, dict):
        raise ContextSelectionError("Task identity, repository, or scope metadata is missing.")
    base_sha = repository.get("base_sha")
    if not isinstance(base_sha, str) or not REVISION_RE.fullmatch(base_sha):
        raise ContextSelectionError("Task has no full pinned Git base SHA.")
    if not isinstance(query, str) or not query.strip() or len(query) > 4_000:
        raise ContextSelectionError("Query must contain 1-4,000 characters.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_SUGGESTIONS:
        raise ContextSelectionError(f"Limit must be between 1 and {MAX_SUGGESTIONS}.")

    allowed, excluded = scope.get("allowed"), scope.get("excluded")
    if (not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed)
            or not isinstance(excluded, list) or not all(isinstance(x, str) for x in excluded)):
        raise ContextSelectionError("Task must have valid explicit allow and exclude path lists.")

    index, index_raw = _read_json(resolved_index_path, "Resolved semantic index")
    report, report_raw = _read_json(critical_paths_path, "Critical-path report")
    if index.get("schema_version") != 2 or index.get("analysis_mode") != "dart_analyzer_resolved_elements_multi_file":
        raise ContextSelectionError("Unsupported or non-resolved semantic-index schema.")
    if report.get("schema_version") != 1 or report.get("analysis_mode") != "static_reachability_from_curated_entrypoints":
        raise ContextSelectionError("Unsupported critical-path report schema.")
    source = index.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("files"), list):
        raise ContextSelectionError("Resolved index has no source file manifest.")
    files = source["files"]
    if not files or len(files) > MAX_INDEXED_FILES or source.get("file_count") != len(files):
        raise ContextSelectionError("Resolved index source-file count is empty, inconsistent, or exceeds the safety limit.")
    report_files = report.get("source_files")
    if not isinstance(report_files, list) or report_files != files:
        raise ContextSelectionError("Critical-path report and resolved index do not describe the exact same source snapshot.")

    by_path: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict):
            raise ContextSelectionError("Resolved index contains a malformed source-file entry.")
        path = _safe_index_path(item.get("path"))
        blob_sha = item.get("git_blob_sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", blob_sha):
            raise ContextSelectionError(f"Resolved index has an invalid Git blob fingerprint: {path}")
        if path in by_path:
            raise ContextSelectionError(f"Resolved index contains duplicate source paths: {path}")
        actual_sha = _git_blob_sha(root, base_sha, path)
        if actual_sha != blob_sha:
            raise ContextSelectionError(f"Semantic index is stale for the task's pinned base: {path}")
        by_path[path] = item

    declarations = index.get("declarations")
    call_sites = index.get("call_sites")
    paths = report.get("paths")
    if not isinstance(declarations, list) or not isinstance(call_sites, list) or not isinstance(paths, list):
        raise ContextSelectionError("Semantic index or critical-path report is missing graph collections.")
    if report.get("source_file_count") != len(files):
        raise ContextSelectionError("Critical-path report source-file count does not match the resolved index.")
    for collection in (declarations, call_sites):
        for entry in collection:
            if not isinstance(entry, dict) or entry.get("source_path") not in by_path:
                raise ContextSelectionError("Semantic graph contains a source path absent from its verified file manifest.")
    if len(paths) > MAX_CRITICAL_PATHS:
        raise ContextSelectionError("Critical-path report exceeds its path-count limit.")

    request_tokens = _tokens(query)
    query_tokens = request_tokens | _tokens(str(task_record.get("goal", "")) + " " +
                                            str(task_record.get("capability_improved", "")))
    if not request_tokens:
        raise ContextSelectionError("Query contains no searchable terms.")

    terms_by_file: dict[str, set[str]] = {path: set() for path in by_path}
    score_by_file: dict[str, int] = {path: 0 for path in by_path}
    reasons_by_file: dict[str, set[str]] = {path: set() for path in by_path}

    for path in by_path:
        path_tokens = _tokens(path)
        matched = query_tokens & path_tokens
        if matched:
            score_by_file[path] += 5 * len(matched)
            terms_by_file[path].update(matched)
            reasons_by_file[path].add("file_path_match")

    for declaration in declarations:
        if not isinstance(declaration, dict):
            continue
        path = declaration.get("source_path")
        if path not in by_path:
            continue
        symbol_text = " ".join(str(declaration.get(key) or "") for key in
                               ("name", "display_name", "owner", "kind"))
        matched = query_tokens & _tokens(symbol_text)
        if matched:
            score_by_file[path] += 4 * len(matched)
            terms_by_file[path].update(matched)
            reasons_by_file[path].add("resolved_declaration_match")

    for call in call_sites:
        if not isinstance(call, dict):
            continue
        path = call.get("source_path")
        if path not in by_path:
            continue
        symbol_text = " ".join(str(call.get(key) or "") for key in
                               ("target_name", "target_display_name", "target_expression"))
        matched = query_tokens & _tokens(symbol_text)
        if matched:
            score_by_file[path] += 2 * len(matched)
            terms_by_file[path].update(matched)
            reasons_by_file[path].add("call_site_match")

    matched_critical_paths = []
    for item in paths:
        if not isinstance(item, dict):
            continue
        path_id = str(item.get("id") or "")
        description = " ".join(str(item.get(key) or "") for key in ("id", "title", "description"))
        matched = request_tokens & _tokens(description)
        if not matched:
            continue
        matched_critical_paths.append(path_id)
        for declaration in item.get("reachable_declarations", []):
            if not isinstance(declaration, dict):
                raise ContextSelectionError("Critical-path report contains a malformed reachable declaration.")
            source_path = _safe_index_path(declaration.get("source_path"))
            if source_path not in by_path:
                raise ContextSelectionError(f"Critical-path report references a source absent from its index: {source_path}")
            score_by_file[source_path] += 7 + 2 * len(matched)
            terms_by_file[source_path].update(matched)
            reasons_by_file[source_path].add(f"critical_path:{path_id}")

    ranked = []
    for path, score in score_by_file.items():
        if score <= 0:
            continue
        if not _matches(path, allowed) or _matches(path, excluded):
            continue
        ranked.append({
            "path": path,
            "git_blob_sha": by_path[path]["git_blob_sha"],
            "score": score,
            "matched_terms": sorted(terms_by_file[path]),
            "reasons": sorted(reasons_by_file[path]),
        })
    ranked.sort(key=lambda item: (-item["score"], item["path"]))
    selected = ranked[:limit]
    return {
        "schema_version": 1,
        "task_id": task_id,
        "source_revision": base_sha,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "resolved_index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "critical_paths_sha256": hashlib.sha256(report_raw).hexdigest(),
        "ranking_method": "deterministic_lexical_and_curated_static_reachability",
        "limitations": [
            "Suggestions are advisory and do not alter the task's explicit context_paths or scope.",
            "Static analyzer reachability is not runtime execution or proof of behavioral impact.",
            "State fields, UI event wiring, callbacks, dynamic dispatch, generated code, and native Java behavior may be missing or only partially represented.",
            "Only source files present in the verified resolved index can be suggested.",
        ],
        "matched_critical_path_ids": sorted(set(matched_critical_paths)),
        "suggestions": selected,
        "candidate_count": len(ranked),
        "omitted_count": max(0, len(ranked) - len(selected)),
    }
