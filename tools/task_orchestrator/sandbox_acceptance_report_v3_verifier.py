"""Independent schema-v3 acceptance report verifier.

The verifier accepts only exact report/evidence/envelope/manifest bytes and
pinned host expectations. It reconstructs verifier-result adapters from raw
envelopes plus read-only replay receipts, then delegates full cross-binding and
independent observer-signature checks to the pure v3 builder before checking
the acceptance-report signature. It performs no signing or execution.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol

from tools.task_orchestrator.sandbox_acceptance import (
    MAX_REPORT_BYTES,
    MAX_SIGNATURE_BYTES,
    REQUIRED_PROBES,
)
from tools.task_orchestrator.sandbox_acceptance_provenance import (
    AcceptanceProvenanceExpectation,
    _parse_canonical_object,
)
from tools.task_orchestrator.sandbox_acceptance_report_v3 import (
    AcceptanceReportV3Error,
    ObserverReplayReceiptReader,
    _decode_b64,
    _parse_envelope,
    build_schema_v3_report_draft,
)
from tools.task_orchestrator.sandbox_host_evidence import ProbeObservation, _required_domains
from tools.task_orchestrator.sandbox_observer_auth import (
    AuthenticatedObserverResult,
    ObserverReplayReceipt,
    ObserverSignatureVerifier,
    PinnedObserverRegistry,
)

_V3_REPORT_KEYS = frozenset({
    "schema_version", "suite_id", "suite_version", "key_id", "provider_id",
    "region", "runtime_id", "task_id", "attempt_id", "image_digest",
    "policy_digest", "started_at", "completed_at", "probes",
    "observer_registry_sha256", "observer_registry_version",
    "observer_provenance_sha256", "observer_provenance",
    "observer_envelope_manifest_version", "observer_envelope_manifest_sha256",
})
MAX_ENVELOPE_MANIFEST_BYTES = 256 * 1024


class AcceptanceReportV3SignatureVerifier(Protocol):
    """Verifier backed by the separately pinned acceptance-report trust key."""

    def verify(self, key_id: str, message: bytes, signature: bytes) -> bool: ...


def verify_signed_acceptance_report_v3(
    report_bytes: bytes,
    signature: bytes | None,
    expectation: AcceptanceProvenanceExpectation,
    report_signature_verifier: AcceptanceReportV3SignatureVerifier | None,
    *,
    probe_evidence: Mapping[str, bytes],
    raw_observer_envelopes: Mapping[tuple[str, str], bytes],
    envelope_manifest_bytes: bytes,
    registry: PinnedObserverRegistry,
    observer_signature_verifier: ObserverSignatureVerifier,
    replay_receipt_reader: ObserverReplayReceiptReader,
) -> dict[str, Any]:
    """Independently verify report contents and, when supplied, its signature.

    Passing both signature and report_signature_verifier as None performs the
    pre-signing content/evidence verification used to authorize the separate
    report signer. A supplied signature is verified after exact reconstruction.
    No caller-created AuthenticatedObserverResult is accepted as input.
    """
    expectation.validate()
    if not isinstance(report_bytes, bytes) or not report_bytes or len(report_bytes) > MAX_REPORT_BYTES:
        raise AcceptanceReportV3Error("Schema-v3 report is empty or oversized.")
    if signature is not None and (
        not isinstance(signature, bytes) or not signature or len(signature) > MAX_SIGNATURE_BYTES
    ):
        raise AcceptanceReportV3Error("Schema-v3 report signature is malformed or oversized.")
    if (
        not isinstance(envelope_manifest_bytes, bytes)
        or not envelope_manifest_bytes
        or len(envelope_manifest_bytes) > MAX_ENVELOPE_MANIFEST_BYTES
    ):
        raise AcceptanceReportV3Error("Raw observer-envelope manifest is missing or oversized.")
    if signature is None:
        if report_signature_verifier is not None:
            raise AcceptanceReportV3Error("A report signature verifier cannot be supplied without a report signature.")
    elif not callable(getattr(report_signature_verifier, "verify", None)):
        raise AcceptanceReportV3Error("A trusted acceptance-report signature verifier is required.")
    if not isinstance(registry, PinnedObserverRegistry):
        raise AcceptanceReportV3Error("A pinned observer registry is required.")

    report = _parse_canonical_object(report_bytes, label="Schema-v3 acceptance report")
    if frozenset(report) != _V3_REPORT_KEYS:
        raise AcceptanceReportV3Error("Schema-v3 report fields do not match the strict schema.")
    if type(report["schema_version"]) is not int or report["schema_version"] != 3:
        raise AcceptanceReportV3Error("Schema-v3 acceptance report is required.")
    if report["key_id"] != expectation.acceptance.trusted_key_id:
        raise AcceptanceReportV3Error("Schema-v3 report key ID does not match the pinned acceptance key.")
    if (
        type(report["observer_envelope_manifest_version"]) is not int
        or report["observer_envelope_manifest_version"] != 1
    ):
        raise AcceptanceReportV3Error("Observer-envelope manifest version 1 is required.")
    if hashlib.sha256(envelope_manifest_bytes).hexdigest() != report["observer_envelope_manifest_sha256"]:
        raise AcceptanceReportV3Error("Exact raw envelope-manifest digest does not match the signed report.")

    required_domains = _required_domains()
    required_pairs = {
        (probe_id, domain)
        for probe_id, domains in required_domains.items()
        for domain in domains
    }
    if (
        not isinstance(raw_observer_envelopes, Mapping)
        or set(raw_observer_envelopes) != required_pairs
        or not isinstance(probe_evidence, Mapping)
        or set(probe_evidence) != REQUIRED_PROBES
    ):
        raise AcceptanceReportV3Error("Raw evidence and envelope inventories must exactly match the pinned suite.")

    observer_results: dict[tuple[str, str], AuthenticatedObserverResult] = {}
    for pair in sorted(required_pairs):
        raw = raw_observer_envelopes[pair]
        envelope = _parse_envelope(raw)
        envelope_digest = hashlib.sha256(raw).hexdigest()
        observer_id = envelope["observer_id"]
        try:
            receipt = replay_receipt_reader.get_acceptance(
                observer_id=observer_id,
                envelope_sha256=envelope_digest,
            )
        except Exception as exc:
            raise AcceptanceReportV3Error("Read-only replay receipt lookup failed closed.") from exc
        if type(receipt) is not ObserverReplayReceipt:
            raise AcceptanceReportV3Error("Committed immutable replay receipt is missing.")
        nonce = _decode_b64(envelope["nonce_b64"], "Observer nonce", exact_length=32)
        payload = _decode_b64(envelope["payload_b64"], "Observer payload")
        observation = ProbeObservation(
            probe_id=envelope["probe_id"],
            observer_domain=envelope["observer_domain"],
            observer_id=observer_id,
            attempt_id=envelope["attempt_id"],
            runtime_id=envelope["runtime_id"],
            policy_digest=envelope["policy_digest"],
            monotonic_start_ns=envelope["monotonic_start_ns"],
            monotonic_end_ns=envelope["monotonic_end_ns"],
            observed_at=envelope["observed_at"],
            outcome=envelope["outcome"],
            payload=payload,
        )
        observer_results[pair] = AuthenticatedObserverResult(
            observation=observation,
            observer_registry_sha256=receipt.observer_registry_sha256,
            observer_registry_version=receipt.observer_registry_version,
            key_id=envelope["key_id"],
            sequence=envelope["sequence"],
            nonce_sha256=hashlib.sha256(nonce).hexdigest(),
            envelope_sha256=envelope_digest,
            challenge_expires_at=receipt.challenge_expires_at,
            accepted_at=receipt.accepted_at,
            ledger_revision=receipt.ledger_revision,
            fencing_epoch=receipt.fencing_epoch,
        )

    draft = build_schema_v3_report_draft(
        expectation,
        started_at=report["started_at"],
        completed_at=report["completed_at"],
        probe_evidence=probe_evidence,
        observer_results=observer_results,
        raw_observer_envelopes=raw_observer_envelopes,
        registry=registry,
        observer_signature_verifier=observer_signature_verifier,
        replay_receipt_reader=replay_receipt_reader,
    )
    if draft.report_bytes != report_bytes:
        raise AcceptanceReportV3Error("Schema-v3 report differs from independently reconstructed bytes.")
    if draft.envelope_manifest_bytes != envelope_manifest_bytes:
        raise AcceptanceReportV3Error("Raw observer-envelope manifest differs from independently reconstructed bytes.")

    signature_verified = False
    if signature is not None:
        try:
            verified = report_signature_verifier.verify(
                expectation.acceptance.trusted_key_id,
                report_bytes,
                signature,
            )
        except Exception as exc:
            raise AcceptanceReportV3Error("Acceptance-report signature verification failed closed.") from exc
        if verified is not True:
            raise AcceptanceReportV3Error("Schema-v3 acceptance-report signature is invalid.")
        signature_verified = True

    return {
        "schema_version": 3,
        "status": "runtime_acceptance_evidence_verified_with_observer_provenance_and_retained_envelopes",
        "suite_id": report["suite_id"],
        "suite_version": report["suite_version"],
        "provider_id": report["provider_id"],
        "region": report["region"],
        "runtime_id": report["runtime_id"],
        "task_id": report["task_id"],
        "attempt_id": report["attempt_id"],
        "image_digest": report["image_digest"],
        "policy_digest": report["policy_digest"],
        "probe_count": draft.probe_count,
        "observer_count": draft.observer_count,
        "evidence_bytes_total": draft.evidence_bytes_total,
        "envelope_bytes_total": draft.envelope_bytes_total,
        "report_sha256": draft.report_sha256,
        "observer_provenance_sha256": draft.observer_provenance_sha256,
        "observer_envelope_manifest_sha256": draft.observer_envelope_manifest_sha256,
        "content_verified": True,
        "report_signature_verified": signature_verified,
        "signature_verified": signature_verified,
        "execution_authorized": False,
        "eligible_for_untrusted_execution": False,
        "patch_applied": False,
    }


def verify_unsigned_acceptance_report_v3_for_signing(
    report_bytes: bytes,
    expectation: AcceptanceProvenanceExpectation,
    *,
    probe_evidence: Mapping[str, bytes],
    raw_observer_envelopes: Mapping[tuple[str, str], bytes],
    envelope_manifest_bytes: bytes,
    registry: PinnedObserverRegistry,
    observer_signature_verifier: ObserverSignatureVerifier,
    replay_receipt_reader: ObserverReplayReceiptReader,
) -> dict[str, Any]:
    """Verify exact report contents/evidence before the report signature exists."""
    return verify_signed_acceptance_report_v3(
        report_bytes,
        None,
        expectation,
        None,
        probe_evidence=probe_evidence,
        raw_observer_envelopes=raw_observer_envelopes,
        envelope_manifest_bytes=envelope_manifest_bytes,
        registry=registry,
        observer_signature_verifier=observer_signature_verifier,
        replay_receipt_reader=replay_receipt_reader,
    )


class VerifierAttestationSigningBackend(Protocol):
    """Separate protected signer for verifier authorization attestations."""

    def sign(self, key_id: str, message: bytes) -> bytes: ...


@dataclass(frozen=True)
class VerificationAttestation:
    """Result of successful independent report verification and authorization."""

    verification_result: Mapping[str, Any]
    attestation_bytes: bytes
    verification_id: str


class SchemaV3VerificationAttestor:
    """Issue short-lived report-signing authorization only after full content verification.

    Deploy this adapter inside the independently administered verifier
    workload. Its attestation key must be distinct from the acceptance-report
    key and held by a separate KMS/HSM policy. No private key is loaded here.
    """

    def __init__(
        self, *, verifier_id: str, verifier_key_id: str, audience: str,
        attestation_signer: VerifierAttestationSigningBackend,
        trusted_clock,
        lifetime_seconds: int = 60,
    ) -> None:
        identifier = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
        for value, label in (
            (verifier_id, "verifier ID"),
            (verifier_key_id, "verifier key ID"),
            (audience, "verifier audience"),
        ):
            if not isinstance(value, str) or not identifier.fullmatch(value):
                raise AcceptanceReportV3Error(f"Pinned {label} is invalid.")
        if not callable(getattr(attestation_signer, "sign", None)):
            raise AcceptanceReportV3Error("A protected verifier-attestation signing backend is required.")
        if not callable(trusted_clock):
            raise AcceptanceReportV3Error("A trusted verifier clock is required.")
        if (
            isinstance(lifetime_seconds, bool) or not isinstance(lifetime_seconds, int)
            or not 1 <= lifetime_seconds <= 120
        ):
            raise AcceptanceReportV3Error("Verifier attestation lifetime must be between 1 and 120 seconds.")
        self._verifier_id = verifier_id
        self._verifier_key_id = verifier_key_id
        self._audience = audience
        self._signer = attestation_signer
        self._clock = trusted_clock
        self._lifetime = lifetime_seconds

    def verify_and_attest(
        self,
        report_bytes: bytes,
        expectation: AcceptanceProvenanceExpectation,
        *,
        probe_evidence: Mapping[str, bytes],
        raw_observer_envelopes: Mapping[tuple[str, str], bytes],
        envelope_manifest_bytes: bytes,
        registry: PinnedObserverRegistry,
        observer_signature_verifier: ObserverSignatureVerifier,
        replay_receipt_reader: ObserverReplayReceiptReader,
    ) -> VerificationAttestation:
        expectation.validate()
        if self._verifier_key_id == expectation.acceptance.trusted_key_id:
            raise AcceptanceReportV3Error("Verifier-attestation and report-signing keys must be distinct.")
        result = verify_unsigned_acceptance_report_v3_for_signing(
            report_bytes,
            expectation,
            probe_evidence=probe_evidence,
            raw_observer_envelopes=raw_observer_envelopes,
            envelope_manifest_bytes=envelope_manifest_bytes,
            registry=registry,
            observer_signature_verifier=observer_signature_verifier,
            replay_receipt_reader=replay_receipt_reader,
        )
        if (
            result.get("content_verified") is not True
            or result.get("report_signature_verified") is not False
            or result.get("execution_authorized") is not False
            or result.get("eligible_for_untrusted_execution") is not False
            or result.get("patch_applied") is not False
            or result.get("schema_version") != 3
        ):
            raise AcceptanceReportV3Error("Independent content-verification result is not eligible for report-signing attestation.")

        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise AcceptanceReportV3Error("Trusted verifier clock must return timezone-aware UTC.")
        now = now.astimezone(timezone.utc).replace(microsecond=0)
        expires = now + timedelta(seconds=self._lifetime)
        try:
            verification_id = secrets.token_hex(32)
        except Exception as exc:
            raise AcceptanceReportV3Error("Verifier authorization ID CSPRNG failed closed.") from exc
        if not isinstance(verification_id, str) or not re.fullmatch(r"[0-9a-f]{64}", verification_id):
            raise AcceptanceReportV3Error("Verifier authorization ID must be 32 random bytes in lowercase hex.")

        unsigned = {
            "schema_version": 1,
            "verifier_id": self._verifier_id,
            "verifier_key_id": self._verifier_key_id,
            "audience": self._audience,
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "envelope_manifest_sha256": hashlib.sha256(envelope_manifest_bytes).hexdigest(),
            "verification_id": verification_id,
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "signature_algorithm": "Ed25519",
        }
        message = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        try:
            attestation_signature = self._signer.sign(self._verifier_key_id, message)
        except Exception as exc:
            raise AcceptanceReportV3Error("Protected verifier-attestation signing failed closed.") from exc
        if not isinstance(attestation_signature, bytes) or len(attestation_signature) != 64:
            raise AcceptanceReportV3Error("Verifier attestation signer must return exactly 64 Ed25519 signature bytes.")
        attested = dict(unsigned)
        attested["signature_b64"] = base64.b64encode(attestation_signature).decode("ascii")
        attestation_bytes = json.dumps(
            attested, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        return VerificationAttestation(
            verification_result=result,
            attestation_bytes=attestation_bytes,
            verification_id=verification_id,
        )
