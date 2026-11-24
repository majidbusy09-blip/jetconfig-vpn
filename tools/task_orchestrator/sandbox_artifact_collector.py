"""Pure artifact-inventory validation contract for sandbox acceptance.

This module validates caller-supplied artifact bytes and metadata. It does not
open files, inspect filesystem objects, retain/delete artifacts, verify signed
reports, or authorize execution. A future trusted host adapter must independently
collect files with descriptor-relative, no-follow filesystem operations.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MAX_FILES = 32
_MAX_FILE_BYTES = 1024 * 1024
_MAX_TOTAL_BYTES = 8 * 1024 * 1024
_MAX_RETENTION_SECONDS = 30 * 24 * 60 * 60
_MIN_RETENTION_SECONDS = 60
_MANIFEST_SCHEMA_VERSION = 1


class ArtifactCollectionError(ValueError):
    """Artifact candidate inventory is malformed, unsafe, or exceeds policy."""


@dataclass(frozen=True)
class AcceptanceReference:
    """Caller assertion produced after separate signed-report verification.

    This data class is not a cryptographic capability. Callers must obtain it
    only after verify_signed_acceptance_report succeeds under an independently
    pinned trust configuration. This module cannot enforce that provenance.
    """

    status: str
    attempt_id: str
    runtime_id: str
    policy_digest: str
    evidence_digest: str
    report_digest: str


@dataclass(frozen=True)
class ArtifactCandidate:
    """Bounded bytes plus host-observed metadata supplied to the pure validator."""

    relative_path: str
    content: bytes
    file_type: str = "regular_file"
    is_symlink: bool = False
    link_count: int = 1


@dataclass(frozen=True)
class ArtifactCollectionPolicy:
    attempt_id: str
    runtime_id: str
    policy_digest: str
    evidence_digest: str
    acceptance_report_digest: str
    allowed_roots: tuple[str, ...]
    retention_policy_id: str
    retention_seconds: int = 24 * 60 * 60
    max_files: int = _MAX_FILES
    max_file_bytes: int = _MAX_FILE_BYTES
    max_total_bytes: int = _MAX_TOTAL_BYTES

    def validate(self) -> None:
        for field in ("attempt_id", "runtime_id", "retention_policy_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ArtifactCollectionError(f"{field} is invalid.")
        for field in ("policy_digest", "evidence_digest", "acceptance_report_digest"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.startswith("sha256:") or not _SHA256_RE.fullmatch(value[7:]):
                raise ArtifactCollectionError(f"{field} must be a pinned SHA-256 digest.")
        if not isinstance(self.allowed_roots, tuple) or not self.allowed_roots:
            raise ArtifactCollectionError("At least one explicit allowed root is required.")
        roots = tuple(_normalize_path(root, is_root=True) for root in self.allowed_roots)
        if len(set(roots)) != len(roots):
            raise ArtifactCollectionError("Allowed roots must be unique.")
        for field in ("max_files", "max_file_bytes", "max_total_bytes", "retention_seconds"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ArtifactCollectionError(f"{field} must be an integer.")
        if not 1 <= self.max_files <= _MAX_FILES:
            raise ArtifactCollectionError("max_files exceeds the hard policy ceiling.")
        if not 1 <= self.max_file_bytes <= _MAX_FILE_BYTES:
            raise ArtifactCollectionError("max_file_bytes exceeds the hard policy ceiling.")
        if not 1 <= self.max_total_bytes <= _MAX_TOTAL_BYTES:
            raise ArtifactCollectionError("max_total_bytes exceeds the hard policy ceiling.")
        if not _MIN_RETENTION_SECONDS <= self.retention_seconds <= _MAX_RETENTION_SECONDS:
            raise ArtifactCollectionError("retention_seconds is outside the bounded retention window.")


@dataclass(frozen=True)
class ArtifactManifest:
    canonical_bytes: bytes
    sha256: str
    artifact_count: int
    total_bytes: int
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False


def _normalize_path(value: str, *, is_root: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ArtifactCollectionError("Artifact path is empty or exceeds the path limit.")
    if (
        value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or ":" in value
    ):
        raise ArtifactCollectionError("Artifact path contains an absolute, platform-specific, or control component.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ArtifactCollectionError("Artifact path is not a normalized relative path.")
    if any(len(part.encode("utf-8")) > 128 for part in parts):
        raise ArtifactCollectionError("Artifact path component exceeds the byte limit.")
    if is_root and len(parts) > 8:
        raise ArtifactCollectionError("Allowed root is too deeply nested.")
    return "/".join(parts)


def evidence_bundle_digest(probe_evidence: dict[str, bytes]) -> str:
    """Compute a deterministic digest over exact raw probe evidence bytes."""
    if not isinstance(probe_evidence, dict) or not probe_evidence:
        raise ArtifactCollectionError("A non-empty raw evidence mapping is required.")
    entries = []
    for probe_id in sorted(probe_evidence):
        payload = probe_evidence[probe_id]
        if not isinstance(probe_id, str) or not _ID_RE.fullmatch(probe_id):
            raise ArtifactCollectionError("Probe evidence key is invalid.")
        if not isinstance(payload, bytes) or not payload:
            raise ArtifactCollectionError("Probe evidence must contain non-empty raw bytes.")
        entries.append({
            "probe_id": probe_id,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


class ArtifactCollector:
    """Validate and serialize a bounded artifact inventory without filesystem I/O."""

    def __init__(self, policy: ArtifactCollectionPolicy) -> None:
        if not isinstance(policy, ArtifactCollectionPolicy):
            raise ArtifactCollectionError("A typed artifact collection policy is required.")
        policy.validate()
        self._policy = policy
        self._roots = tuple(_normalize_path(root, is_root=True) for root in policy.allowed_roots)

    def collect(
        self,
        *,
        acceptance: AcceptanceReference,
        artifacts: Iterable[ArtifactCandidate],
    ) -> ArtifactManifest:
        if not isinstance(acceptance, AcceptanceReference):
            raise ArtifactCollectionError("A verified acceptance reference is required.")
        expected = {
            "status": "verified",
            "attempt_id": self._policy.attempt_id,
            "runtime_id": self._policy.runtime_id,
            "policy_digest": self._policy.policy_digest,
            "evidence_digest": self._policy.evidence_digest,
            "report_digest": self._policy.acceptance_report_digest,
        }
        for field, value in expected.items():
            if getattr(acceptance, field, None) != value:
                raise ArtifactCollectionError(f"Acceptance reference {field} does not match the pinned attempt.")

        if isinstance(artifacts, (str, bytes, dict)):
            raise ArtifactCollectionError("Artifacts must be a finite iterable of typed candidates.")
        try:
            candidates = tuple(artifacts)
        except (TypeError, ValueError) as exc:
            raise ArtifactCollectionError("Artifact candidates are not a valid finite iterable.") from exc
        if not candidates or len(candidates) > self._policy.max_files:
            raise ArtifactCollectionError("Artifact count is empty or exceeds the configured limit.")

        seen: set[str] = set()
        entries: list[dict[str, object]] = []
        total_bytes = 0
        for candidate in candidates:
            if not isinstance(candidate, ArtifactCandidate):
                raise ArtifactCollectionError("Every artifact must use the typed candidate contract.")
            path = _normalize_path(candidate.relative_path)
            if path in seen:
                raise ArtifactCollectionError("Duplicate artifact path.")
            seen.add(path)
            if not any(path.startswith(root + "/") for root in self._roots):
                raise ArtifactCollectionError("Artifact path is outside the explicit allowed roots.")
            if candidate.file_type != "regular_file":
                raise ArtifactCollectionError("Only regular files are accepted; directories and special files are rejected.")
            if candidate.is_symlink is not False:
                raise ArtifactCollectionError("Symlink artifacts are rejected.")
            if isinstance(candidate.link_count, bool) or candidate.link_count != 1:
                raise ArtifactCollectionError("Hard-linked or invalid file records are rejected.")
            if not isinstance(candidate.content, bytes) or not candidate.content:
                raise ArtifactCollectionError("Artifact content must be non-empty raw bytes.")
            size = len(candidate.content)
            if size > self._policy.max_file_bytes:
                raise ArtifactCollectionError("Artifact exceeds the per-file size limit.")
            total_bytes += size
            if total_bytes > self._policy.max_total_bytes:
                raise ArtifactCollectionError("Artifact inventory exceeds the aggregate size limit.")
            entries.append({
                "path": path,
                "size_bytes": size,
                "sha256": hashlib.sha256(candidate.content).hexdigest(),
            })

        entries.sort(key=lambda item: str(item["path"]))
        manifest = {
            "schema_version": _MANIFEST_SCHEMA_VERSION,
            "attempt_id": self._policy.attempt_id,
            "runtime_id": self._policy.runtime_id,
            "policy_digest": self._policy.policy_digest,
            "evidence_digest": self._policy.evidence_digest,
            "acceptance_report_digest": self._policy.acceptance_report_digest,
            "retention": {
                "policy_id": self._policy.retention_policy_id,
                "retention_seconds": self._policy.retention_seconds,
            },
            "artifacts": entries,
            "artifact_count": len(entries),
            "total_bytes": total_bytes,
            "execution_authorized": False,
            "eligible_for_untrusted_execution": False,
        }
        canonical = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        return ArtifactManifest(
            canonical_bytes=canonical,
            sha256=hashlib.sha256(canonical).hexdigest(),
            artifact_count=len(entries),
            total_bytes=total_bytes,
        )
