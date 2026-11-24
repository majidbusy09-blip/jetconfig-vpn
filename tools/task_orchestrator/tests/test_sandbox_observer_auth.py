import base64
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from tools.task_orchestrator.sandbox_observer_auth import (
    ObserverAuthenticationError,
    ObserverChallenge,
    ObserverEnvelopeVerifier,
    PinnedObserverRegistry,
)


NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
POLICY = "sha256:" + "a" * 64
AUDIENCE = "sandbox-test-eu1"
OBSERVER = "host-observer-01"
DOMAIN = "host_controller"
KEY_ID = "host-key-01"
ATTEMPT = "attempt-observer-001"
RUNTIME = "runtime-observer-001"
PROBE = "runtime_vm_boundary"
NONCE = b"N" * 32
PAYLOAD = b"independent host observation"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def registry_bytes(*, status="active", version=3, observer_id=OBSERVER, domain=DOMAIN, key_id=KEY_ID):
    value = {
        "schema_version": 1,
        "version": version,
        "audience": AUDIENCE,
        "identities": [{
            "observer_id": observer_id,
            "observer_domain": domain,
            "key_id": key_id,
            "status": status,
            "not_before": "2026-11-24T10:00:00Z",
            "not_after": "2026-11-25T10:00:00Z",
        }],
    }
    return canonical(value)


class FakeSignatureVerifier:
    def verify(self, key_id, message, signature):
        expected = hashlib.sha512(key_id.encode("ascii") + b"\x00" + message).digest()
        return signature == expected


class MemoryReplayStore:
    def __init__(self):
        self.nonces = set()
        self.last_sequence = {}
        self.records = []

    def consume(self, *, observer_id, nonce_sha256, sequence, envelope_sha256):
        if nonce_sha256 in self.nonces or sequence <= self.last_sequence.get(observer_id, 0):
            return False
        self.nonces.add(nonce_sha256)
        self.last_sequence[observer_id] = sequence
        self.records.append((observer_id, sequence, envelope_sha256))
        return True


class FailingReplayStore:
    def consume(self, **kwargs):
        raise OSError("fixture store unavailable")


def challenge(*, nonce=NONCE, issued_at=None, expires_at=None, probe_id=PROBE, audience=AUDIENCE):
    return ObserverChallenge(
        nonce=nonce,
        audience=audience,
        observer_id=OBSERVER,
        observer_domain=DOMAIN,
        attempt_id=ATTEMPT,
        runtime_id=RUNTIME,
        policy_digest=POLICY,
        probe_id=probe_id,
        issued_at=issued_at or NOW - timedelta(seconds=30),
        expires_at=expires_at or NOW + timedelta(seconds=30),
    )


def make_envelope(*, nonce=NONCE, sequence=1, observed_at="2026-11-24T11:59:45Z",
                  payload=PAYLOAD, payload_sha256=None, observer_id=OBSERVER,
                  observer_domain=DOMAIN, key_id=KEY_ID, attempt_id=ATTEMPT,
                  runtime_id=RUNTIME, policy_digest=POLICY, probe_id=PROBE,
                  outcome="pass", monotonic_start_ns=100, monotonic_end_ns=200,
                  audience=AUDIENCE, signature_override=None):
    unsigned = {
        "schema_version": 1,
        "audience": audience,
        "observer_id": observer_id,
        "observer_domain": observer_domain,
        "key_id": key_id,
        "attempt_id": attempt_id,
        "runtime_id": runtime_id,
        "policy_digest": policy_digest,
        "probe_id": probe_id,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "sequence": sequence,
        "observed_at": observed_at,
        "monotonic_start_ns": monotonic_start_ns,
        "monotonic_end_ns": monotonic_end_ns,
        "outcome": outcome,
        "payload_b64": base64.b64encode(payload).decode("ascii"),
        "payload_sha256": payload_sha256 or hashlib.sha256(payload).hexdigest(),
    }
    signed = canonical(unsigned)
    signature = signature_override or hashlib.sha512(key_id.encode("ascii") + b"\x00" + signed).digest()
    return canonical({**unsigned, "signature_b64": base64.b64encode(signature).decode("ascii")})


