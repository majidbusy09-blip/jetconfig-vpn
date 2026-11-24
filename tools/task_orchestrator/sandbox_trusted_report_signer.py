"""Trusted Report Signer gate.

The signer accepts only a canonical schema-v3 report accompanied by a
verifier-signed attestation that binds the exact report and envelope manifest.
Private signing material is supplied only through an injected KMS/HSM adapter.
This module does not create, load, or persist private keys.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES, SUITE_ID, SUITE_VERSION

MAX_REPORT_BYTES = 256 * 1024
MAX_ATTESTATION_BYTES = 16 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ATTESTATION_LIFETIME_SECONDS = 120
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_V3_REPORT_FIELDS = frozenset({
    "schema_version", "suite_id", "suite_version", "key_id", "provider_id",
    "region", "runtime_id", "task_id", "attempt_id", "image_digest",
    "policy_digest", "started_at", "completed_at", "probes",
    "observer_registry_sha256", "observer_registry_version",
    "observer_provenance_sha256", "observer_provenance",
    "observer_envelope_manifest_version", "observer_envelope_manifest_sha256",
})
_PROBE_FIELDS = frozenset({"probe_id", "outcome", "evidence_sha256"})
_ATTESTATION_FIELDS = frozenset({
    "schema_version", "verifier_id", "verifier_key_id", "audience", "report_sha256",
    "envelope_manifest_sha256", "verification_id", "issued_at", "expires_at",
    "signature_algorithm", "signature_b64",
})


class TrustedReportSigningError(ValueError):
    """A report is not independently authorized for signing."""


class VerifierAttestationVerifier(Protocol):
    """Must verify Ed25519 with an independently pinned verifier public key."""

    def verify(self, verifier_id: str, verifier_key_id: str, message: bytes, signature: bytes) -> bool: ...


class ReportSigningBackend(Protocol):
    """KMS/HSM adapter; key material must never be returned to this process."""

    def sign(self, key_id: str, message: bytes) -> bytes: ...


class SigningAuthorizationStore(Protocol):
    """Atomic durable one-time attestation/verification-ID consumption."""

    def consume(
        self, *, verifier_id: str, verifier_key_id: str, audience: str,
        verification_id: str, report_sha256: str,
        envelope_manifest_sha256: str, accepted_at: str, expires_at: str,
    ) -> bool: ...


@dataclass(frozen=True)
class SignedAcceptanceReport:
    report_bytes: bytes
    report_sha256: str
    key_id: str
    signature: bytes
    signature_algorithm: str = "Ed25519"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise TrustedReportSigningError("Input cannot be canonically encoded.") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedReportSigningError("Duplicate JSON keys are forbidden.")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise TrustedReportSigningError("Non-finite JSON values are forbidden.")


def _parse_canonical(raw: bytes, *, maximum: int, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > maximum:
        raise TrustedReportSigningError(f"{label} is empty or oversized.")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except TrustedReportSigningError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TrustedReportSigningError(f"{label} is not valid bounded UTF-8 JSON.") from exc
    if not isinstance(value, dict) or _canonical(value) != raw:
        raise TrustedReportSigningError(f"{label} must be a canonical JSON object.")
    return value


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise TrustedReportSigningError(f"{field} must be a UTC timestamp with second precision.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise TrustedReportSigningError(f"{field} is invalid.") from exc


def _id(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise TrustedReportSigningError(f"{field} is invalid.")


def _digest(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise TrustedReportSigningError(f"{field} must be a lowercase SHA-256 digest.")


def _decode_signature(value: Any) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise TrustedReportSigningError("Verifier attestation signature is missing or oversized.")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TrustedReportSigningError("Verifier attestation signature is not strict base64.") from exc
    if base64.b64encode(raw).decode("ascii") != value or len(raw) != 64:
        raise TrustedReportSigningError("Verifier attestation must contain a canonical 64-byte Ed25519 signature.")
    return raw


class TrustedReportSigner:
    """Sign only reports authorized by a verifier-signed, exact-digest attestation.

    The verifier trust pin, signer key ID, audience, clock, durable one-time
    authorization store, and KMS/HSM signing backend are all injected by the
    trusted deployment. Caller-supplied timestamps or keys are never accepted.
    """

    def __init__(
        self, *, verifier_id: str, verifier_key_id: str, audience: str, signing_key_id: str,
        attestation_verifier: VerifierAttestationVerifier,
        authorization_store: SigningAuthorizationStore,
        signing_backend: ReportSigningBackend,
        trusted_clock: Callable[[], datetime],
        max_attestation_lifetime_seconds: int = MAX_ATTESTATION_LIFETIME_SECONDS,
    ) -> None:
        _id(verifier_id, "Pinned verifier ID")
        _id(verifier_key_id, "Pinned verifier attestation key ID")
        _id(audience, "Pinned signer audience")
        _id(signing_key_id, "Pinned report signing key ID")
        if verifier_key_id == signing_key_id:
            raise TrustedReportSigningError("Verifier-attestation and report-signing keys must be distinct.")
        if not callable(getattr(attestation_verifier, "verify", None)):
            raise TrustedReportSigningError("Pinned verifier-attestation verification is required.")
        if not callable(getattr(authorization_store, "consume", None)):
            raise TrustedReportSigningError("A durable one-time authorization store is required.")
        if not callable(getattr(signing_backend, "sign", None)):
            raise TrustedReportSigningError("A protected KMS/HSM signing backend is required.")
        if not callable(trusted_clock):
            raise TrustedReportSigningError("A trusted host clock is required.")
        if (
            isinstance(max_attestation_lifetime_seconds, bool)
            or not isinstance(max_attestation_lifetime_seconds, int)
            or not 1 <= max_attestation_lifetime_seconds <= MAX_ATTESTATION_LIFETIME_SECONDS
        ):
            raise TrustedReportSigningError("Attestation lifetime must be between 1 and 120 seconds.")
        self._verifier_id = verifier_id
        self._verifier_key_id = verifier_key_id
        self._audience = audience
        self._key_id = signing_key_id
        self._attestation_verifier = attestation_verifier
        self._authorization_store = authorization_store
        self._signing_backend = signing_backend
        self._clock = trusted_clock
        self._max_lifetime = max_attestation_lifetime_seconds

    def sign(
        self, report_bytes: bytes, attestation_bytes: bytes,
        envelope_manifest_bytes: bytes,
    ) -> SignedAcceptanceReport:
        report = _parse_canonical(report_bytes, maximum=MAX_REPORT_BYTES, label="Acceptance report")
        if frozenset(report) != _V3_REPORT_FIELDS:
            raise TrustedReportSigningError("Report fields do not match the strict schema-v3 contract.")
        if type(report.get("schema_version")) is not int or report["schema_version"] != 3:
            raise TrustedReportSigningError("Only canonical schema-v3 acceptance reports may be signed.")
        if report.get("suite_id") != SUITE_ID or report.get("suite_version") != SUITE_VERSION:
            raise TrustedReportSigningError("Report suite identity/version is not pinned.")
        if report.get("key_id") != self._key_id:
            raise TrustedReportSigningError("Report key ID does not match the signer's pinned key.")
        probes = report.get("probes")
        if not isinstance(probes, list) or len(probes) != len(REQUIRED_PROBES):
            raise TrustedReportSigningError("Report does not contain the exact required probe inventory.")
        seen_probes = []
        for probe in probes:
            if not isinstance(probe, dict) or frozenset(probe) != _PROBE_FIELDS:
                raise TrustedReportSigningError("Report contains a malformed probe record.")
            probe_id = probe.get("probe_id")
            if (
                not isinstance(probe_id, str) or probe.get("outcome") != "pass"
                or not isinstance(probe.get("evidence_sha256"), str)
                or not _SHA256.fullmatch(probe["evidence_sha256"])
            ):
                raise TrustedReportSigningError("Every required report probe must have a valid digest and pass outcome.")
            seen_probes.append(probe_id)
        if seen_probes != sorted(REQUIRED_PROBES):
            raise TrustedReportSigningError("Report probe inventory is unknown, duplicated, or not canonical.")
        provenance = report.get("observer_provenance")
        if not isinstance(provenance, list):
            raise TrustedReportSigningError("Report observer provenance must be a canonical list.")
        if report.get("observer_provenance_sha256") != hashlib.sha256(_canonical(provenance)).hexdigest():
            raise TrustedReportSigningError("Report observer provenance digest does not match its contents.")
        if (
            type(report.get("observer_envelope_manifest_version")) is not int
            or report["observer_envelope_manifest_version"] != 1
        ):
            raise TrustedReportSigningError("Report envelope-manifest version 1 is required.")
        if (
            not isinstance(envelope_manifest_bytes, bytes)
            or not envelope_manifest_bytes
            or len(envelope_manifest_bytes) > MAX_MANIFEST_BYTES
        ):
            raise TrustedReportSigningError("Exact envelope-manifest bytes are required and bounded.")

        attestation = _parse_canonical(
            attestation_bytes, maximum=MAX_ATTESTATION_BYTES,
            label="Verifier authorization attestation",
        )
        if frozenset(attestation) != _ATTESTATION_FIELDS:
            raise TrustedReportSigningError("Verifier attestation fields do not match the strict schema.")
        if type(attestation["schema_version"]) is not int or attestation["schema_version"] != 1:
            raise TrustedReportSigningError("Verifier attestation schema version 1 is required.")
        if attestation["signature_algorithm"] != "Ed25519":
            raise TrustedReportSigningError("Only Ed25519 verifier attestations are accepted.")

        _id(attestation["verifier_id"], "Attestation verifier ID")
        _id(attestation["verifier_key_id"], "Attestation verifier key ID")
        _id(attestation["audience"], "Attestation audience")
        _id(attestation["verification_id"], "Attestation verification ID")
        _digest(attestation["report_sha256"], "Attested report digest")
        _digest(attestation["envelope_manifest_sha256"], "Attested envelope-manifest digest")
        report_digest = hashlib.sha256(report_bytes).hexdigest()
        manifest_digest = hashlib.sha256(envelope_manifest_bytes).hexdigest()
        if report.get("observer_envelope_manifest_sha256") != manifest_digest:
            raise TrustedReportSigningError("Report does not bind the exact supplied envelope-manifest bytes.")
        if (
            attestation["verifier_id"] != self._verifier_id
            or attestation["verifier_key_id"] != self._verifier_key_id
            or attestation["audience"] != self._audience
            or attestation["report_sha256"] != report_digest
            or attestation["envelope_manifest_sha256"] != manifest_digest
        ):
            raise TrustedReportSigningError("Verifier attestation does not authorize these exact report/manifest bytes.")

        issued = _utc(attestation["issued_at"], "Attestation issued_at")
        expires = _utc(attestation["expires_at"], "Attestation expires_at")
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise TrustedReportSigningError("Trusted signer clock must return timezone-aware UTC.")
        now = now.astimezone(timezone.utc).replace(microsecond=0)
        lifetime = (expires - issued).total_seconds()
        if lifetime < 1 or lifetime > self._max_lifetime:
            raise TrustedReportSigningError("Verifier attestation lifetime is invalid or exceeds its hard limit.")
        if issued > now or expires <= now:
            raise TrustedReportSigningError("Verifier attestation is future-issued or expired.")

        unsigned = dict(attestation)
        signature = _decode_signature(unsigned.pop("signature_b64"))
        signed_message = _canonical(unsigned)
        try:
            valid = self._attestation_verifier.verify(
                self._verifier_id, self._verifier_key_id, signed_message, signature
            )
        except Exception as exc:
            raise TrustedReportSigningError("Verifier attestation verification failed closed.") from exc
        if valid is not True:
            raise TrustedReportSigningError("Verifier attestation signature is invalid.")

        try:
            consumed = self._authorization_store.consume(
                verifier_id=self._verifier_id,
                verifier_key_id=self._verifier_key_id,
                audience=self._audience,
                verification_id=attestation["verification_id"],
                report_sha256=report_digest,
                envelope_manifest_sha256=manifest_digest,
                accepted_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                expires_at=attestation["expires_at"],
            )
        except Exception as exc:
            raise TrustedReportSigningError("Durable one-time authorization store failed closed.") from exc
        if consumed is not True:
            raise TrustedReportSigningError("Verifier attestation was already consumed or could not be durably claimed.")

        try:
            signed = self._signing_backend.sign(self._key_id, report_bytes)
        except Exception as exc:
            raise TrustedReportSigningError("Protected report signing backend failed closed.") from exc
        if not isinstance(signed, bytes) or len(signed) != 64:
            raise TrustedReportSigningError("Ed25519 signing backend did not return exactly 64 signature bytes.")
        return SignedAcceptanceReport(
            report_bytes=report_bytes,
            report_sha256=report_digest,
            key_id=self._key_id,
            signature=signed,
        )
