"""Schema-v2 signed acceptance verifier binding observer provenance to raw evidence.

Schema v1 remains unchanged in sandbox_acceptance.py. This module requires the
observer registry pin and verifies every provenance record against the exact
host-assembled probe evidence bytes before accepting the report signature.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from tools.task_orchestrator.sandbox_acceptance import (
    AcceptanceExpectation,
    MAX_PROBE_EVIDENCE_BYTES,
    MAX_REPORT_BYTES,
    MAX_SIGNATURE_BYTES,
    REQUIRED_PROBES,
    SUITE_ID,
    SUITE_VERSION,
    SignatureVerifier,
    SandboxEvidenceError,
    _parse_utc,
    _validate_digest,
    _validate_text,
    canonical_report_bytes,
)
from tools.task_orchestrator.sandbox_host_evidence import _required_domains

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TOP_LEVEL_KEYS_V2 = frozenset({
    "schema_version", "suite_id", "suite_version", "key_id", "provider_id",
    "region", "runtime_id", "task_id", "attempt_id", "image_digest",
    "policy_digest", "started_at", "completed_at", "probes",
    "observer_registry_sha256", "observer_registry_version",
    "observer_provenance_sha256", "observer_provenance",
})
_PROBE_KEYS = frozenset({"probe_id", "outcome", "evidence_sha256"})
_EVIDENCE_KEYS = frozenset({
    "schema_version", "suite_id", "suite_version", "attempt_id", "runtime_id",
    "policy_digest", "probe_id", "observations",
})
_OBSERVATION_KEYS = frozenset({
    "observer_domain", "observer_id", "runtime_id", "policy_digest",
    "monotonic_start_ns", "monotonic_end_ns", "observed_at", "outcome",
    "payload_b64", "payload_sha256",
})
_PROVENANCE_KEYS = frozenset({
    "probe_id", "observer_domain", "observer_id", "key_id",
    "observer_registry_sha256", "observer_registry_version", "sequence",
    "nonce_sha256", "envelope_sha256", "payload_sha256", "signature_algorithm",
})


class AcceptanceProvenanceError(ValueError):
    """Schema-v2 report or observer provenance is malformed or inconsistent."""


@dataclass(frozen=True)
class AcceptanceProvenanceExpectation:
    acceptance: AcceptanceExpectation
    observer_registry_sha256: str
    observer_registry_version: int

    def validate(self) -> None:
        if not isinstance(self.acceptance, AcceptanceExpectation):
            raise AcceptanceProvenanceError("Base acceptance expectation is required.")
        self.acceptance.validate()
        if not isinstance(self.observer_registry_sha256, str) or not _SHA256_RE.fullmatch(self.observer_registry_sha256):
            raise AcceptanceProvenanceError("An independently pinned observer registry digest is required.")
        if (
            isinstance(self.observer_registry_version, bool)
            or not isinstance(self.observer_registry_version, int)
            or self.observer_registry_version < 1
        ):
            raise AcceptanceProvenanceError("Pinned observer registry version must be a positive integer.")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AcceptanceProvenanceError("Signed acceptance data contains duplicate JSON keys.")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise AcceptanceProvenanceError("Signed acceptance data contains a non-finite JSON value.")


def _parse_canonical_object(raw: bytes, *, label: str, ascii_only: bool = False) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("ascii" if ascii_only else "utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except AcceptanceProvenanceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AcceptanceProvenanceError(f"{label} is not valid bounded canonical JSON.") from exc
    if not isinstance(value, dict):
        raise AcceptanceProvenanceError(f"{label} must be a JSON object.")
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only, allow_nan=False
        ).encode("ascii" if ascii_only else "utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise AcceptanceProvenanceError(f"{label} cannot be canonically encoded.") from exc
    if canonical != raw:
        raise AcceptanceProvenanceError(f"{label} is not in canonical signed form.")
    return value


def _decode_payload(value: Any, probe_id: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 64 * 1024:
        raise AcceptanceProvenanceError(f"Observation payload is missing or oversized: {probe_id}.")
    try:
        payload = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AcceptanceProvenanceError(f"Observation payload is not strict base64: {probe_id}.") from exc
    if base64.b64encode(payload).decode("ascii") != value or not payload:
        raise AcceptanceProvenanceError(f"Observation payload is not canonical non-empty base64: {probe_id}.")
    if len(payload) > 48 * 1024:
        raise AcceptanceProvenanceError(f"Observation payload exceeds the raw payload limit: {probe_id}.")
    return payload


def verify_signed_acceptance_report_v2(
    report_bytes: bytes,
    signature: bytes,
    expectation: AcceptanceProvenanceExpectation,
    verifier: SignatureVerifier,
    *,
    probe_evidence: Mapping[str, bytes],
) -> dict[str, Any]:
    """Verify a schema-v2 report and cross-bind signed observer provenance.

    The report signature covers provenance records. Each record is independently
    cross-checked against the observer identity/domain and payload digest inside
    the exact raw evidence blob whose SHA-256 is also signed in the report.
    """
    expectation.validate()
    base = expectation.acceptance
    if not isinstance(report_bytes, bytes) or not report_bytes or len(report_bytes) > MAX_REPORT_BYTES:
        raise AcceptanceProvenanceError("Schema-v2 report is empty or exceeds the size limit.")
    if not isinstance(signature, bytes) or not signature or len(signature) > MAX_SIGNATURE_BYTES:
        raise AcceptanceProvenanceError("Schema-v2 report signature is missing or oversized.")
    if not isinstance(verifier, SignatureVerifier):
        raise AcceptanceProvenanceError("A trusted report signature verifier is required.")
    if not isinstance(probe_evidence, Mapping) or set(probe_evidence) != REQUIRED_PROBES:
        raise AcceptanceProvenanceError("Raw evidence inventory must exactly match the required probes.")

    report = _parse_canonical_object(report_bytes, label="Schema-v2 report")
    if frozenset(report) != _TOP_LEVEL_KEYS_V2:
        raise AcceptanceProvenanceError("Schema-v2 report fields do not match the strict schema.")
    if type(report["schema_version"]) is not int or report["schema_version"] != 2:
        raise AcceptanceProvenanceError("Acceptance report schema version 2 is required.")
    if report["suite_id"] != SUITE_ID or report["suite_version"] != SUITE_VERSION:
        raise AcceptanceProvenanceError("Acceptance report suite identity or version is not pinned.")
    if report["key_id"] != base.trusted_key_id:
        raise AcceptanceProvenanceError("Acceptance report signing key is not the pinned trusted key.")

    for field in ("provider_id", "region", "runtime_id", "task_id", "attempt_id", "key_id"):
        _validate_text(report[field], field)
    for field in ("image_digest", "policy_digest"):
        _validate_digest(report[field], field)
    expected_bindings = {
        "provider_id": base.provider_id,
        "region": base.region,
        "task_id": base.task_id,
        "attempt_id": base.attempt_id,
        "image_digest": base.image_digest,
        "policy_digest": base.policy_digest,
    }
    for field, expected in expected_bindings.items():
        if report[field] != expected:
            raise AcceptanceProvenanceError(f"Acceptance report {field} does not match the pinned attempt.")

    started = _parse_utc(report["started_at"], "started_at")
    completed = _parse_utc(report["completed_at"], "completed_at")
    now = base.now.astimezone(__import__("datetime").timezone.utc)
    if completed < started:
        raise AcceptanceProvenanceError("Acceptance report completion precedes its start.")
    if (completed - started).total_seconds() > base.max_suite_duration_seconds:
        raise AcceptanceProvenanceError("Acceptance suite exceeded its maximum duration.")
    if completed > now + timedelta(seconds=base.allowed_clock_skew_seconds):
        raise AcceptanceProvenanceError("Acceptance report completion timestamp is in the future.")
    if (now - completed).total_seconds() > base.max_age_seconds:
        raise AcceptanceProvenanceError("Acceptance report is stale and must be rerun.")

    registry_digest = report["observer_registry_sha256"]
    registry_version = report["observer_registry_version"]
    if registry_digest != expectation.observer_registry_sha256:
        raise AcceptanceProvenanceError("Report observer registry digest does not match the protected pin.")
    if (
        isinstance(registry_version, bool) or not isinstance(registry_version, int)
        or registry_version != expectation.observer_registry_version
    ):
        raise AcceptanceProvenanceError("Report observer registry version does not match the protected pin.")

    provenance = report["observer_provenance"]
    if not isinstance(provenance, list) or not provenance:
        raise AcceptanceProvenanceError("Signed observer provenance inventory is required.")
    provenance_digest = report["observer_provenance_sha256"]
    if not isinstance(provenance_digest, str) or not _SHA256_RE.fullmatch(provenance_digest):
        raise AcceptanceProvenanceError("Observer provenance digest is invalid.")
    canonical_provenance = json.dumps(
        provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if hashlib.sha256(canonical_provenance).hexdigest() != provenance_digest:
        raise AcceptanceProvenanceError("Observer provenance digest does not match the signed inventory.")

    required_domains = _required_domains()
    expected_provenance: dict[tuple[str, str], dict[str, Any]] = {}
    seen_nonces: set[str] = set()
    seen_envelopes: set[str] = set()
    seen_sequences: set[tuple[str, int]] = set()
    previous_sort_key: tuple[str, str] | None = None
    for record in provenance:
        if not isinstance(record, dict) or frozenset(record) != _PROVENANCE_KEYS:
            raise AcceptanceProvenanceError("Observer provenance record does not match the strict schema.")
        probe_id = record["probe_id"]
        domain = record["observer_domain"]
        _validate_text(probe_id, "observer provenance probe_id")
        _validate_text(domain, "observer provenance observer_domain")
        if probe_id not in REQUIRED_PROBES or domain not in required_domains[probe_id]:
            raise AcceptanceProvenanceError("Observer provenance references an unauthorized probe/domain.")
        sort_key = (probe_id, domain)
        if previous_sort_key is not None and sort_key <= previous_sort_key:
            raise AcceptanceProvenanceError("Observer provenance records must be uniquely sorted by probe and domain.")
        previous_sort_key = sort_key
        if sort_key in expected_provenance:
            raise AcceptanceProvenanceError("Duplicate observer provenance record.")
        observer_id = record["observer_id"]
        key_id = record["key_id"]
        _validate_text(observer_id, "observer provenance observer_id")
        _validate_text(key_id, "observer provenance key_id")
        if record["observer_registry_sha256"] != registry_digest:
            raise AcceptanceProvenanceError("Observer provenance registry digest mismatch.")
        if (
            isinstance(record["observer_registry_version"], bool)
            or not isinstance(record["observer_registry_version"], int)
            or record["observer_registry_version"] != registry_version
        ):
            raise AcceptanceProvenanceError("Observer provenance registry version mismatch.")
        sequence = record["sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or not 1 <= sequence <= 2**63 - 1:
            raise AcceptanceProvenanceError("Observer provenance sequence is invalid.")
        nonce_digest = record["nonce_sha256"]
        envelope_digest = record["envelope_sha256"]
        payload_digest = record["payload_sha256"]
        for value, field in (
            (nonce_digest, "nonce_sha256"),
            (envelope_digest, "envelope_sha256"),
            (payload_digest, "payload_sha256"),
        ):
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise AcceptanceProvenanceError(f"Observer provenance {field} is invalid.")
        if record["signature_algorithm"] != "Ed25519":
            raise AcceptanceProvenanceError("Only Ed25519 observer provenance is accepted.")
        sequence_key = (observer_id, sequence)
        if nonce_digest in seen_nonces or envelope_digest in seen_envelopes or sequence_key in seen_sequences:
            raise AcceptanceProvenanceError("Observer provenance contains replayed nonce/envelope/sequence data.")
        seen_nonces.add(nonce_digest)
        seen_envelopes.add(envelope_digest)
        seen_sequences.add(sequence_key)
        expected_provenance[sort_key] = record

    probes = report["probes"]
    if not isinstance(probes, list) or len(probes) != len(REQUIRED_PROBES):
        raise AcceptanceProvenanceError("Schema-v2 report lacks the exact required probe inventory.")
    if [item.get("probe_id") if isinstance(item, dict) else None for item in probes] != sorted(REQUIRED_PROBES):
        raise AcceptanceProvenanceError("Schema-v2 probe records must be uniquely sorted by probe ID.")
    evidence_total = 0
    seen_probes: set[str] = set()
    expected_pairs: set[tuple[str, str]] = set()
    for probe in probes:
        if not isinstance(probe, dict) or frozenset(probe) != _PROBE_KEYS:
            raise AcceptanceProvenanceError("Schema-v2 report contains a malformed probe record.")
        probe_id = probe["probe_id"]
        _validate_text(probe_id, "probe_id")
        if probe_id not in REQUIRED_PROBES or probe_id in seen_probes:
            raise AcceptanceProvenanceError("Schema-v2 report contains an unknown or duplicate probe.")
        seen_probes.add(probe_id)
        if probe["outcome"] != "pass":
            raise AcceptanceProvenanceError(f"Required sandbox probe did not pass: {probe_id}.")
        digest = probe["evidence_sha256"]
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise AcceptanceProvenanceError(f"Probe evidence digest is invalid: {probe_id}.")
        raw = probe_evidence[probe_id]
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_PROBE_EVIDENCE_BYTES:
            raise AcceptanceProvenanceError(f"Raw probe evidence is missing, invalid, or oversized: {probe_id}.")
        evidence_total += len(raw)
        if evidence_total > 2 * 1024 * 1024:
            raise AcceptanceProvenanceError("Raw probe evidence exceeds the aggregate size limit.")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise AcceptanceProvenanceError(f"Raw probe evidence digest does not match the signed report: {probe_id}.")

        evidence_doc = _parse_canonical_object(raw, label=f"Raw probe evidence {probe_id}", ascii_only=True)
        if frozenset(evidence_doc) != _EVIDENCE_KEYS:
            raise AcceptanceProvenanceError(f"Raw probe evidence fields do not match the strict schema: {probe_id}.")
        if (
            type(evidence_doc["schema_version"]) is not int or evidence_doc["schema_version"] != 1
            or evidence_doc["suite_id"] != SUITE_ID or evidence_doc["suite_version"] != SUITE_VERSION
            or evidence_doc["attempt_id"] != base.attempt_id
            or evidence_doc["runtime_id"] != report["runtime_id"]
            or evidence_doc["policy_digest"] != base.policy_digest
            or evidence_doc["probe_id"] != probe_id
        ):
            raise AcceptanceProvenanceError(f"Raw probe evidence context does not match the signed attempt: {probe_id}.")
        observations = evidence_doc["observations"]
        domains = sorted(required_domains[probe_id])
        if not isinstance(observations, list) or len(observations) != len(domains):
            raise AcceptanceProvenanceError(f"Raw probe evidence observer inventory is incomplete: {probe_id}.")
        actual_domains: list[str] = []
        for observation in observations:
            if not isinstance(observation, dict) or frozenset(observation) != _OBSERVATION_KEYS:
                raise AcceptanceProvenanceError(f"Raw probe evidence observation is malformed: {probe_id}.")
            domain = observation["observer_domain"]
            observer_id = observation["observer_id"]
            _validate_text(domain, "evidence observer_domain")
            _validate_text(observer_id, "evidence observer_id")
            if domain not in required_domains[probe_id]:
                raise AcceptanceProvenanceError(f"Raw evidence has an unauthorized observer domain: {probe_id}.")
            actual_domains.append(domain)
            if observation["runtime_id"] != report["runtime_id"] or observation["policy_digest"] != base.policy_digest:
                raise AcceptanceProvenanceError(f"Observation context does not match the signed attempt: {probe_id}.")
            if observation["outcome"] != "pass":
                raise AcceptanceProvenanceError(f"Observation did not pass: {probe_id}.")
            start_ns, end_ns = observation["monotonic_start_ns"], observation["monotonic_end_ns"]
            for value in (start_ns, end_ns):
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**63 - 1:
                    raise AcceptanceProvenanceError(f"Observation monotonic offset is invalid: {probe_id}.")
            if end_ns < start_ns:
                raise AcceptanceProvenanceError(f"Observation monotonic interval is reversed: {probe_id}.")
            observed_at = _parse_utc(observation["observed_at"], "observation observed_at")
            if observed_at > base.now.astimezone(__import__("datetime").timezone.utc) + timedelta(seconds=base.allowed_clock_skew_seconds):
                raise AcceptanceProvenanceError(f"Observation timestamp is in the future: {probe_id}.")
            payload = _decode_payload(observation["payload_b64"], probe_id)
            payload_digest = observation["payload_sha256"]
            if not isinstance(payload_digest, str) or not _SHA256_RE.fullmatch(payload_digest):
                raise AcceptanceProvenanceError(f"Observation payload digest is invalid: {probe_id}.")
            if hashlib.sha256(payload).hexdigest() != payload_digest:
                raise AcceptanceProvenanceError(f"Observation payload digest mismatch: {probe_id}.")
            record = expected_provenance.get((probe_id, domain))
            if record is None:
                raise AcceptanceProvenanceError(f"Observer provenance is missing for {probe_id}/{domain}.")
            if record["observer_id"] != observer_id or record["payload_sha256"] != payload_digest:
                raise AcceptanceProvenanceError(f"Observer provenance does not match raw evidence for {probe_id}/{domain}.")
            expected_pairs.add((probe_id, domain))
        if actual_domains != domains:
            raise AcceptanceProvenanceError(f"Raw probe evidence domains are not in canonical required order: {probe_id}.")
    if seen_probes != REQUIRED_PROBES:
        raise AcceptanceProvenanceError("Schema-v2 report is missing required probes.")
    if set(expected_provenance) != expected_pairs:
        raise AcceptanceProvenanceError("Observer provenance inventory does not exactly match raw evidence observations.")

    canonical = canonical_report_bytes(report)
    if canonical != report_bytes:
        raise AcceptanceProvenanceError("Schema-v2 report is not in canonical signed form.")
    try:
        verified = verifier.verify(base.trusted_key_id, canonical, signature)
    except Exception as exc:
        raise AcceptanceProvenanceError("Trusted schema-v2 report signature verification failed closed.") from exc
    if verified is not True:
        raise AcceptanceProvenanceError("Schema-v2 report signature is invalid.")

    return {
        "schema_version": 2,
        "status": "runtime_acceptance_evidence_verified_with_observer_provenance",
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "provider_id": report["provider_id"],
        "region": report["region"],
        "runtime_id": report["runtime_id"],
        "task_id": report["task_id"],
        "attempt_id": report["attempt_id"],
        "image_digest": report["image_digest"],
        "policy_digest": report["policy_digest"],
        "probe_count": len(seen_probes),
        "observer_provenance_count": len(expected_provenance),
        "observer_registry_sha256": registry_digest,
        "observer_registry_version": registry_version,
        "evidence_bytes_total": evidence_total,
        "probe_ids": sorted(seen_probes),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "observer_provenance_sha256": provenance_digest,
        "signature_verified": True,
        "execution_authorized": False,
        "eligible_for_untrusted_execution": False,
        "patch_applied": False,
    }