def make_verifier(*, store=None, status="active", registry_raw=None, expected_audience=AUDIENCE,
                  expected_sha256=None, minimum_version=1, now=NOW):
    raw = registry_raw if registry_raw is not None else registry_bytes(status=status)
    registry = PinnedObserverRegistry(
        raw,
        expected_sha256=expected_sha256 or hashlib.sha256(raw).hexdigest(),
        minimum_version=minimum_version,
        expected_audience=expected_audience,
        now=now,
    )
    replay = store or MemoryReplayStore()
    verifier = ObserverEnvelopeVerifier(
        registry=registry,
        signature_verifier=FakeSignatureVerifier(),
        replay_store=replay,
        now=now,
    )
    return verifier, replay


class ObserverAuthenticationTests(unittest.TestCase):
    def test_valid_signed_envelope_returns_typed_probe_observation(self):
        verifier, replay = make_verifier()
        result = verifier.verify(make_envelope(), challenge=challenge())
        self.assertEqual(result.observation.probe_id, PROBE)
        self.assertEqual(result.observation.observer_id, OBSERVER)
        self.assertEqual(result.observation.observer_domain, DOMAIN)
        self.assertEqual(result.observation.payload, PAYLOAD)
        self.assertEqual(result.observation.outcome, "pass")
        self.assertEqual(result.observer_registry_version, 3)
        self.assertEqual(result.observer_registry_sha256, hashlib.sha256(registry_bytes()).hexdigest())
        self.assertEqual(result.key_id, KEY_ID)
        self.assertEqual(result.sequence, 1)
        self.assertEqual(result.nonce_sha256, hashlib.sha256(NONCE).hexdigest())
        self.assertEqual(result.envelope_sha256, hashlib.sha256(make_envelope()).hexdigest())
        self.assertEqual(replay.last_sequence[OBSERVER], 1)

    def test_duplicate_nonce_is_rejected_even_with_new_sequence(self):
        verifier, _ = make_verifier()
        verifier.verify(make_envelope(sequence=1), challenge=challenge())
        with self.assertRaisesRegex(ObserverAuthenticationError, "replayed"):
            verifier.verify(make_envelope(sequence=2), challenge=challenge())

    def test_sequence_must_increase_across_distinct_challenges(self):
        verifier, _ = make_verifier()
        verifier.verify(make_envelope(sequence=4), challenge=challenge())
        second_challenge = challenge(nonce=b"M" * 32)
        with self.assertRaisesRegex(ObserverAuthenticationError, "replayed"):
            verifier.verify(make_envelope(nonce=b"M" * 32, sequence=4), challenge=second_challenge)

    def test_bad_signature_and_tampered_signed_fields_are_rejected(self):
        verifier, _ = make_verifier()
        with self.assertRaisesRegex(ObserverAuthenticationError, "signature is invalid"):
            verifier.verify(
                make_envelope(signature_override=b"X" * 64),
                challenge=challenge(),
            )
        envelope = json.loads(make_envelope())
        envelope["outcome"] = "fail"
        with self.assertRaisesRegex(ObserverAuthenticationError, "signature is invalid"):
            verifier.verify(canonical(envelope), challenge=challenge())

    def test_challenge_context_and_nonce_are_exactly_bound(self):
        verifier, _ = make_verifier()
        cases = (
            ({"observer_id": "other-observer"}, challenge()),
            ({"observer_domain": "guest"}, challenge()),
            ({"key_id": "other-key"}, challenge()),
            ({"attempt_id": "other-attempt"}, challenge()),
            ({"runtime_id": "other-runtime"}, challenge()),
            ({"policy_digest": "sha256:" + "b" * 64}, challenge()),
            ({"probe_id": "seccomp_enforced"}, challenge()),
            ({"audience": "other-audience"}, challenge()),
            ({"nonce": b"Z" * 32}, challenge()),
        )
        for fields, supplied_challenge in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(ObserverAuthenticationError):
                    verifier.verify(make_envelope(**fields), challenge=supplied_challenge)

    def test_challenge_audience_must_match_the_pinned_registry(self):
        verifier, _ = make_verifier()
        other_challenge = challenge(audience="other-audience")
        with self.assertRaisesRegex(ObserverAuthenticationError, "does not match the pinned"):
            verifier.verify(make_envelope(audience="other-audience"), challenge=other_challenge)

    def test_registry_pin_version_audience_and_identity_status_fail_closed(self):
        raw = registry_bytes()
        with self.assertRaisesRegex(ObserverAuthenticationError, "out-of-band pin"):
            PinnedObserverRegistry(
                raw,
                expected_sha256="0" * 64,
                minimum_version=1,
                expected_audience=AUDIENCE,
                now=NOW,
            )
        with self.assertRaisesRegex(ObserverAuthenticationError, "minimum version"):
            make_verifier(minimum_version=4)
        with self.assertRaisesRegex(ObserverAuthenticationError, "audience mismatch"):
            make_verifier(expected_audience="different-audience")
        revoked, _ = make_verifier(status="revoked")
        with self.assertRaisesRegex(ObserverAuthenticationError, "retired or revoked"):
            revoked.verify(make_envelope(), challenge=challenge())

    def test_registry_identity_expiry_is_checked_at_envelope_verification_time(self):
        registry_raw = registry_bytes()
        registry = PinnedObserverRegistry(
            registry_raw,
            expected_sha256=hashlib.sha256(registry_raw).hexdigest(),
            minimum_version=1,
            expected_audience=AUDIENCE,
            now=NOW,
        )
        later = datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc)
        verifier = ObserverEnvelopeVerifier(
            registry=registry,
            signature_verifier=FakeSignatureVerifier(),
            replay_store=MemoryReplayStore(),
            now=later,
        )
        later_challenge = challenge(
            issued_at=later - timedelta(seconds=30),
            expires_at=later + timedelta(seconds=30),
        )
        envelope = make_envelope(observed_at="2026-11-25T10:00:00Z")
        with self.assertRaisesRegex(ObserverAuthenticationError, "outside its validity window"):
            verifier.verify(envelope, challenge=later_challenge)

    def test_registry_rejects_duplicate_identity_and_unknown_domain(self):
        base = json.loads(registry_bytes())
        base["identities"].append(dict(base["identities"][0]))
        with self.assertRaisesRegex(ObserverAuthenticationError, "duplicate identities"):
            make_verifier(registry_raw=canonical(base))

        base = json.loads(registry_bytes())
        base["identities"][0]["observer_domain"] = "provider_api"
        with self.assertRaisesRegex(ObserverAuthenticationError, "unknown trust domain"):
            make_verifier(registry_raw=canonical(base))

        base["identities"][0]["observer_domain"] = ["host_controller"]
        with self.assertRaises(ObserverAuthenticationError):
            make_verifier(registry_raw=canonical(base))

        base = json.loads(registry_bytes())
        base["identities"][0]["status"] = ["active"]
        with self.assertRaises(ObserverAuthenticationError):
            make_verifier(registry_raw=canonical(base))

    def test_payload_digest_and_size_are_verified_before_acceptance(self):
        verifier, _ = make_verifier()
        with self.assertRaisesRegex(ObserverAuthenticationError, "digest does not match"):
            verifier.verify(
                make_envelope(payload=b"changed", payload_sha256=hashlib.sha256(PAYLOAD).hexdigest()),
                challenge=challenge(),
            )
        with self.assertRaisesRegex(ObserverAuthenticationError, "exceeds the size limit"):
            verifier.verify(make_envelope(payload=b"x" * (48 * 1024 + 1)), challenge=challenge())

    def test_timestamp_challenge_window_and_monotonic_bounds_are_checked(self):
        verifier, _ = make_verifier()
        for fields in (
            {"observed_at": "2026-11-24T10:00:00Z"},
            {"observed_at": "2026-11-24T12:10:00Z"},
            {"observed_at": "2026-11-24T11:58:00Z"},
            {"monotonic_start_ns": 201, "monotonic_end_ns": 200},
            {"monotonic_start_ns": -1},
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ObserverAuthenticationError):
                    verifier.verify(make_envelope(**fields), challenge=challenge())

    def test_challenge_rejects_probe_ids_outside_the_acceptance_inventory(self):
        verifier, _ = make_verifier()
        invalid = challenge(probe_id="not_a_real_probe")
        with self.assertRaisesRegex(ObserverAuthenticationError, "not in the pinned"):
            verifier.verify(make_envelope(probe_id="not_a_real_probe"), challenge=invalid)

    def test_naive_challenge_timestamps_are_rejected(self):
        verifier, _ = make_verifier()
        invalid = challenge(issued_at=datetime(2026, 11, 24, 11, 59, 30), expires_at=NOW + timedelta(seconds=30))
        with self.assertRaisesRegex(ObserverAuthenticationError, "timezone-aware"):
            verifier.verify(make_envelope(), challenge=invalid)

    def test_expired_or_overlong_host_challenges_are_rejected(self):
        verifier, _ = make_verifier()
        expired = challenge(
            issued_at=NOW - timedelta(minutes=3),
            expires_at=NOW - timedelta(minutes=1),
        )
        with self.assertRaisesRegex(ObserverAuthenticationError, "expired"):
            verifier.verify(make_envelope(), challenge=expired)
        overlong = challenge(
            issued_at=NOW - timedelta(minutes=3),
            expires_at=NOW + timedelta(seconds=30),
        )
        with self.assertRaisesRegex(ObserverAuthenticationError, "hard limit"):
            verifier.verify(make_envelope(), challenge=overlong)

    def test_invalid_outcome_sequence_and_policy_fields_are_rejected(self):
        verifier, _ = make_verifier()
        for fields in (
            {"outcome": "unknown"},
            {"sequence": 0},
            {"sequence": True},
            {"policy_digest": "not-a-digest"},
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ObserverAuthenticationError):
                    verifier.verify(make_envelope(**fields), challenge=challenge())

    def test_verification_time_policy_has_hard_bounds(self):
        raw = registry_bytes()
        registry = PinnedObserverRegistry(
            raw,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            minimum_version=1,
            expected_audience=AUDIENCE,
            now=NOW,
        )
        for kwargs in (
            {"max_age_seconds": 3601},
            {"max_age_seconds": True},
            {"allowed_clock_skew_seconds": 121},
            {"allowed_clock_skew_seconds": -1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ObserverAuthenticationError):
                    ObserverEnvelopeVerifier(
                        registry=registry,
                        signature_verifier=FakeSignatureVerifier(),
                        replay_store=MemoryReplayStore(),
                        now=NOW,
                        **kwargs,
                    )

    def test_replay_store_failure_fails_closed(self):
        verifier, _ = make_verifier(store=FailingReplayStore())
        with self.assertRaisesRegex(ObserverAuthenticationError, "Replay store unavailable"):
            verifier.verify(make_envelope(), challenge=challenge())

    def test_duplicate_json_keys_and_noncanonical_json_are_rejected(self):
        verifier, _ = make_verifier()
        duplicate = b'{"schema_version":1,"schema_version":1}'
        with self.assertRaisesRegex(ObserverAuthenticationError, "duplicate keys"):
            verifier.verify(duplicate, challenge=challenge())
        noncanonical = json.dumps(json.loads(make_envelope()), indent=2).encode("utf-8")
        with self.assertRaisesRegex(ObserverAuthenticationError, "canonical JSON"):
            verifier.verify(noncanonical, challenge=challenge())


if __name__ == "__main__":
    unittest.main()
