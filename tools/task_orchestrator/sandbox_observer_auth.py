"""Verify signed observer envelopes before evidence assembly.

This is a contract adapter, not a network service or production replay store.
Observer registry bytes must be pinned out of band; the replay store must be a
trusted atomic implementation. Unit tests use deterministic in-memory fakes.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES
from tools.task_orchestrator.sandbox_host_evidence import ProbeObservation

MAX_REGISTRY_BYTES = 32 * 1024
MAX_ENVELOPE_BYTES = 96 * 1024
MAX_IDENTITIES = 64
MAX_PAYLOAD_BYTES = 48 * 1024
MAX_CHALLENGE_SECONDS = 120
MAX_OBSERVATION_AGE_SECONDS = 3600
MAX_CLOCK_SKEW_SECONDS = 120
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_DOMAINS = frozenset({"host_controller", "guest", "external_canary"})
_REGISTRY_FIELDS = frozenset({"schema_version", "version", "audience", "identities"})
_IDENTITY_FIELDS = frozenset({
    "observer_id", "observer_domain", "key_id", "status", "not_before", "not_after"
})
_ENVELOPE_FIELDS = frozenset({
    "schema_version", "audience", "observer_id", "observer_domain", "key_id",
    "attempt_id", "runtime_id", "policy_digest", "probe_id", "nonce_b64",
    "sequence", "observed_at", "monotonic_start_ns", "monotonic_end_ns",
    "outcome", "payload_b64", "payload_sha256", "signature_b64",
})


class ObserverAuthenticationError(ValueError):
    """Observer envelope or trust binding is malformed, stale, or untrusted."""


class ObserverSignatureVerifier(Protocol):
    def verify(self, key_id: str, message: bytes, signature: bytes) -> bool: ...


class ObserverReplayStore(Protocol):
    """Trusted implementations must atomically consume nonce and advance sequence.

    The transaction must reject a previously used nonce and any sequence not
    strictly greater than the observer's previously accepted sequence. State
    must be durable across restart; unavailable/corrupt state must fail closed.
    """

    def consume(
        self, *, observer_id: str, nonce_sha256: str, sequence: int, envelope_sha256: str
    ) -> bool: ...


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ObserverAuthenticationError("Observer JSON contains duplicate keys.")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ObserverAuthenticationError("Observer JSON contains a non-finite value.")


def _canonical(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ObserverAuthenticationError("Observer data cannot be canonically encoded.") from exc


def _parse_json(raw: bytes, *, maximum: int, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > maximum:
        raise ObserverAuthenticationError(f"{label} is empty or exceeds its size limit.")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except ObserverAuthenticationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ObserverAuthenticationError(f"{label} is not valid bounded UTF-8 JSON.") from exc
    if not isinstance(value, dict) or _canonical(value) != raw:
        raise ObserverAuthenticationError(f"{label} must be a canonical JSON object.")
    return value


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise ObserverAuthenticationError(f"{field} must be a UTC timestamp ending in Z.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ObserverAuthenticationError(f"{field} is invalid.") from exc


def _validate_id(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ObserverAuthenticationError(f"{field} is invalid.")


def _decode_canonical_b64(value: Any, field: str, *, expected_length: int | None = None) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 96 * 1024:
        raise ObserverAuthenticationError(f"{field} is missing or oversized.")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ObserverAuthenticationError(f"{field} is not strict base64.") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ObserverAuthenticationError(f"{field} is not canonical base64.")
    if expected_length is not None and len(decoded) != expected_length:
        raise ObserverAuthenticationError(f"{field} has an invalid decoded length.")
    return decoded


@dataclass(frozen=True)
class ObserverIdentity:
    observer_id: str
    observer_domain: str
    key_id: str
    not_before: datetime
    not_after: datetime
    status: str


class PinnedObserverRegistry:
    """Parse an identity registry whose digest/version/audience are pinned externally."""

    def __init__(
        self,
        registry_bytes: bytes,
        *,
        expected_sha256: str,
        minimum_version: int,
        expected_audience: str,
        now: datetime,
    ) -> None:
        if not isinstance(registry_bytes, bytes) or not registry_bytes or len(registry_bytes) > MAX_REGISTRY_BYTES:
            raise ObserverAuthenticationError("Pinned observer registry bytes are required and bounded.")
        if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
            raise ObserverAuthenticationError("An independently pinned registry SHA-256 is required.")
        if hashlib.sha256(registry_bytes).hexdigest() != expected_sha256:
            raise ObserverAuthenticationError("Observer registry digest does not match the out-of-band pin.")
        if isinstance(minimum_version, bool) or not isinstance(minimum_version, int) or minimum_version < 1:
            raise ObserverAuthenticationError("Minimum observer registry version must be positive.")
        _validate_id(expected_audience, "Expected observer audience")
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ObserverAuthenticationError("Trusted registry time must be timezone-aware UTC.")

        document = _parse_json(registry_bytes, maximum=MAX_REGISTRY_BYTES, label="Observer registry")
        if frozenset(document) != _REGISTRY_FIELDS:
            raise ObserverAuthenticationError("Observer registry fields do not match the strict schema.")
        if type(document["schema_version"]) is not int or document["schema_version"] != 1:
            raise ObserverAuthenticationError("Observer registry schema version is unsupported.")
        version = document["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < minimum_version:
            raise ObserverAuthenticationError("Observer registry is below the protected minimum version.")
        if document["audience"] != expected_audience:
            raise ObserverAuthenticationError("Observer registry audience mismatch.")
        entries = document["identities"]
        if not isinstance(entries, list) or not entries or len(entries) > MAX_IDENTITIES:
            raise ObserverAuthenticationError("Observer registry identity inventory is empty or oversized.")

        indexed: dict[str, ObserverIdentity] = {}
        for entry in entries:
            if not isinstance(entry, dict) or frozenset(entry) != _IDENTITY_FIELDS:
                raise ObserverAuthenticationError("Observer registry contains a malformed identity.")
            observer_id = entry["observer_id"]
            key_id = entry["key_id"]
            domain = entry["observer_domain"]
            _validate_id(observer_id, "Observer identity")
            _validate_id(key_id, "Observer key ID")
            if observer_id in indexed:
                raise ObserverAuthenticationError("Observer registry contains duplicate identities.")
            if not isinstance(domain, str) or domain not in _DOMAINS:
                raise ObserverAuthenticationError("Observer registry contains an unknown trust domain.")
            if not isinstance(entry["status"], str) or entry["status"] not in {"active", "retired", "revoked"}:
                raise ObserverAuthenticationError("Observer registry status is invalid.")
            not_before = _parse_utc(entry["not_before"], "observer not_before")
            not_after = _parse_utc(entry["not_after"], "observer not_after")
            if not_after <= not_before:
                raise ObserverAuthenticationError("Observer identity validity interval is empty or reversed.")
            indexed[observer_id] = ObserverIdentity(
                observer_id=observer_id,
                observer_domain=domain,
                key_id=key_id,
                not_before=not_before,
                not_after=not_after,
                status=entry["status"],
            )
        self.version = version
        self.audience = expected_audience
        self.sha256 = expected_sha256
        self._now = now.astimezone(timezone.utc)
        self._identities: Mapping[str, ObserverIdentity] = MappingProxyType(indexed)

    def resolve(self, observer_id: str, observer_domain: str, key_id: str, *, now: datetime | None = None) -> ObserverIdentity:
        identity = self._identities.get(observer_id)
        if identity is None:
            raise ObserverAuthenticationError("Observer identity is not in the pinned registry.")
        if identity.observer_domain != observer_domain or identity.key_id != key_id:
            raise ObserverAuthenticationError("Observer domain or signing key does not match the pinned identity.")
        if identity.status != "active":
            raise ObserverAuthenticationError("Observer identity is retired or revoked.")
        trusted_now = self._now if now is None else now.astimezone(timezone.utc)
        if trusted_now < identity.not_before or trusted_now >= identity.not_after:
            raise ObserverAuthenticationError("Observer identity is outside its validity window.")
        return identity


@dataclass(frozen=True)
class ObserverChallenge:
    nonce: bytes
    audience: str
    observer_id: str
    observer_domain: str
    attempt_id: str
    runtime_id: str
    policy_digest: str
    probe_id: str
    issued_at: datetime
    expires_at: datetime

    def validate(self, now: datetime) -> None:
        if not isinstance(self.nonce, bytes) or len(self.nonce) != 32:
            raise ObserverAuthenticationError("Host challenge nonce must contain exactly 32 random bytes.")
        for field in ("audience", "observer_id", "attempt_id", "runtime_id", "probe_id"):
            _validate_id(getattr(self, field), f"Challenge {field}")
        if not isinstance(self.observer_domain, str) or self.observer_domain not in _DOMAINS:
            raise ObserverAuthenticationError("Challenge observer domain is invalid.")
        if self.probe_id not in REQUIRED_PROBES:
            raise ObserverAuthenticationError("Challenge probe ID is not in the pinned acceptance inventory.")
        if not isinstance(self.policy_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", self.policy_digest):
            raise ObserverAuthenticationError("Challenge policy digest is invalid.")
        if not isinstance(self.issued_at, datetime) or not isinstance(self.expires_at, datetime):
            raise ObserverAuthenticationError("Challenge timestamps are required.")
        if (
            self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None
            or self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None
        ):
            raise ObserverAuthenticationError("Challenge timestamps must be timezone-aware.")
        issued = self.issued_at.astimezone(timezone.utc)
        expires = self.expires_at.astimezone(timezone.utc)
        trusted_now = now.astimezone(timezone.utc)
        if expires <= issued or (expires - issued).total_seconds() > MAX_CHALLENGE_SECONDS:
            raise ObserverAuthenticationError("Challenge lifetime is invalid or exceeds its hard limit.")
        if issued > trusted_now or expires <= trusted_now:
            raise ObserverAuthenticationError("Challenge is future-issued or expired.")
        if (trusted_now - issued).total_seconds() > MAX_CHALLENGE_SECONDS:
            raise ObserverAuthenticationError("Challenge is stale.")



@dataclass(frozen=True)
class AuthenticatedObserverResult:
    """Successful signature/replay verification plus audit bindings.

    The observation can be passed to HostEvidenceCollector. Preserve the
    provenance fields in host-side audit and later signed-report integration.
    """

    observation: ProbeObservation
    observer_registry_sha256: str
    observer_registry_version: int
    key_id: str
    sequence: int
    nonce_sha256: str
    envelope_sha256: str
    signature_algorithm: str = "Ed25519"


class ObserverEnvelopeVerifier:
    """Verify a signed observer envelope and atomically consume its challenge/sequence."""

    def __init__(
        self,
        *,
        registry: PinnedObserverRegistry,
        signature_verifier: ObserverSignatureVerifier,
        replay_store: ObserverReplayStore,
        now: datetime,
        max_age_seconds: int = 600,
        allowed_clock_skew_seconds: int = 30,
    ) -> None:
        if not isinstance(registry, PinnedObserverRegistry):
            raise ObserverAuthenticationError("A pinned observer registry is required.")
        if not callable(getattr(signature_verifier, "verify", None)):
            raise ObserverAuthenticationError("An audited observer signature verifier is required.")
        if not callable(getattr(replay_store, "consume", None)):
            raise ObserverAuthenticationError("An atomic replay store is required.")
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ObserverAuthenticationError("Trusted observer verification time must be UTC.")
        if (
            isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int)
            or not 1 <= max_age_seconds <= MAX_OBSERVATION_AGE_SECONDS
        ):
            raise ObserverAuthenticationError("Maximum observation age must be between 1 second and one hour.")
        if (
            isinstance(allowed_clock_skew_seconds, bool) or not isinstance(allowed_clock_skew_seconds, int)
            or not 0 <= allowed_clock_skew_seconds <= MAX_CLOCK_SKEW_SECONDS
        ):
            raise ObserverAuthenticationError("Allowed clock skew must be between zero and 120 seconds.")
        self._registry = registry
        self._signature_verifier = signature_verifier
        self._replay_store = replay_store
        self._now = now.astimezone(timezone.utc)
        self._max_age = max_age_seconds
        self._skew = allowed_clock_skew_seconds

    def verify(self, envelope_bytes: bytes, *, challenge: ObserverChallenge) -> AuthenticatedObserverResult:
        challenge.validate(self._now)
        if challenge.audience != self._registry.audience:
            raise ObserverAuthenticationError("Host challenge audience does not match the pinned observer registry.")
        envelope = _parse_json(envelope_bytes, maximum=MAX_ENVELOPE_BYTES, label="Observer envelope")
        if frozenset(envelope) != _ENVELOPE_FIELDS:
            raise ObserverAuthenticationError("Observer envelope fields do not match the strict schema.")
        if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
            raise ObserverAuthenticationError("Observer envelope schema version is unsupported.")

        bindings = {
            "audience": challenge.audience,
            "observer_id": challenge.observer_id,
            "observer_domain": challenge.observer_domain,
            "attempt_id": challenge.attempt_id,
            "runtime_id": challenge.runtime_id,
            "policy_digest": challenge.policy_digest,
            "probe_id": challenge.probe_id,
        }
        for field, expected in bindings.items():
            if envelope[field] != expected:
                raise ObserverAuthenticationError(f"Observer envelope {field} does not match the host challenge.")

        key_id = envelope["key_id"]
        _validate_id(key_id, "Observer key ID")
        self._registry.resolve(challenge.observer_id, challenge.observer_domain, key_id, now=self._now)

        nonce = _decode_canonical_b64(envelope["nonce_b64"], "Observer nonce", expected_length=32)
        if nonce != challenge.nonce:
            raise ObserverAuthenticationError("Observer envelope nonce does not match the one-time host challenge.")
        sequence = envelope["sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > (2**63 - 1):
            raise ObserverAuthenticationError("Observer sequence must be a positive integer.")

        observed_at = _parse_utc(envelope["observed_at"], "Observer observed_at")
        now = self._now
        if observed_at > now + timedelta(seconds=self._skew):
            raise ObserverAuthenticationError("Observer timestamp is in the future.")
        if (now - observed_at).total_seconds() > self._max_age:
            raise ObserverAuthenticationError("Observer evidence is stale.")
        challenge_start = challenge.issued_at.astimezone(timezone.utc)
        challenge_end = challenge.expires_at.astimezone(timezone.utc)
        if observed_at < challenge_start - timedelta(seconds=self._skew) or observed_at > challenge_end + timedelta(seconds=self._skew):
            raise ObserverAuthenticationError("Observer timestamp falls outside the challenge window.")

        start_ns = envelope["monotonic_start_ns"]
        end_ns = envelope["monotonic_end_ns"]
        for field, value in (("monotonic_start_ns", start_ns), ("monotonic_end_ns", end_ns)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > (2**63 - 1):
                raise ObserverAuthenticationError(f"{field} must be a non-negative integer.")
        if end_ns < start_ns:
            raise ObserverAuthenticationError("Observer monotonic end precedes its start.")

        outcome = envelope["outcome"]
        if not isinstance(outcome, str) or outcome not in {"pass", "fail"}:
            raise ObserverAuthenticationError("Observer outcome must be pass or fail.")
        payload = _decode_canonical_b64(envelope["payload_b64"], "Observer payload")
        if not payload or len(payload) > MAX_PAYLOAD_BYTES:
            raise ObserverAuthenticationError("Observer payload is empty or exceeds the size limit.")
        payload_digest = envelope["payload_sha256"]
        if not isinstance(payload_digest, str) or not _SHA256_RE.fullmatch(payload_digest):
            raise ObserverAuthenticationError("Observer payload digest must be lowercase SHA-256.")
        if hashlib.sha256(payload).hexdigest() != payload_digest:
            raise ObserverAuthenticationError("Observer payload digest does not match its exact bytes.")

        signature = _decode_canonical_b64(envelope["signature_b64"], "Observer signature", expected_length=64)
        unsigned = dict(envelope)
        unsigned.pop("signature_b64")
        signed_bytes = _canonical(unsigned)
        try:
            valid = self._signature_verifier.verify(key_id, signed_bytes, signature)
        except Exception as exc:
            raise ObserverAuthenticationError("Observer signature verification failed closed.") from exc
        if valid is not True:
            raise ObserverAuthenticationError("Observer signature is invalid.")

        nonce_digest = hashlib.sha256(nonce).hexdigest()
        envelope_digest = hashlib.sha256(envelope_bytes).hexdigest()
        try:
            consumed = self._replay_store.consume(
                observer_id=challenge.observer_id,
                nonce_sha256=nonce_digest,
                sequence=sequence,
                envelope_sha256=envelope_digest,
            )
        except Exception as exc:
            raise ObserverAuthenticationError("Replay store unavailable; observer evidence rejected.") from exc
        if consumed is not True:
            raise ObserverAuthenticationError("Observer challenge was replayed or sequence is not increasing.")

        observation = ProbeObservation(
            probe_id=challenge.probe_id,
            observer_domain=challenge.observer_domain,
            observer_id=challenge.observer_id,
            attempt_id=challenge.attempt_id,
            runtime_id=challenge.runtime_id,
            policy_digest=challenge.policy_digest,
            monotonic_start_ns=start_ns,
            monotonic_end_ns=end_ns,
            observed_at=envelope["observed_at"],
            outcome=outcome,
            payload=payload,
        )
        return AuthenticatedObserverResult(
            observation=observation,
            observer_registry_sha256=self._registry.sha256,
            observer_registry_version=self._registry.version,
            key_id=key_id,
            sequence=sequence,
            nonce_sha256=nonce_digest,
            envelope_sha256=envelope_digest,
        )
