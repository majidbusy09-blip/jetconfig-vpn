"""Fail-closed, out-of-band pinned-key policy for sandbox evidence signatures.

This module validates trust-store bytes against an independently pinned
SHA-256 digest and caller-supplied minimum version before selecting a key.
Production callers may inject CryptographyEd25519Backend from ed25519_backend;
the verifier itself does not create keys, persist rollback state, or authorize execution.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_MAX_TRUST_STORE_BYTES = 64 * 1024
_MAX_KEYS = 64
_TRUST_SCHEMA_VERSION = 1
_TOP_KEYS = frozenset({"schema_version", "version", "keys"})
_KEY_KEYS = frozenset({"key_id", "algorithm", "public_key_b64", "not_before", "not_after", "status"})


class TrustStoreError(ValueError):
    """Pinned trust-store data is invalid or violates key policy."""


class Ed25519Backend(Protocol):
    """Adapter to an audited Ed25519 implementation; no fallback is provided."""

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool: ...


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustStoreError("Trust store contains duplicate JSON keys.")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise TrustStoreError("Trust store contains a non-finite JSON value.")


def _canonical(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise TrustStoreError("Trust store cannot be canonically encoded.") from exc


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise TrustStoreError(f"{field} must be a UTC timestamp ending in Z.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise TrustStoreError(f"{field} is not a valid UTC timestamp.") from exc


@dataclass(frozen=True)
class PinnedTrustStoreVerifier:
    """SignatureVerifier-compatible adapter with externally pinned trust inputs.

    expected_sha256 and minimum_version MUST come from trusted configuration
    outside the provider, guest, report, and trust-store file itself. The caller
    must advance minimum_version monotonically in its protected configuration
    to prevent rollback to an older but correctly hashed trust store.
    """

    trust_store_bytes: bytes
    expected_sha256: str
    minimum_version: int
    now: datetime
    backend: Ed25519Backend

    def __post_init__(self) -> None:
        if not isinstance(self.trust_store_bytes, bytes) or not self.trust_store_bytes:
            raise TrustStoreError("Pinned trust store bytes are required.")
        if len(self.trust_store_bytes) > _MAX_TRUST_STORE_BYTES:
            raise TrustStoreError("Trust store exceeds the size limit.")
        if not isinstance(self.expected_sha256, str) or not _SHA256_RE.fullmatch(self.expected_sha256):
            raise TrustStoreError("An independently pinned trust-store SHA-256 is required.")
        if hashlib.sha256(self.trust_store_bytes).hexdigest() != self.expected_sha256:
            raise TrustStoreError("Trust store does not match the out-of-band pinned digest.")
        if isinstance(self.minimum_version, bool) or not isinstance(self.minimum_version, int) or self.minimum_version < 1:
            raise TrustStoreError("Minimum trust-store version must be a positive integer.")
        if not isinstance(self.now, datetime) or self.now.tzinfo is None or self.now.utcoffset() is None:
            raise TrustStoreError("Trusted verification time must be timezone-aware.")
        if not callable(getattr(self.backend, "verify", None)):
            raise TrustStoreError("An audited Ed25519 backend is required.")
        self._parse_store()

    def _parse_store(self) -> dict[str, dict[str, Any]]:
        try:
            document = json.loads(
                self.trust_store_bytes.decode("utf-8", errors="strict"),
                object_pairs_hook=_pairs_no_duplicates,
                parse_constant=_reject_constant,
            )
        except TrustStoreError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise TrustStoreError("Trust store is not valid bounded UTF-8 JSON.") from exc
        if not isinstance(document, dict) or frozenset(document) != _TOP_KEYS:
            raise TrustStoreError("Trust store fields do not match the strict schema.")
        if type(document["schema_version"]) is not int or document["schema_version"] != _TRUST_SCHEMA_VERSION:
            raise TrustStoreError("Trust-store schema version is unsupported.")
        version = document["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < self.minimum_version:
            raise TrustStoreError("Trust-store version is below the protected minimum.")
        keys = document["keys"]
        if not isinstance(keys, list) or not keys or len(keys) > _MAX_KEYS:
            raise TrustStoreError("Trust store must contain between 1 and 64 keys.")
        indexed: dict[str, dict[str, Any]] = {}
        for entry in keys:
            if not isinstance(entry, dict) or frozenset(entry) != _KEY_KEYS:
                raise TrustStoreError("Trust store contains a malformed key entry.")
            key_id = entry["key_id"]
            if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id) or key_id in indexed:
                raise TrustStoreError("Trust store contains an invalid or duplicate key ID.")
            if entry["algorithm"] != "Ed25519":
                raise TrustStoreError("Only Ed25519 keys are accepted.")
            if entry["status"] not in {"active", "retired", "revoked"}:
                raise TrustStoreError("Trust-store key status is invalid.")
            encoded = entry["public_key_b64"]
            if not isinstance(encoded, str) or not encoded or len(encoded) > 128:
                raise TrustStoreError("Ed25519 public key encoding is invalid.")
            try:
                public_key = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise TrustStoreError("Ed25519 public key is not valid base64.") from exc
            if len(public_key) != 32:
                raise TrustStoreError("Ed25519 public keys must be exactly 32 bytes.")
            not_before = _timestamp(entry["not_before"], "not_before")
            not_after = _timestamp(entry["not_after"], "not_after")
            if not_after <= not_before:
                raise TrustStoreError("Key validity interval is empty or reversed.")
            indexed[key_id] = {
                **entry,
                "_public_key": public_key,
                "_not_before": not_before,
                "_not_after": not_after,
            }
        if _canonical(document) != self.trust_store_bytes:
            raise TrustStoreError("Trust store is not in canonical signed/pinned form.")
        return indexed

    def verify(self, key_id: str, message: bytes, signature: bytes) -> bool:
        """Return True only for a pinned, active, in-window key and valid signature."""
        if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
            return False
        if not isinstance(message, bytes) or not message or not isinstance(signature, bytes) or not signature:
            return False
        try:
            entry = self._parse_store().get(key_id)
            if entry is None or entry["status"] != "active":
                return False
            now = self.now.astimezone(timezone.utc)
            if now < entry["_not_before"] or now >= entry["_not_after"]:
                return False
            return self.backend.verify(entry["_public_key"], message, signature) is True
        except Exception:
            # Fail closed; do not leak backend details to untrusted callers.
            return False
