"""Pure schema-v3 acceptance report draft builder.

This module performs no signing, filesystem access, network access, replay
consumption, provider operation, or execution. It revalidates exact retained
observer envelopes and read-only replay receipts before producing deterministic
canonical report and envelope-manifest bytes. Schema v1/v2 remain unchanged.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol

from tools.task_orchestrator.sandbox_acceptance import (
    MAX_PROBE_EVIDENCE_BYTES,
    MAX_REPORT_BYTES,
    MAX_TOTAL_EVIDENCE_BYTES,
    REQUIRED_PROBES,
    SUITE_ID,
    SUITE_VERSION,
    _parse_utc,
    _validate_digest,
    _validate_text,
    canonical_report_bytes,
)
from tools.task_orchestrator.sandbox_acceptance_provenance import (
    AcceptanceProvenanceError,
    AcceptanceProvenanceExpectation,
    _EVIDENCE_KEYS,
    _OBSERVATION_KEYS,
    _PROBE_KEYS,
    _parse_canonical_object,
)
from tools.task_orchestrator.sandbox_host_evidence import ProbeObservation, _required_domains
from tools.task_orchestrator.sandbox_observer_auth import (
    MAX_CHALLENGE_SECONDS,
    MAX_ENVELOPE_BYTES,
    MAX_PAYLOAD_BYTES,
    AuthenticatedObserverResult,
    ObserverReplayReceipt,
    ObserverSignatureVerifier,
    PinnedObserverRegistry,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_MICRO_RE = re.compile(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6}Z$")
_ENVELOPE_FIELDS = frozenset({
    "schema_version", "audience", "observer_id", "observer_domain", "key_id",
    "attempt_id", "runtime_id", "policy_digest", "probe_id", "nonce_b64",
    "sequence", "observed_at", "monotonic_start_ns", "monotonic_end_ns",
    "outcome", "payload_b64", "payload_sha256", "signature_b64",
})


class AcceptanceReportV3Error(ValueError):
    """Schema-v3 report inputs are missing, malformed, or inconsistent."""


class ObserverReplayReceiptReader(Protocol):
    """Read-only view of the committed replay ledger; never consumes a nonce."""

    def get_acceptance(
        self, *, observer_id: str, envelope_sha256: str
    ) -> ObserverReplayReceipt | None: ...


@dataclass(frozen=True)
class SchemaV3ReportDraft:
    """Deterministic unsigned report and pre-acceptance envelope manifest."""

    report_bytes: bytes
    envelope_manifest_bytes: bytes
    report_sha256: str
    observer_provenance_sha256: str
    observer_envelope_manifest_sha256: str
    probe_count: int
    observer_count: int
    evidence_bytes_total: int
    envelope_bytes_total: int
    signature_verified: bool = False
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False
    patch_applied: bool = False


def _canonical(value: Any, *, ascii_only: bool = False) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=ascii_only, allow_nan=False,
        ).encode("ascii" if ascii_only else "utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise AcceptanceReportV3Error("Input cannot be canonically encoded.") from exc


def _decode_b64(value: Any, field: str, *, exact_length: int | None = None) -> bytes:
    if not isinstance(value, str) or not value or len(value) > MAX_ENVELOPE_BYTES:
        raise AcceptanceReportV3Error(f"{field} is missing or oversized.")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AcceptanceReportV3Error(f"{field} is not strict base64.") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise AcceptanceReportV3Error(f"{field} is not canonical base64.")
    if exact_length is not None and len(decoded) != exact_length:
        raise AcceptanceReportV3Error(f"{field} has an invalid decoded length.")
    return decoded


def _parse_envelope(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ENVELOPE_BYTES:
        raise AcceptanceReportV3Error("Raw observer envelope is missing or oversized.")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except AcceptanceReportV3Error:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AcceptanceReportV3Error("Raw observer envelope is not bounded UTF-8 JSON.") from exc
    if not isinstance(value, dict) or _canonical(value) != raw:
        raise AcceptanceReportV3Error("Raw observer envelope must be canonical JSON.")
    if frozenset(value) != _ENVELOPE_FIELDS:
        raise AcceptanceReportV3Error("Raw observer envelope does not match the strict schema.")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise AcceptanceReportV3Error("Observer envelope schema version 1 is required.")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AcceptanceReportV3Error("Observer envelope contains duplicate JSON keys.")
        result[key] = value
    return result


def _reject_nonfinite(_: str) -> None:
    raise AcceptanceReportV3Error("Observer envelope contains a non-finite value.")


def _parse_accepted_at(value: Any) -> datetime:
    if not isinstance(value, str) or not _UTC_MICRO_RE.fullmatch(value):
        raise AcceptanceReportV3Error("Replay receipt accepted_at must use canonical UTC microsecond precision.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AcceptanceReportV3Error("Replay receipt accepted_at is invalid.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise AcceptanceReportV3Error("Replay receipt accepted_at must be UTC.")
    return parsed.astimezone(timezone.utc)


def _check_receipt(
    receipt: Any,
    *,
    result: AuthenticatedObserverResult,
    envelope: Mapping[str, Any],
    envelope_digest: str,
    registry: PinnedObserverRegistry,
    attempt_id: str,
    runtime_id: str,
    policy_digest: str,
) -> None:
    if type(receipt) is not ObserverReplayReceipt:
        raise AcceptanceReportV3Error("A committed immutable replay receipt is required.")
    observation = result.observation
    for field in ("sequence", "ledger_revision", "fencing_epoch"):
        value = getattr(result, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise AcceptanceReportV3Error(f"Authenticated observer result {field} is invalid.")
    nonce = _decode_b64(envelope["nonce_b64"], "Observer nonce", exact_length=32)
    accepted_at = _parse_accepted_at(receipt.accepted_at)
    expires_at = _parse_utc(receipt.challenge_expires_at, "challenge_expires_at")
    if accepted_at > expires_at or (expires_at - accepted_at).total_seconds() > MAX_CHALLENGE_SECONDS:
        raise AcceptanceReportV3Error("Replay receipt challenge expiry is invalid or exceeds its hard lifetime.")
    try:
        registry.resolve(
            observation.observer_id, observation.observer_domain,
            result.key_id, now=accepted_at,
        )
    except Exception as exc:
        raise AcceptanceReportV3Error("Observer identity was not valid at trusted acceptance time.") from exc

    expected = {
        "observer_id": observation.observer_id,
        "observer_domain": observation.observer_domain,
        "attempt_id": attempt_id,
        "runtime_id": runtime_id,
        "policy_digest": policy_digest,
        "probe_id": observation.probe_id,
        "observer_registry_sha256": registry.sha256,
        "observer_registry_version": registry.version,
        "key_id": result.key_id,
        "nonce_sha256": hashlib.sha256(nonce).hexdigest(),
        "sequence": envelope["sequence"],
        "envelope_sha256": envelope_digest,
        "challenge_expires_at": receipt.challenge_expires_at,
        "accepted_at": receipt.accepted_at,
    }
    if any(getattr(receipt, field) != value for field, value in expected.items()):
        raise AcceptanceReportV3Error("Replay receipt does not match the exact envelope and pinned attempt.")
    if (
        result.observer_registry_sha256 != registry.sha256
        or result.observer_registry_version != registry.version
        or result.sequence != envelope["sequence"]
        or result.nonce_sha256 != expected["nonce_sha256"]
        or result.envelope_sha256 != envelope_digest
        or result.challenge_expires_at != receipt.challenge_expires_at
        or result.accepted_at != receipt.accepted_at
        or result.ledger_revision != receipt.ledger_revision
        or result.fencing_epoch != receipt.fencing_epoch
    ):
        raise AcceptanceReportV3Error("Authenticated observer result does not match the committed receipt.")
    for field in ("ledger_revision", "fencing_epoch"):
        value = getattr(receipt, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise AcceptanceReportV3Error("Replay receipt lacks a positive ledger revision/fencing epoch.")


def build_schema_v3_report_draft(
    expectation: AcceptanceProvenanceExpectation,
    *,
    started_at: str,
    completed_at: str,
    probe_evidence: Mapping[str, bytes],
    observer_results: Mapping[tuple[str, str], AuthenticatedObserverResult],
    raw_observer_envelopes: Mapping[tuple[str, str], bytes],
    registry: PinnedObserverRegistry,
    observer_signature_verifier: ObserverSignatureVerifier,
    replay_receipt_reader: ObserverReplayReceiptReader,
) -> SchemaV3ReportDraft:
    """Build deterministic schema-v3 bytes after independent envelope/receipt checks.

    Inputs are exact raw bytes and pinned host expectations. The builder never
    consumes replay state and never signs; signing is a separate injected step.
    """
    expectation.validate()
    base = expectation.acceptance
    if not isinstance(registry, PinnedObserverRegistry):
        raise AcceptanceReportV3Error("A pinned observer registry is required.")
    if (
        registry.sha256 != expectation.observer_registry_sha256
        or registry.version != expectation.observer_registry_version
    ):
        raise AcceptanceReportV3Error("Observer registry does not match the protected expectation.")
    if not callable(getattr(observer_signature_verifier, "verify", None)):
        raise AcceptanceReportV3Error("An independent observer signature verifier is required.")
    if not callable(getattr(replay_receipt_reader, "get_acceptance", None)):
        raise AcceptanceReportV3Error("A read-only replay receipt reader is required.")
    if not isinstance(probe_evidence, Mapping) or set(probe_evidence) != REQUIRED_PROBES:
        raise AcceptanceReportV3Error("Raw evidence inventory must exactly match the 20 required probes.")

    required_domains = _required_domains()
    required_pairs = {
        (probe_id, domain)
        for probe_id, domains in required_domains.items()
        for domain in domains
    }
    if (
        not isinstance(observer_results, Mapping)
        or set(observer_results) != required_pairs
        or not isinstance(raw_observer_envelopes, Mapping)
        or set(raw_observer_envelopes) != required_pairs
    ):
        raise AcceptanceReportV3Error("Observer results and raw envelopes must exactly cover required probe/domain pairs.")

    started = _parse_utc(started_at, "started_at")
    completed = _parse_utc(completed_at, "completed_at")
    now = base.now.astimezone(timezone.utc)
    if completed < started or (completed - started).total_seconds() > base.max_suite_duration_seconds:
        raise AcceptanceReportV3Error("Suite time interval is reversed or exceeds the pinned duration.")
    if completed > now + timedelta(seconds=base.allowed_clock_skew_seconds):
        raise AcceptanceReportV3Error("Suite completion is in the future.")
    if (now - completed).total_seconds() > base.max_age_seconds:
        raise AcceptanceReportV3Error("Suite completion is stale.")

    provenance: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []
    seen_nonces: set[str] = set()
    seen_envelopes: set[str] = set()
    seen_sequences: set[tuple[str, int]] = set()
    seen_fencing_epochs: set[int] = set()
    envelope_total = 0
    evidence_total = 0

    for probe_id in sorted(REQUIRED_PROBES):
        raw_evidence = probe_evidence[probe_id]
        if (
            not isinstance(raw_evidence, bytes) or not raw_evidence
            or len(raw_evidence) > MAX_PROBE_EVIDENCE_BYTES
        ):
            raise AcceptanceReportV3Error(f"Raw evidence is missing or oversized: {probe_id}.")
        evidence_total += len(raw_evidence)
        if evidence_total > MAX_TOTAL_EVIDENCE_BYTES:
            raise AcceptanceReportV3Error("Aggregate raw evidence exceeds the hard limit.")
        evidence_doc = _parse_canonical_object(
            raw_evidence, label=f"Raw probe evidence {probe_id}", ascii_only=True
        )
        if frozenset(evidence_doc) != _EVIDENCE_KEYS:
            raise AcceptanceReportV3Error(f"Raw evidence schema mismatch: {probe_id}.")
        if (
            type(evidence_doc["schema_version"]) is not int
            or evidence_doc["schema_version"] != 1
            or evidence_doc["suite_id"] != SUITE_ID
            or evidence_doc["suite_version"] != SUITE_VERSION
            or evidence_doc["attempt_id"] != base.attempt_id
            or evidence_doc["runtime_id"] != expectation.runtime_id
            or evidence_doc["policy_digest"] != base.policy_digest
            or evidence_doc["probe_id"] != probe_id
        ):
            raise AcceptanceReportV3Error(f"Raw evidence is not bound to the pinned attempt: {probe_id}.")
        observations = evidence_doc["observations"]
        domains = sorted(required_domains[probe_id])
        if not isinstance(observations, list) or len(observations) != len(domains):
            raise AcceptanceReportV3Error(f"Raw evidence observer inventory is incomplete: {probe_id}.")

        actual_domains: list[str] = []
        for evidence_observation in observations:
            if not isinstance(evidence_observation, dict) or frozenset(evidence_observation) != _OBSERVATION_KEYS:
                raise AcceptanceReportV3Error(f"Raw evidence observation schema mismatch: {probe_id}.")
            domain = evidence_observation["observer_domain"]
            if domain not in required_domains[probe_id]:
                raise AcceptanceReportV3Error(f"Unauthorized observer domain in evidence: {probe_id}.")
            actual_domains.append(domain)
            pair = (probe_id, domain)
            result = observer_results[pair]
            if type(result) is not AuthenticatedObserverResult:
                raise AcceptanceReportV3Error("Observer result must be an exact verifier result type.")
            observation = result.observation
            if type(observation) is not ProbeObservation:
                raise AcceptanceReportV3Error("Observer result does not contain an exact ProbeObservation.")
            if result.signature_algorithm != "Ed25519":
                raise AcceptanceReportV3Error("Only Ed25519 observer results are accepted.")
            if (
                observation.probe_id != probe_id
                or observation.observer_domain != domain
                or evidence_observation["observer_id"] != observation.observer_id
                or observation.attempt_id != base.attempt_id
                or observation.runtime_id != expectation.runtime_id
                or observation.policy_digest != base.policy_digest
                or observation.outcome != "pass"
                or evidence_observation["outcome"] != "pass"
                or evidence_observation["runtime_id"] != expectation.runtime_id
                or evidence_observation["policy_digest"] != base.policy_digest
                or evidence_observation["observed_at"] != observation.observed_at
                or evidence_observation["monotonic_start_ns"] != observation.monotonic_start_ns
                or evidence_observation["monotonic_end_ns"] != observation.monotonic_end_ns
                or _decode_b64(evidence_observation["payload_b64"], "Evidence payload") != observation.payload
                or evidence_observation["payload_sha256"] != hashlib.sha256(observation.payload).hexdigest()
            ):
                raise AcceptanceReportV3Error(f"Raw evidence does not match verified observer result: {probe_id}/{domain}.")

            raw_envelope = raw_observer_envelopes[pair]
            envelope = _parse_envelope(raw_envelope)
            if (
                isinstance(envelope["sequence"], bool)
                or not isinstance(envelope["sequence"], int)
                or not 1 <= envelope["sequence"] <= 2**63 - 1
            ):
                raise AcceptanceReportV3Error("Raw observer envelope sequence is invalid.")
            for counter_name in ("monotonic_start_ns", "monotonic_end_ns"):
                counter = envelope[counter_name]
                if isinstance(counter, bool) or not isinstance(counter, int) or not 0 <= counter <= 2**63 - 1:
                    raise AcceptanceReportV3Error(f"Raw observer envelope {counter_name} is invalid.")
            if envelope["monotonic_end_ns"] < envelope["monotonic_start_ns"]:
                raise AcceptanceReportV3Error("Raw observer envelope monotonic interval is reversed.")
            envelope_digest = hashlib.sha256(raw_envelope).hexdigest()
            if result.envelope_sha256 != envelope_digest:
                raise AcceptanceReportV3Error("Exact retained envelope digest differs from verifier result.")
            for field, expected in {
                "audience": registry.audience,
                "observer_id": observation.observer_id,
                "observer_domain": domain,
                "key_id": result.key_id,
                "attempt_id": base.attempt_id,
                "runtime_id": expectation.runtime_id,
                "policy_digest": base.policy_digest,
                "probe_id": probe_id,
                "observed_at": observation.observed_at,
                "monotonic_start_ns": observation.monotonic_start_ns,
                "monotonic_end_ns": observation.monotonic_end_ns,
                "outcome": observation.outcome,
                "payload_sha256": hashlib.sha256(observation.payload).hexdigest(),
                "sequence": result.sequence,
            }.items():
                if envelope[field] != expected:
                    raise AcceptanceReportV3Error(f"Raw envelope {field} mismatch: {probe_id}/{domain}.")
            nonce = _decode_b64(envelope["nonce_b64"], "Observer nonce", exact_length=32)
            payload = _decode_b64(envelope["payload_b64"], "Observer payload")
            if not payload or len(payload) > MAX_PAYLOAD_BYTES:
                raise AcceptanceReportV3Error("Raw observer payload is empty or oversized.")
            if payload != observation.payload:
                raise AcceptanceReportV3Error("Raw envelope payload differs from verified observation bytes.")
            if envelope["payload_sha256"] != hashlib.sha256(payload).hexdigest():
                raise AcceptanceReportV3Error("Raw envelope payload digest is invalid.")
            signature = _decode_b64(envelope["signature_b64"], "Observer signature", exact_length=64)
            unsigned = dict(envelope)
            unsigned.pop("signature_b64")
            try:
                valid = observer_signature_verifier.verify(
                    result.key_id, _canonical(unsigned), signature
                )
            except Exception as exc:
                raise AcceptanceReportV3Error("Independent observer signature verification failed closed.") from exc
            if valid is not True:
                raise AcceptanceReportV3Error("Raw observer envelope signature is invalid.")

            nonce_digest = hashlib.sha256(nonce).hexdigest()
            if (
                nonce_digest != result.nonce_sha256
                or nonce_digest in seen_nonces
                or envelope_digest in seen_envelopes
            ):
                raise AcceptanceReportV3Error("Observer nonce or envelope digest is duplicated or mismatched.")
            sequence_key = (observation.observer_id, result.sequence)
            if sequence_key in seen_sequences:
                raise AcceptanceReportV3Error("Observer sequence is duplicated.")
            seen_nonces.add(nonce_digest)
            seen_envelopes.add(envelope_digest)
            seen_sequences.add(sequence_key)

            try:
                receipt = replay_receipt_reader.get_acceptance(
                    observer_id=observation.observer_id,
                    envelope_sha256=envelope_digest,
                )
            except Exception as exc:
                raise AcceptanceReportV3Error("Read-only replay receipt lookup failed closed.") from exc
            _check_receipt(
                receipt, result=result, envelope=envelope, envelope_digest=envelope_digest,
                registry=registry, attempt_id=base.attempt_id,
                runtime_id=expectation.runtime_id, policy_digest=base.policy_digest,
            )
            accepted_at = _parse_accepted_at(receipt.accepted_at)
            expires_at = _parse_utc(receipt.challenge_expires_at, "challenge_expires_at")
            observed_at = _parse_utc(observation.observed_at, "observer observed_at")
            if (
                accepted_at < started - timedelta(seconds=base.allowed_clock_skew_seconds)
                or accepted_at > completed + timedelta(seconds=base.allowed_clock_skew_seconds)
                or accepted_at > now + timedelta(seconds=base.allowed_clock_skew_seconds)
                or (now - accepted_at).total_seconds() > base.max_age_seconds
                or observed_at > accepted_at + timedelta(seconds=base.allowed_clock_skew_seconds)
                or accepted_at > expires_at
            ):
                raise AcceptanceReportV3Error("Observer acceptance time is outside the pinned attempt/challenge window.")
            seen_fencing_epochs.add(receipt.fencing_epoch)
            if len(seen_fencing_epochs) != 1:
                raise AcceptanceReportV3Error("Replay receipts do not share one stable fencing epoch.")

            provenance.append({
                "probe_id": probe_id,
                "observer_domain": domain,
                "observer_id": observation.observer_id,
                "key_id": result.key_id,
                "observer_registry_sha256": registry.sha256,
                "observer_registry_version": registry.version,
                "sequence": result.sequence,
                "nonce_sha256": nonce_digest,
                "envelope_sha256": envelope_digest,
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "signature_algorithm": "Ed25519",
            })
            manifest_entries.append({
                "path": (
                    f"artifacts/observer-envelopes/{base.attempt_id}/"
                    f"{envelope_digest[:2]}/{envelope_digest}.json"
                ),
                "size_bytes": len(raw_envelope),
                "envelope_sha256": envelope_digest,
                "observer_id": observation.observer_id,
                "observer_domain": domain,
                "key_id": result.key_id,
                "attempt_id": base.attempt_id,
                "runtime_id": expectation.runtime_id,
                "policy_digest": base.policy_digest,
                "probe_id": probe_id,
                "observer_registry_sha256": registry.sha256,
                "observer_registry_version": registry.version,
                "sequence": result.sequence,
                "nonce_sha256": nonce_digest,
                "challenge_expires_at": receipt.challenge_expires_at,
                "accepted_at": receipt.accepted_at,
            })
            envelope_total += len(raw_envelope)
            if envelope_total > 20 * 3 * MAX_ENVELOPE_BYTES:
                raise AcceptanceReportV3Error("Aggregate raw observer envelopes exceed the hard limit.")

        if actual_domains != domains:
            raise AcceptanceReportV3Error(f"Raw evidence domains are not in canonical order: {probe_id}.")

    provenance_bytes = _canonical(provenance)
    provenance_digest = hashlib.sha256(provenance_bytes).hexdigest()
    manifest_bytes = _canonical({
        "schema_version": 1,
        "attempt_id": base.attempt_id,
        "runtime_id": expectation.runtime_id,
        "policy_digest": base.policy_digest,
        "observer_registry_sha256": registry.sha256,
        "observer_registry_version": registry.version,
        "entries": manifest_entries,
    })
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    report = {
        "schema_version": 3,
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "key_id": base.trusted_key_id,
        "provider_id": base.provider_id,
        "region": base.region,
        "runtime_id": expectation.runtime_id,
        "task_id": base.task_id,
        "attempt_id": base.attempt_id,
        "image_digest": base.image_digest,
        "policy_digest": base.policy_digest,
        "started_at": started_at,
        "completed_at": completed_at,
        "probes": [
            {
                "probe_id": probe_id,
                "outcome": "pass",
                "evidence_sha256": hashlib.sha256(probe_evidence[probe_id]).hexdigest(),
            }
            for probe_id in sorted(REQUIRED_PROBES)
        ],
        "observer_registry_sha256": registry.sha256,
        "observer_registry_version": registry.version,
        "observer_provenance_sha256": provenance_digest,
        "observer_provenance": provenance,
        "observer_envelope_manifest_version": 1,
        "observer_envelope_manifest_sha256": manifest_digest,
    }
    report_bytes = canonical_report_bytes(report)
    if len(report_bytes) > MAX_REPORT_BYTES:
        raise AcceptanceReportV3Error("Canonical schema-v3 report exceeds the report size limit.")

    return SchemaV3ReportDraft(
        report_bytes=report_bytes,
        envelope_manifest_bytes=manifest_bytes,
        report_sha256=hashlib.sha256(report_bytes).hexdigest(),
        observer_provenance_sha256=provenance_digest,
        observer_envelope_manifest_sha256=manifest_digest,
        probe_count=len(REQUIRED_PROBES),
        observer_count=len(provenance),
        evidence_bytes_total=evidence_total,
        envelope_bytes_total=envelope_total,
    )
