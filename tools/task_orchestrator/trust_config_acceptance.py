"""Provider-neutral acceptance of root-signed trust configuration envelopes."""
from __future__ import annotations
import base64, binascii, hashlib, json, re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from .sandbox_trust import PinnedTrustStoreVerifier, TrustStoreError, Ed25519Backend

MAX_ENVELOPE_BYTES = 128 * 1024
MAX_TRUST_STORE_BYTES = 64 * 1024
MAX_JSON_DEPTH = 16
MAX_LIFETIME = timedelta(hours=1)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ENVELOPE_FIELDS = frozenset({"schema_version","audience","config_epoch","trust_store_version_floor","trust_store_sha256","trust_store_bytes","issued_at","expires_at","root_key_id","signature_algorithm","signature_b64"})
AUDIENCE_FIELDS = frozenset({"environment","deployment","provider","region"})

class TrustConfigError(ValueError):
    """Invalid or non-durably-accepted trust configuration."""

class RootSignatureVerifier(Protocol):
    def verify(self, root_key_id: str, message: bytes, signature: bytes) -> bool: ...

class MonotonicTrustStore(Protocol):
    """Production CAS and append-only audit MUST be one durable atomic transaction."""
    def read(self, audience: "TrustAudience") -> "MonotonicState | None": ...
    def compare_and_swap(self, audience: "TrustAudience", expected_revision: int | None,
                         new_state: "MonotonicState", audit_record: "TrustConfigAuditRecord") -> bool:
        """Atomically compare state, persist new_state, and append audit_record."""

@dataclass(frozen=True)
class TrustAudience:
    environment: str
    deployment: str
    provider: str
    region: str
    def __post_init__(self):
        for name in AUDIENCE_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value or len(value) > 128:
                raise TrustConfigError(f"Audience field {name} must be a non-empty bounded string.")

@dataclass(frozen=True)
class MonotonicState:
    revision: int
    config_epoch: int
    trust_store_version: int
    trust_store_sha256: str
    envelope_sha256: str
    audit_reference: str

@dataclass(frozen=True)
class TrustConfigAuditRecord:
    audience: TrustAudience
    previous_revision: int | None
    previous_config_epoch: int
    new_config_epoch: int
    previous_trust_store_version: int
    new_trust_store_version: int
    previous_trust_store_sha256: str | None
    new_trust_store_sha256: str
    envelope_sha256: str
    root_key_id: str
    accepted_at: str
    outcome: str

@dataclass(frozen=True)
class AcceptedTrustConfig:
    """Immutable result returned only after durable CAS success."""
    audience: TrustAudience
    trust_store_bytes: bytes
    trust_store_sha256: str
    trust_store_version_floor: int
    trust_store_version: int
    config_epoch: int
    expires_at: datetime
    root_key_id: str
    envelope_sha256: str
    audit_reference: str

def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TrustConfigError("Envelope contains duplicate JSON keys.")
        result[key] = value
    return result

def _reject_constant(_):
    raise TrustConfigError("Envelope contains a non-finite JSON value.")

def _check_depth(value, depth=0):
    if depth > MAX_JSON_DEPTH:
        raise TrustConfigError("Envelope JSON nesting exceeds the limit.")
    if isinstance(value, dict):
        for child in value.values(): _check_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value: _check_depth(child, depth + 1)

def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise TrustConfigError("Envelope cannot be canonically encoded.") from exc

def _timestamp(value, field):
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise TrustConfigError(f"{field} must be a strict UTC timestamp ending in Z.")
    try: return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc: raise TrustConfigError(f"{field} is invalid.") from exc

def _positive_int(value, field):
    if type(value) is not int or value < 1:
        raise TrustConfigError(f"{field} must be a positive integer.")
    return value

def _parse_envelope(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ENVELOPE_BYTES:
        raise TrustConfigError("Envelope bytes are missing or exceed the size limit.")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs_no_duplicates, parse_constant=_reject_constant)
        _check_depth(value)
    except TrustConfigError: raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TrustConfigError("Envelope is not bounded valid UTF-8 JSON.") from exc
    if not isinstance(value, dict) or frozenset(value) != ENVELOPE_FIELDS:
        raise TrustConfigError("Envelope fields do not match schema version 1.")
    if _canonical(value) != raw:
        raise TrustConfigError("Envelope is not canonical JSON.")
    unsigned = dict(value)
    encoded = unsigned.pop("signature_b64")
    if not isinstance(encoded, str) or not encoded or len(encoded) > 128:
        raise TrustConfigError("Root signature encoding is invalid.")
    try: signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc: raise TrustConfigError("Root signature is not strict base64.") from exc
    if len(signature) != 64 or base64.b64encode(signature).decode("ascii") != encoded:
        raise TrustConfigError("Ed25519 root signature must be canonical base64 of 64 bytes.")
    return value, _canonical(unsigned), signature

