"""Pure in-memory artifact validation for a future trusted sandbox host.

This module validates caller-supplied bytes and metadata only. It does not open
paths, inspect filesystem objects, retain/delete files, or authenticate evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

MAX_ARTIFACTS = 64
MAX_ARTIFACT_BYTES = 256 * 1024
MAX_TOTAL_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_PATH_BYTES = 240
MAX_COMPONENT_BYTES = 64
MAX_RETENTION_SECONDS = 30 * 24 * 60 * 60
_ALLOWED_ROOTS = ("artifacts/", "reports/")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ArtifactCollectionError(ValueError):
    """An artifact candidate is malformed, unsafe, oversized, or out of scope."""


@dataclass(frozen=True)
class ArtifactCandidate:
    path: str
    kind: str
    content: bytes
    symlink_target: str | None = None


@dataclass(frozen=True)
class CollectedArtifact:
    path: str
    size_bytes: int
    sha256: str
    content: bytes


@dataclass(frozen=True)
class ArtifactManifest:
    attempt_id: str
    runtime_id: str
    policy_digest: str
    evidence_digest: str
    acceptance_report_digest: str
    retention_seconds: int
    artifacts: tuple[CollectedArtifact, ...]
    canonical_bytes: bytes
    manifest_sha256: str
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False


def _validate_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ArtifactCollectionError(f"{field} is invalid.")


def _validate_digest(value: str, field: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ArtifactCollectionError(f"{field} must be a lowercase SHA-256 digest.")


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ArtifactCollectionError("Artifact path must be a non-empty string.")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ArtifactCollectionError("Artifact path is not valid UTF-8.") from exc
    if len(encoded) > MAX_PATH_BYTES:
        raise ArtifactCollectionError("Artifact path exceeds the maximum length.")
    if value.startswith("/") or value.startswith("\\") or "\\" in value or "\x00" in value:
        raise ArtifactCollectionError("Artifact path must be a normalized relative POSIX path.")
    if re.match(r"^[A-Za-z]:", value):
        raise ArtifactCollectionError("Windows drive-qualified artifact paths are forbidden.")
    if value.endswith("/") or "//" in value:
        raise ArtifactCollectionError("Artifact path contains an empty component.")
    components = value.split("/")
    if len(components) < 2 or any(part in {"", ".", ".."} for part in components):
        raise ArtifactCollectionError("Artifact path traversal or non-normalized components are forbidden.")
    for component in components:
        if len(component.encode("utf-8")) > MAX_COMPONENT_BYTES or not _COMPONENT_RE.fullmatch(component):
            raise ArtifactCollectionError("Artifact path contains an unsupported component.")
    normalized = "/".join(components)
    if not any(normalized.startswith(root) for root in _ALLOWED_ROOTS):
        raise ArtifactCollectionError("Artifact path is outside the configured allowlisted roots.")
    return normalized


class ArtifactCollector:
    """Validate bounded in-memory candidates and produce a deterministic manifest."""

    def __init__(
        self,
        *,
        attempt_id: str,
        runtime_id: str,
        policy_digest: str,
        evidence_digest: str,
        acceptance_report_digest: str,
        retention_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        _validate_id(attempt_id, "Attempt identity")
        _validate_id(runtime_id, "Runtime identity")
        _validate_digest(policy_digest, "Policy digest")
        _validate_digest(evidence_digest, "Evidence digest")
        _validate_digest(acceptance_report_digest, "Acceptance report digest")
        if (
            isinstance(retention_seconds, bool)
            or not isinstance(retention_seconds, int)
            or not 1 <= retention_seconds <= MAX_RETENTION_SECONDS
        ):
            raise ArtifactCollectionError("Retention must be between 1 second and 30 days.")
        self._attempt_id = attempt_id
        self._runtime_id = runtime_id
        self._policy_digest = policy_digest
        self._evidence_digest = evidence_digest
        self._acceptance_report_digest = acceptance_report_digest
        self._retention_seconds = retention_seconds

    def collect(self, candidates: list[ArtifactCandidate]) -> ArtifactManifest:
        if not isinstance(candidates, list):
            raise ArtifactCollectionError("Artifact candidates must be supplied as a bounded list.")
        if len(candidates) > MAX_ARTIFACTS:
            raise ArtifactCollectionError("Artifact count exceeds the configured limit.")

        seen: set[str] = set()
        collected: list[CollectedArtifact] = []
        total_bytes = 0
        for candidate in candidates:
            if not isinstance(candidate, ArtifactCandidate):
                raise ArtifactCollectionError("Every candidate must use the typed artifact contract.")
            path = _normalize_relative_path(candidate.path)
            if path in seen:
                raise ArtifactCollectionError("Duplicate artifact path.")
            seen.add(path)
            if candidate.kind != "regular_file":
                raise ArtifactCollectionError("Only regular files are eligible; symlinks, directories, and devices are rejected.")
            if candidate.symlink_target is not None:
                raise ArtifactCollectionError("Symlink metadata is forbidden for artifact candidates.")
            if not isinstance(candidate.content, bytes):
                raise ArtifactCollectionError("Artifact content must be supplied as raw bytes.")
            size = len(candidate.content)
            if size == 0:
                raise ArtifactCollectionError("Empty artifacts are not accepted.")
            if size > MAX_ARTIFACT_BYTES:
                raise ArtifactCollectionError("Artifact exceeds the per-file size limit.")
            total_bytes += size
            if total_bytes > MAX_TOTAL_ARTIFACT_BYTES:
                raise ArtifactCollectionError("Artifacts exceed the aggregate size limit.")
            payload = bytes(candidate.content)
            collected.append(
                CollectedArtifact(
                    path=path,
                    size_bytes=size,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    content=payload,
                )
            )

        collected.sort(key=lambda item: item.path)
        manifest_object = {
            "schema_version": 1,
            "attempt_id": self._attempt_id,
            "runtime_id": self._runtime_id,
            "policy_digest": self._policy_digest,
            "evidence_digest": self._evidence_digest,
            "acceptance_report_digest": self._acceptance_report_digest,
            "retention_seconds": self._retention_seconds,
            "artifacts": [
                {"path": item.path, "size_bytes": item.size_bytes, "sha256": item.sha256}
                for item in collected
            ],
        }
        canonical = json.dumps(
            manifest_object,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        return ArtifactManifest(
            attempt_id=self._attempt_id,
            runtime_id=self._runtime_id,
            policy_digest=self._policy_digest,
            evidence_digest=self._evidence_digest,
            acceptance_report_digest=self._acceptance_report_digest,
            retention_seconds=self._retention_seconds,
            artifacts=tuple(collected),
            canonical_bytes=canonical,
            manifest_sha256=hashlib.sha256(canonical).hexdigest(),
        )
