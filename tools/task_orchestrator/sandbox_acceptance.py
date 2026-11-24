"""Fail-closed verifier for independently signed sandbox runtime evidence.

This module verifies evidence produced by a separately trusted acceptance suite.
It does not run probes, provision VMs, verify signatures by itself, or authorize
untrusted code execution. Production callers must inject a verifier backed by an
out-of-band pinned public key (for example, Ed25519).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, runtime_checkable


MAX_REPORT_BYTES = 256 * 1024
MAX_SIGNATURE_BYTES = 1024
SUITE_ID = "jetvpn-sandbox-runtime-acceptance"
SUITE_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_RE = re.compile(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$")

# Exact suite inventory. Every probe must be independently executed and
# represented by a digest of its bounded raw evidence in the signed report.
REQUIRED_PROBES = frozenset({
    "runtime_vm_boundary",
    "dedicated_kernel",
    "guest_non_root_no_capabilities",
    "seccomp_enforced",
    "cgroup_cpu_memory_pid_enforced",
    "disk_quota_enforced",
    "source_readonly_scratch_writable",
    "host_home_secrets_absent",
    "host_sockets_devices_absent",
    "metadata_endpoint_blocked",
    "ipv4_egress_blocked",
    "ipv6_egress_blocked",
    "dns_udp_tcp_blocked",
    "quic_udp443_blocked",
    "external_canary_unreachable",
    "wall_clock_timeout_enforced",
    "process_tree_kill_verified",
    "artifact_path_size_digest_verified",
    "cleanup_success_failure_timeout",
    "fresh_vm_no_prior_attempt_residue",
})

_TOP_LEVEL_KEYS = frozenset({
    "schema_version",
    "suite_id",
    "suite_version",
    "key_id",
    "provider_id",
    "region",
    "runtime_id",
    "task_id",
    "attempt_id",
    "image_digest",
    "policy_digest",
    "started_at",
    "completed_at",
    "probes",
})
_PROBE_KEYS = frozenset({"probe_id", "outcome", "evidence_sha256"})


class SandboxEvidenceError(ValueError):
    """Signed runtime evidence is malformed, stale, untrusted, or incomplete."""


@runtime_checkable
class SignatureVerifier(Protocol):
    """Trusted verifier configured outside the sandbox/provider trust domain."""

    def verify(self, key_id: str, message: bytes, signature: bytes) -> bool: ...


@dataclass(frozen=True)
class AcceptanceExpectation:
    provider_id: str
    region: str
    task_id: str
    attempt_id: str
    image_digest: str
    policy_digest: str
    trusted_key_id: str
    now: datetime
    max_age_seconds: int = 600
    max_suite_duration_seconds: int = 1800
    allowed_clock_skew_seconds: int = 30

    def validate(self) -> None:
        for name in ("provider_id", "region", "task_id", "attempt_id", "trusted_key_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise SandboxEvidenceError(f"Expected {name} is invalid.")
        for name in ("image_digest", "policy_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:") or not _SHA256_RE.fullmatch(value[7:]):
                raise SandboxEvidenceError(f"Expected {name} must be a pinned SHA-256 digest.")
        if not isinstance(self.now, datetime) or self.now.tzinfo is None or self.now.utcoffset() is None:
            raise SandboxEvidenceError("Trusted verification time must be timezone-aware.")
        for name in ("max_age_seconds", "max_suite_duration_seconds", "allowed_clock_skew_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SandboxEvidenceError(f"Expected {name} is invalid.")
        if self.max_age_seconds == 0 or self.max_suite_duration_seconds == 0:
            raise SandboxEvidenceError("Evidence age and suite duration limits must be positive.")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SandboxEvidenceError("Acceptance report contains duplicate JSON keys.")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise SandboxEvidenceError("Acceptance report contains a non-finite JSON number.")


def canonical_report_bytes(report: dict[str, Any]) -> bytes:
    """Return the only accepted canonical UTF-8 representation for signing."""
    try:
        return json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise SandboxEvidenceError("Acceptance report cannot be canonically encoded.") from exc


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise SandboxEvidenceError(f"Acceptance report {field} must be UTC RFC3339 seconds ending in Z.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SandboxEvidenceError(f"Acceptance report {field} is not a valid UTC timestamp.") from exc


def _validate_text(value: Any, field: str, *, maximum: int = 128) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum or not _ID_RE.fullmatch(value):
        raise SandboxEvidenceError(f"Acceptance report {field} is invalid.")


def _validate_digest(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or not _SHA256_RE.fullmatch(value[7:]):
        raise SandboxEvidenceError(f"Acceptance report {field} must be a pinned SHA-256 digest.")


def verify_signed_acceptance_report(
    report_bytes: bytes,
    signature: bytes,
    expectation: AcceptanceExpectation,
    verifier: SignatureVerifier,
) -> dict[str, Any]:
    """Verify one fresh, complete, signed runtime-acceptance report.

    A passing report is evidence that the pinned external suite reported all
    probes passing. It is not a sandbox launch authorization: this function
    always returns execution_authorized=False and eligible_for_untrusted_execution=False.
    """
    expectation.validate()
    if not isinstance(report_bytes, bytes) or not report_bytes or len(report_bytes) > MAX_REPORT_BYTES:
        raise SandboxEvidenceError("Acceptance report is empty or exceeds the size limit.")
    if not isinstance(signature, bytes) or not signature or len(signature) > MAX_SIGNATURE_BYTES:
        raise SandboxEvidenceError("Acceptance report signature is missing or exceeds the size limit.")
    if not isinstance(verifier, SignatureVerifier):
        # Runtime Protocol checks the presence of verify without trusting its result.
        raise SandboxEvidenceError("A trusted signature verifier is required.")

    try:
        report = json.loads(
            report_bytes.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except SandboxEvidenceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SandboxEvidenceError("Acceptance report is not valid bounded UTF-8 JSON.") from exc

    if not isinstance(report, dict) or frozenset(report) != _TOP_LEVEL_KEYS:
        raise SandboxEvidenceError("Acceptance report fields do not match the strict schema.")
    if type(report["schema_version"]) is not int or report["schema_version"] != REPORT_SCHEMA_VERSION:
        raise SandboxEvidenceError("Acceptance report schema version is unsupported.")
    if report["suite_id"] != SUITE_ID or report["suite_version"] != SUITE_VERSION:
        raise SandboxEvidenceError("Acceptance report suite identity or version is not pinned.")
    if report["key_id"] != expectation.trusted_key_id:
        raise SandboxEvidenceError("Acceptance report signing key is not the pinned trusted key.")

    for field in ("provider_id", "region", "runtime_id", "task_id", "attempt_id", "key_id"):
        _validate_text(report[field], field)
    for field in ("image_digest", "policy_digest"):
        _validate_digest(report[field], field)

    expected_bindings = {
        "provider_id": expectation.provider_id,
        "region": expectation.region,
        "task_id": expectation.task_id,
        "attempt_id": expectation.attempt_id,
        "image_digest": expectation.image_digest,
        "policy_digest": expectation.policy_digest,
    }
    for field, expected in expected_bindings.items():
        if report[field] != expected:
            raise SandboxEvidenceError(f"Acceptance report {field} does not match the pinned attempt.")

    started = _parse_utc(report["started_at"], "started_at")
    completed = _parse_utc(report["completed_at"], "completed_at")
    now = expectation.now.astimezone(timezone.utc)
    if completed < started:
        raise SandboxEvidenceError("Acceptance report completion precedes its start.")
    if (completed - started).total_seconds() > expectation.max_suite_duration_seconds:
        raise SandboxEvidenceError("Acceptance suite exceeded its maximum duration.")
    if completed > now + timedelta(seconds=expectation.allowed_clock_skew_seconds):
        raise SandboxEvidenceError("Acceptance report completion timestamp is in the future.")
    if (now - completed).total_seconds() > expectation.max_age_seconds:
        raise SandboxEvidenceError("Acceptance report is stale and must be rerun.")

    probes = report["probes"]
    if not isinstance(probes, list) or len(probes) != len(REQUIRED_PROBES):
        raise SandboxEvidenceError("Acceptance report does not contain the exact required probe inventory.")
    seen: set[str] = set()
    for probe in probes:
        if not isinstance(probe, dict) or frozenset(probe) != _PROBE_KEYS:
            raise SandboxEvidenceError("Acceptance report contains a malformed probe record.")
        probe_id = probe["probe_id"]
        _validate_text(probe_id, "probe_id")
        if probe_id not in REQUIRED_PROBES or probe_id in seen:
            raise SandboxEvidenceError("Acceptance report contains an unknown or duplicate probe.")
        seen.add(probe_id)
        if probe["outcome"] != "pass":
            raise SandboxEvidenceError(f"Required sandbox probe did not pass: {probe_id}.")
        digest = probe["evidence_sha256"]
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise SandboxEvidenceError(f"Probe evidence digest is invalid: {probe_id}.")
    if seen != REQUIRED_PROBES:
        raise SandboxEvidenceError("Acceptance report is missing one or more required probes.")

    canonical = canonical_report_bytes(report)
    if canonical != report_bytes:
        raise SandboxEvidenceError("Acceptance report is not in canonical signed form.")
    try:
        verified = verifier.verify(expectation.trusted_key_id, canonical, signature)
    except Exception as exc:
        raise SandboxEvidenceError("Trusted signature verification failed closed.") from exc
    if verified is not True:
        raise SandboxEvidenceError("Acceptance report signature is invalid.")

    return {
        "schema_version": 1,
        "status": "runtime_acceptance_evidence_verified",
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "provider_id": report["provider_id"],
        "region": report["region"],
        "runtime_id": report["runtime_id"],
        "task_id": report["task_id"],
        "attempt_id": report["attempt_id"],
        "image_digest": report["image_digest"],
        "policy_digest": report["policy_digest"],
        "probe_count": len(seen),
        "probe_ids": sorted(seen),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "signature_verified": True,
        "execution_authorized": False,
        "eligible_for_untrusted_execution": False,
        "patch_applied": False,
    }
