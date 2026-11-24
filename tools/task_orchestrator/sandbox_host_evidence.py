"""Fail-closed host-side evidence assembly contract.

This module consumes bounded observations from explicitly trusted observer
adapters. It does not launch probes, processes, guests, VMs, network requests,
or provider APIs; it does not sign reports or authorize execution.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES, SUITE_ID, SUITE_VERSION

_MANIFEST_PATH = Path(__file__).with_name("runtime_probe_manifest.json")
_OBSERVER_DOMAINS = frozenset({"host_controller", "guest", "external_canary"})
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_OBSERVATION_BYTES = 48 * 1024
MAX_PROBE_EVIDENCE_BYTES = 128 * 1024
MAX_TOTAL_EVIDENCE_BYTES = 2 * 1024 * 1024


class HostEvidenceError(ValueError):
    """Observer evidence is missing, malformed, untrusted, stale, or oversized."""


@dataclass(frozen=True)
class ProbeObservation:
    probe_id: str
    observer_domain: str
    observer_id: str
    attempt_id: str
    runtime_id: str
    policy_digest: str
    monotonic_start_ns: int
    monotonic_end_ns: int
    observed_at: str
    outcome: str
    payload: bytes


@dataclass(frozen=True)
class CollectedEvidenceBundle:
    attempt_id: str
    probe_evidence: Mapping[str, bytes]
    probe_outcomes: Mapping[str, str]
    probe_digests: Mapping[str, str]
    status: str
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise HostEvidenceError("Probe manifest contains duplicate JSON keys.")
        result[key] = value
    return result


def _required_domains() -> dict[str, frozenset[str]]:
    try:
        raw = _MANIFEST_PATH.read_bytes()
        manifest = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostEvidenceError("Trusted runtime probe manifest is unavailable or invalid.") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("status") != "specification_only_not_executable"
        or manifest.get("execution_enabled") is not False
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("probes"), list)
    ):
        raise HostEvidenceError("Runtime probe manifest is not an accepted non-executable contract.")

    required: dict[str, frozenset[str]] = {}
    for item in manifest["probes"]:
        if not isinstance(item, dict):
            raise HostEvidenceError("Runtime probe manifest contains a malformed probe.")
        probe_id = item.get("probe_id")
        owner = item.get("evidence_owner")
        if not isinstance(probe_id, str) or probe_id not in REQUIRED_PROBES or probe_id in required:
            raise HostEvidenceError("Runtime probe manifest inventory is unknown or duplicated.")
        owner_domains = {
            "host_controller": frozenset({"host_controller"}),
            "guest_plus_host": frozenset({"guest", "host_controller"}),
            "host_controller_plus_guest": frozenset({"host_controller", "guest"}),
            "external_canary_plus_host": frozenset({"external_canary", "host_controller"}),
            "external_canary": frozenset({"external_canary"}),
        }
        domains = owner_domains.get(owner)
        if domains is None:
            raise HostEvidenceError(f"Unsupported evidence owner for probe: {probe_id}.")
        required[probe_id] = domains
    if set(required) != REQUIRED_PROBES:
        raise HostEvidenceError("Runtime probe manifest does not match the verifier inventory.")
    return required


def _parse_observed_at(value: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise HostEvidenceError("Observation time must be UTC RFC3339 seconds ending in Z.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HostEvidenceError("Observation time is invalid.") from exc


class HostEvidenceCollector:
    """Validate and assemble observations; no probe execution capability exists."""

    def __init__(
        self,
        *,
        trusted_observers: Mapping[str, frozenset[str]],
        runtime_id: str,
        policy_digest: str,
        now: datetime,
        max_age_seconds: int = 600,
        allowed_clock_skew_seconds: int = 30,
    ) -> None:
        if set(trusted_observers) != _OBSERVER_DOMAINS:
            raise HostEvidenceError("Trusted observer domains must be explicitly configured.")
        normalized: dict[str, frozenset[str]] = {}
        for domain, observer_ids in trusted_observers.items():
            if not isinstance(observer_ids, (set, frozenset)) or not observer_ids:
                raise HostEvidenceError(f"No trusted observer identities configured for {domain}.")
            if any(not isinstance(value, str) or not _ID_RE.fullmatch(value) for value in observer_ids):
                raise HostEvidenceError(f"Trusted observer identity is invalid for {domain}.")
            normalized[domain] = frozenset(observer_ids)
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise HostEvidenceError("Trusted collection time must be timezone-aware.")
        if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds <= 0:
            raise HostEvidenceError("Maximum observation age must be a positive integer.")
        if isinstance(allowed_clock_skew_seconds, bool) or not isinstance(allowed_clock_skew_seconds, int) or allowed_clock_skew_seconds < 0:
            raise HostEvidenceError("Allowed clock skew must be a non-negative integer.")
        if not isinstance(runtime_id, str) or not _ID_RE.fullmatch(runtime_id):
            raise HostEvidenceError("Pinned runtime identity is invalid.")
        if not isinstance(policy_digest, str) or not _SHA256_RE.fullmatch(policy_digest):
            raise HostEvidenceError("Pinned policy digest must be a lowercase SHA-256 digest.")
        self._trusted_observers = normalized
        self._runtime_id = runtime_id
        self._policy_digest = policy_digest
        self._now = now.astimezone(timezone.utc)
        self._max_age_seconds = max_age_seconds
        self._allowed_clock_skew_seconds = allowed_clock_skew_seconds

    def collect(self, *, attempt_id: str, observations: list[ProbeObservation]) -> CollectedEvidenceBundle:
        if not isinstance(attempt_id, str) or not _ID_RE.fullmatch(attempt_id):
            raise HostEvidenceError("Attempt identity is invalid.")
        if not isinstance(observations, list):
            raise HostEvidenceError("Observations must be supplied as a bounded list.")

        required = _required_domains()
        grouped: dict[str, dict[str, dict[str, object]]] = {probe_id: {} for probe_id in REQUIRED_PROBES}
        for observation in observations:
            if not isinstance(observation, ProbeObservation):
                raise HostEvidenceError("Every observation must use the typed observation contract.")
            if not isinstance(observation.probe_id, str) or observation.probe_id not in REQUIRED_PROBES:
                raise HostEvidenceError("Unknown probe observation.")
            if observation.attempt_id != attempt_id:
                raise HostEvidenceError("Observation belongs to a different attempt.")
            if observation.runtime_id != self._runtime_id:
                raise HostEvidenceError("Observation belongs to a different runtime instance.")
            if observation.policy_digest != self._policy_digest:
                raise HostEvidenceError("Observation policy digest does not match the pinned attempt policy.")
            for field in ("monotonic_start_ns", "monotonic_end_ns"):
                value = getattr(observation, field)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise HostEvidenceError("Monotonic observation offsets must be non-negative integers.")
            if observation.monotonic_end_ns < observation.monotonic_start_ns:
                raise HostEvidenceError("Observation monotonic end precedes its start.")
            if not isinstance(observation.observer_domain, str) or observation.observer_domain not in _OBSERVER_DOMAINS:
                raise HostEvidenceError("Unrecognized observer trust domain.")
            if observation.observer_domain not in required[observation.probe_id]:
                raise HostEvidenceError("Observer domain is not authorized for this probe.")
            if (
                not isinstance(observation.observer_id, str)
                or observation.observer_id not in self._trusted_observers[observation.observer_domain]
            ):
                raise HostEvidenceError("Observer identity is not in the out-of-band trust configuration.")
            if observation.observer_domain in grouped[observation.probe_id]:
                raise HostEvidenceError("Duplicate observation from the same trust domain.")
            if not isinstance(observation.outcome, str) or observation.outcome not in {"pass", "fail"}:
                raise HostEvidenceError("Observation outcome must be pass or fail.")
            if not isinstance(observation.payload, bytes) or not observation.payload:
                raise HostEvidenceError("Raw observer payload is missing or invalid.")
            if len(observation.payload) > MAX_OBSERVATION_BYTES:
                raise HostEvidenceError("Raw observer payload exceeds the per-observation size limit.")
            observed_at = _parse_observed_at(observation.observed_at)
            if observed_at > self._now + timedelta(seconds=self._allowed_clock_skew_seconds):
                raise HostEvidenceError("Observation timestamp is in the future.")
            if (self._now - observed_at).total_seconds() > self._max_age_seconds:
                raise HostEvidenceError("Observation is stale.")
            grouped[observation.probe_id][observation.observer_domain] = {
                "observer_domain": observation.observer_domain,
                "observer_id": observation.observer_id,
                "runtime_id": observation.runtime_id,
                "policy_digest": observation.policy_digest,
                "monotonic_start_ns": observation.monotonic_start_ns,
                "monotonic_end_ns": observation.monotonic_end_ns,
                "observed_at": observation.observed_at,
                "outcome": observation.outcome,
                "payload_b64": base64.b64encode(observation.payload).decode("ascii"),
                "payload_sha256": hashlib.sha256(observation.payload).hexdigest(),
            }

        evidence: dict[str, bytes] = {}
        outcomes: dict[str, str] = {}
        digests: dict[str, str] = {}
        total_bytes = 0
        for probe_id in sorted(REQUIRED_PROBES):
            records = grouped[probe_id]
            if set(records) != required[probe_id]:
                missing = sorted(required[probe_id] - set(records))
                raise HostEvidenceError(f"Probe {probe_id} lacks required independent observers: {missing}.")
            ordered = [records[domain] for domain in sorted(records)]
            outcome = "pass" if all(item["outcome"] == "pass" for item in ordered) else "fail"
            raw = json.dumps(
                {
                    "schema_version": 1,
                    "suite_id": SUITE_ID,
                    "suite_version": SUITE_VERSION,
                    "attempt_id": attempt_id,
                    "runtime_id": self._runtime_id,
                    "policy_digest": self._policy_digest,
                    "probe_id": probe_id,
                    "observations": ordered,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            if len(raw) > MAX_PROBE_EVIDENCE_BYTES:
                raise HostEvidenceError(f"Assembled probe evidence exceeds the size limit: {probe_id}.")
            total_bytes += len(raw)
            if total_bytes > MAX_TOTAL_EVIDENCE_BYTES:
                raise HostEvidenceError("Assembled evidence exceeds the aggregate size limit.")
            evidence[probe_id] = raw
            outcomes[probe_id] = outcome
            digests[probe_id] = hashlib.sha256(raw).hexdigest()

        status = "all_observers_reported_pass" if all(value == "pass" for value in outcomes.values()) else "one_or_more_probes_failed"
        return CollectedEvidenceBundle(
            attempt_id=attempt_id,
            probe_evidence=MappingProxyType(evidence),
            probe_outcomes=MappingProxyType(outcomes),
            probe_digests=MappingProxyType(digests),
            status=status,
        )