def accept_trust_config(envelope_bytes: bytes, *, expected_audience: TrustAudience, now: datetime,
                        root_verifier: RootSignatureVerifier, store: MonotonicTrustStore,
                        trust_store_backend: Ed25519Backend, max_lifetime: timedelta = MAX_LIFETIME) -> AcceptedTrustConfig:
    """Validate then commit. now must be trusted host UTC time; no I/O is performed here."""
    if not isinstance(expected_audience, TrustAudience):
        raise TrustConfigError("An explicit expected audience is required.")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise TrustConfigError("Trusted host time must be timezone-aware UTC.")
    if not isinstance(max_lifetime, timedelta) or max_lifetime <= timedelta(0) or max_lifetime > MAX_LIFETIME:
        raise TrustConfigError("Maximum lifetime must be positive and at most one hour.")
    if not callable(getattr(root_verifier, "verify", None)):
        raise TrustConfigError("An independently provisioned root verifier is required.")
    if not callable(getattr(store, "read", None)) or not callable(getattr(store, "compare_and_swap", None)):
        raise TrustConfigError("A monotonic transactional store is required.")

    env, signed_payload, signature = _parse_envelope(envelope_bytes)
    if type(env["schema_version"]) is not int or env["schema_version"] != 1:
        raise TrustConfigError("Unsupported trust-config schema version.")
    av = env["audience"]
    if not isinstance(av, dict) or frozenset(av) != AUDIENCE_FIELDS:
        raise TrustConfigError("Audience does not match the strict schema.")
    audience = TrustAudience(**av)
    if audience != expected_audience:
        raise TrustConfigError("Envelope audience mismatch.")
    epoch = _positive_int(env["config_epoch"], "config_epoch")
    floor = _positive_int(env["trust_store_version_floor"], "trust_store_version_floor")
    digest = env["trust_store_sha256"]
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise TrustConfigError("Trust-store SHA-256 must be lowercase hexadecimal.")
    if not isinstance(env["trust_store_bytes"], str):
        raise TrustConfigError("trust_store_bytes must be a UTF-8 string.")
    trust_raw = env["trust_store_bytes"].encode("utf-8")
    if not trust_raw or len(trust_raw) > MAX_TRUST_STORE_BYTES:
        raise TrustConfigError("Trust-store bytes are missing or oversized.")
    if hashlib.sha256(trust_raw).hexdigest() != digest:
        raise TrustConfigError("Trust-store digest mismatch.")

    issued = _timestamp(env["issued_at"], "issued_at")
    expires = _timestamp(env["expires_at"], "expires_at")
    if issued > now or expires <= now or expires <= issued or expires - issued > max_lifetime:
        raise TrustConfigError("Envelope is expired, future-issued, or exceeds maximum lifetime.")
    key_id = env["root_key_id"]
    if not isinstance(key_id, str) or not KEY_ID_RE.fullmatch(key_id):
        raise TrustConfigError("Root key ID is invalid.")
    if env["signature_algorithm"] != "Ed25519":
        raise TrustConfigError("Only Ed25519 root signatures are accepted.")
    try: valid = root_verifier.verify(key_id, signed_payload, signature)
    except Exception as exc: raise TrustConfigError("Root signature verification failed closed.") from exc
    if valid is not True:
        raise TrustConfigError("Root signature is invalid or root key is unknown.")

    try:
        pinned = PinnedTrustStoreVerifier(trust_store_bytes=trust_raw, expected_sha256=digest,
            minimum_version=floor, now=now, backend=trust_store_backend)
        pinned._parse_store()
        trust_version = json.loads(trust_raw.decode("utf-8"))["version"]
    except (TrustStoreError, KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise TrustConfigError("Embedded trust store failed pinned schema validation.") from exc

    envelope_digest = hashlib.sha256(envelope_bytes).hexdigest()
    audit_ref = f"trust-config:{epoch}:{envelope_digest}"
    try: previous = store.read(audience)
    except Exception as exc: raise TrustConfigError("Monotonic store unavailable; acceptance rejected.") from exc

    if previous is not None:
        if (type(previous.revision) is not int or previous.revision < 1
            or type(previous.config_epoch) is not int or previous.config_epoch < 1
            or type(previous.trust_store_version) is not int or previous.trust_store_version < 1
            or not isinstance(previous.trust_store_sha256, str) or not SHA256_RE.fullmatch(previous.trust_store_sha256)
            or not isinstance(previous.envelope_sha256, str) or not SHA256_RE.fullmatch(previous.envelope_sha256)
            or not isinstance(previous.audit_reference, str) or not previous.audit_reference):
            raise TrustConfigError("Monotonic state is corrupt; acceptance rejected.")
        if epoch == previous.config_epoch:
            if envelope_digest == previous.envelope_sha256 and digest == previous.trust_store_sha256 and trust_version == previous.trust_store_version:
                return AcceptedTrustConfig(audience, trust_raw, digest, floor, trust_version, epoch, expires, key_id, envelope_digest, previous.audit_reference)
            raise TrustConfigError("Same-epoch trust configuration conflict.")
        if epoch < previous.config_epoch or trust_version < previous.trust_store_version:
            raise TrustConfigError("Trust configuration rollback rejected.")
        expected_revision, prev_epoch, prev_version, prev_digest = previous.revision, previous.config_epoch, previous.trust_store_version, previous.trust_store_sha256
        next_revision = previous.revision + 1
    else:
        expected_revision, prev_epoch, prev_version, prev_digest, next_revision = None, 0, 0, None, 1

    new_state = MonotonicState(next_revision, epoch, trust_version, digest, envelope_digest, audit_ref)
    audit = TrustConfigAuditRecord(audience, expected_revision, prev_epoch, epoch, prev_version, trust_version,
        prev_digest, digest, envelope_digest, key_id, now.strftime("%Y-%m-%dT%H:%M:%SZ"), "accepted")
    try: committed = store.compare_and_swap(audience, expected_revision, new_state, audit)
    except Exception as exc: raise TrustConfigError("CAS transaction or audit append failed; acceptance rejected.") from exc
    if committed is not True:
        raise TrustConfigError("CAS race or transaction failure; acceptance rejected.")
    return AcceptedTrustConfig(audience, trust_raw, digest, floor, trust_version, epoch, expires, key_id, envelope_digest, audit_ref)
