import base64
import hashlib
import json
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from tools.task_orchestrator.sandbox_observer_auth import (
    ObserverAuthenticationError,
    ObserverChallenge,
    ObserverEnvelopeVerifier,
    ObserverReplayReceipt,
    PinnedObserverRegistry,
    issue_observer_challenge,
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
        self.envelopes = set()
        self.last_sequence = {}
        self.records = []
        self.receipts = {}
        self.ledger_revision = 0
        self.fencing_epoch = 1

    def consume(self, **record):
        observer_id = record["observer_id"]
        nonce_sha256 = record["nonce_sha256"]
        envelope_sha256 = record["envelope_sha256"]
        sequence = record["sequence"]
        if (
            nonce_sha256 in self.nonces
            or envelope_sha256 in self.envelopes
            or sequence <= self.last_sequence.get(observer_id, 0)
        ):
            return None
        required_context = (
            "observer_domain", "attempt_id", "runtime_id", "policy_digest",
            "probe_id", "observer_registry_sha256", "observer_registry_version",
            "key_id", "challenge_expires_at", "accepted_at",
        )
        if any(record.get(field) in (None, "") for field in required_context):
            return None
        self.nonces.add(nonce_sha256)
        self.envelopes.add(envelope_sha256)
        self.last_sequence[observer_id] = sequence
        self.ledger_revision += 1
        receipt = ObserverReplayReceipt(
            **record,
            ledger_revision=self.ledger_revision,
            fencing_epoch=self.fencing_epoch,
        )
        self.receipts[(observer_id, envelope_sha256)] = receipt
        self.records.append(dict(record))
        return receipt

    def get_acceptance(self, *, observer_id, envelope_sha256):
        return self.receipts.get((observer_id, envelope_sha256))


class FailingReplayStore:
    def consume(self, **kwargs):
        raise OSError("fixture store unavailable")

    def get_acceptance(self, **kwargs):
        return None


class MissingReceiptReadbackStore(MemoryReplayStore):
    def get_acceptance(self, *, observer_id, envelope_sha256):
        return None


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
        accepted = replay.records[0]
        self.assertEqual(accepted["attempt_id"], ATTEMPT)
        self.assertEqual(accepted["runtime_id"], RUNTIME)
        self.assertEqual(accepted["policy_digest"], POLICY)
        self.assertEqual(accepted["probe_id"], PROBE)
        self.assertEqual(accepted["observer_registry_sha256"], hashlib.sha256(registry_bytes()).hexdigest())
        self.assertEqual(accepted["observer_registry_version"], 3)
        self.assertEqual(accepted["key_id"], KEY_ID)
        self.assertEqual(accepted["challenge_expires_at"], "2026-11-24T12:00:30Z")
        self.assertEqual(accepted["accepted_at"], "2026-11-24T12:00:00.000000Z")
        receipt = replay.get_acceptance(observer_id=OBSERVER, envelope_sha256=result.envelope_sha256)
        self.assertIsInstance(receipt, ObserverReplayReceipt)
        self.assertEqual(receipt.ledger_revision, 1)
        self.assertEqual(receipt.fencing_epoch, 1)
        self.assertEqual(result.accepted_at, receipt.accepted_at)
        self.assertEqual(result.challenge_expires_at, receipt.challenge_expires_at)
        self.assertEqual(result.ledger_revision, receipt.ledger_revision)
        self.assertEqual(result.fencing_epoch, receipt.fencing_epoch)
        with self.assertRaises(AttributeError):
            receipt.sequence = 99

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

    def test_challenge_rejects_fractional_second_expiry(self):
        verifier, _ = make_verifier()
        fractional = challenge(expires_at=NOW + timedelta(seconds=30, microseconds=1))
        with self.assertRaisesRegex(ObserverAuthenticationError, "exact UTC second precision"):
            verifier.verify(make_envelope(), challenge=fractional)

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

    def test_missing_replay_receipt_readback_fails_closed(self):
        verifier, store = make_verifier(store=MissingReceiptReadbackStore())
        with self.assertRaisesRegex(ObserverAuthenticationError, "could not be independently read back"):
            verifier.verify(make_envelope(), challenge=challenge())
        self.assertEqual(store.last_sequence[OBSERVER], 1)

    def test_replay_store_requires_read_only_receipt_lookup(self):
        class ConsumeOnlyStore:
            def consume(self, **kwargs):
                return True

        with self.assertRaisesRegex(ObserverAuthenticationError, "read-only receipt lookup"):
            make_verifier(store=ConsumeOnlyStore())

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


class ObserverChallengeIssuerTests(unittest.TestCase):
    def setUp(self):
        raw = registry_bytes()
        self.registry = PinnedObserverRegistry(
            raw,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            minimum_version=3,
            expected_audience=AUDIENCE,
            now=NOW,
        )

    def issue(self, **overrides):
        values = {
            "registry": self.registry,
            "observer_id": OBSERVER,
            "observer_domain": DOMAIN,
            "key_id": KEY_ID,
            "attempt_id": ATTEMPT,
            "runtime_id": RUNTIME,
            "policy_digest": POLICY,
            "probe_id": PROBE,
            "now": NOW,
        }
        values.update(overrides)
        return issue_observer_challenge(**values)

    def test_uses_os_csprng_and_binds_all_host_context(self):
        with patch("tools.task_orchestrator.sandbox_observer_auth.secrets.token_bytes", return_value=b"R" * 32) as rng:
            issued = self.issue(lifetime_seconds=45)
        rng.assert_called_once_with(32)
        self.assertEqual(issued.nonce, b"R" * 32)
        self.assertEqual(issued.audience, AUDIENCE)
        self.assertEqual(issued.observer_id, OBSERVER)
        self.assertEqual(issued.observer_domain, DOMAIN)
        self.assertEqual(issued.attempt_id, ATTEMPT)
        self.assertEqual(issued.runtime_id, RUNTIME)
        self.assertEqual(issued.policy_digest, POLICY)
        self.assertEqual(issued.probe_id, PROBE)
        self.assertEqual(issued.expires_at - issued.issued_at, timedelta(seconds=45))
        issued.validate(NOW)

    def test_rejects_invalid_lifetime_and_identity(self):
        for lifetime in (0, 121, True, 1.5):
            with self.subTest(lifetime=lifetime), self.assertRaises(ObserverAuthenticationError):
                self.issue(lifetime_seconds=lifetime)
        with self.assertRaises(ObserverAuthenticationError):
            self.issue(key_id="untrusted-key")

    def test_rejects_csprng_failure_or_wrong_length(self):
        with patch("tools.task_orchestrator.sandbox_observer_auth.secrets.token_bytes", side_effect=OSError("entropy unavailable")):
            with self.assertRaises(ObserverAuthenticationError):
                self.issue()
        with patch("tools.task_orchestrator.sandbox_observer_auth.secrets.token_bytes", return_value=b"short"):
            with self.assertRaises(ObserverAuthenticationError):
                self.issue()

    def test_rejects_non_utc_clock_and_unknown_probe(self):
        with self.assertRaises(ObserverAuthenticationError):
            self.issue(now=NOW.replace(tzinfo=None))
        with self.assertRaises(ObserverAuthenticationError):
            self.issue(probe_id="not-in-the-acceptance-manifest")

    def test_does_not_issue_challenge_past_key_expiry(self):
        near_expiry = datetime(2026, 11, 25, 9, 59, 30, tzinfo=timezone.utc)
        with self.assertRaises(ObserverAuthenticationError):
            self.issue(now=near_expiry, lifetime_seconds=60)
