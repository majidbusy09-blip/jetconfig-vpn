"""Independent schema-v3 acceptance report verifier.

The verifier accepts only exact report/evidence/envelope/manifest bytes and
pinned host expectations. It reconstructs verifier-result adapters from raw
envelopes plus read-only replay receipts, then delegates full cross-binding and
independent observer-signature checks to the pure v3 builder before checking
the acceptance-report signature. It performs no signing or execution.
"""
from __future__ import annotations

import hashlib
import json
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
    signature: bytes,
    expectation: AcceptanceProvenanceExpectation,
    report_signature_verifier: AcceptanceReportV3SignatureVerifier,
    *,
    probe_evidence: Mapping[str, bytes],
    raw_observer_envelopes: Mapping[tuple[str, str], bytes],
    envelope_manifest_bytes: bytes,
    registry: PinnedObserverRegistry,
    observer_signature_verifier: ObserverSignatureVerifier,
    replay_receipt_reader: ObserverReplayReceiptReader,
) -> dict[str, Any]:
    """Independently verify a signed v3 report and its exact retained envelope set.

    No caller-created AuthenticatedObserverResult is accepted as input. Adapter
    objects are reconstructed from the exact raw envelope and read-only receipt
    lookup, then the builder revalidates signatures, evidence, receipts, pins,
    and deterministic report/manifest bytes.
    """
    expectation.validate()
    if not isinstance(report_bytes, bytes) or not report_bytes or len(report_bytes) > MAX_REPORT_BYTES:
        raise AcceptanceReportV3Error("Schema-v3 report is empty or oversized.")
    if not isinstance(signature, bytes) or not signature or len(signature) > MAX_SIGNATURE_BYTES:
        raise AcceptanceReportV3Error("Schema-v3 report signature is missing or oversized.")
    if (
        not isinstance(envelope_manifest_bytes, bytes)
        or not envelope_manifest_bytes
        or len(envelope_manifest_bytes) > MAX_ENVELOPE_MANIFEST_BYTES
    ):
        raise AcceptanceReportV3Error("Raw observer-envelope manifest is missing or oversized.")
    if not callable(getattr(report_signature_verifier, "verify", None)):
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
        raise AcceptanceReportV3Error("Signed schema-v3 report differs from independently reconstructed bytes.")
    if draft.envelope_manifest_bytes != envelope_manifest_bytes:
        raise AcceptanceReportV3Error("Raw observer-envelope manifest differs from independently reconstructed bytes.")

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
        "signature_verified": True,
        "execution_authorized": False,
        "eligible_for_untrusted_execution": False,
        "patch_applied": False,
    }
