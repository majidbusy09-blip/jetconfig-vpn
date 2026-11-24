import base64, hashlib, json, unittest
from datetime import datetime, timedelta, timezone
from tools.task_orchestrator.trust_config_acceptance import (
    AcceptedTrustConfig, MonotonicState, TrustAudience, TrustConfigError,
    accept_trust_config,
)

NOW = datetime(2026, 11, 24, 8, 0, 0, tzinfo=timezone.utc)
AUDIENCE = TrustAudience("test", "verifier-a", "fixture-provider", "eu-test")
PUB = bytes(range(32))
SIG = b"\x42" * 64

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def trust_bytes(version=3):
    key = {"key_id":"fixture-key", "algorithm":"Ed25519",
        "public_key_b64":base64.b64encode(PUB).decode(),
        "not_before":"2026-01-01T00:00:00Z", "not_after":"2027-01-01T00:00:00Z",
        "status":"active"}
    return canonical({"schema_version":1, "version":version, "keys":[key]})

def envelope(*, epoch=1, version=3, issued="2026-11-24T07:59:00Z",
             expires="2026-11-24T08:30:00Z", audience=None, signature=SIG,
             digest_override=None, trust_override=None):
    raw = trust_bytes(version) if trust_override is None else trust_override
    doc = {"schema_version":1,
        "audience": {"environment":"test","deployment":"verifier-a","provider":"fixture-provider","region":"eu-test"} if audience is None else audience,
        "config_epoch":epoch, "trust_store_version_floor":version,
        "trust_store_sha256":digest_override or hashlib.sha256(raw).hexdigest(),
        "trust_store_bytes":raw.decode("utf-8", errors="strict"),
        "issued_at":issued, "expires_at":expires, "root_key_id":"offline-root-1",
        "signature_algorithm":"Ed25519", "signature_b64":base64.b64encode(signature).decode()}
    return canonical(doc)

class FakeRootVerifier:
    """Test-only deterministic fixture; not cryptographic root verification."""
    def verify(self, key_id, message, signature):
        return key_id == "offline-root-1" and signature == SIG and bool(message)

class FakeTrustBackend:
    def verify(self, public_key, message, signature):
        return False

class MemoryCASStore:
    """Test-only in-memory fake; never production anti-rollback storage."""
    def __init__(self):
        self.state = None
        self.audit = []
        self.fail_read = False
        self.fail_commit = False
    def read(self, audience):
        if self.fail_read: raise OSError("fixture unavailable")
        return self.state
    def compare_and_swap(self, audience, expected_revision, new_state, audit_record):
        if self.fail_commit: raise OSError("fixture transaction failed")
        actual = None if self.state is None else self.state.revision
        if actual != expected_revision: return False
        self.state = new_state
        self.audit.append(audit_record)
        return True

def accept(raw, store=None, **kwargs):
    return accept_trust_config(raw, expected_audience=kwargs.pop("expected_audience", AUDIENCE),
        now=kwargs.pop("now", NOW), root_verifier=kwargs.pop("root_verifier", FakeRootVerifier()),
        store=store or MemoryCASStore(), trust_store_backend=FakeTrustBackend(), **kwargs)

class TrustConfigAcceptanceTests(unittest.TestCase):
    def setUp(self): self.store = MemoryCASStore()

    def test_valid_envelope_commits_state_and_audit_before_return(self):
        result = accept(envelope(), self.store)
        self.assertIsInstance(result, AcceptedTrustConfig)
        self.assertEqual(result.config_epoch, 1)
        self.assertEqual(result.trust_store_version, 3)
        self.assertEqual(self.store.state.envelope_sha256, result.envelope_sha256)
        self.assertEqual(len(self.store.audit), 1)
        self.assertEqual(self.store.audit[0].outcome, "accepted")

    def test_exact_same_envelope_is_idempotent_without_second_write(self):
        raw = envelope()
        first = accept(raw, self.store)
        second = accept(raw, self.store)
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.audit), 1)

    def test_wrong_signature_and_unknown_root_fail_closed(self):
        with self.assertRaisesRegex(TrustConfigError, "signature"):
            accept(envelope(signature=b"\x43" * 64), self.store)

    def test_audience_mismatch_fails_closed(self):
        with self.assertRaisesRegex(TrustConfigError, "audience"):
            accept(envelope(), self.store, expected_audience=TrustAudience("prod","verifier-a","fixture-provider","eu-test"))

    def test_expired_future_issued_and_excessive_lifetime_rejected(self):
        cases = [
            envelope(expires="2026-11-24T07:59:59Z"),
            envelope(issued="2026-11-24T08:00:01Z"),
            envelope(issued="2026-11-24T07:00:00Z", expires="2026-11-24T09:00:01Z"),
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(TrustConfigError): accept(raw, MemoryCASStore())

    def test_duplicate_keys_noncanonical_and_invalid_utf8_rejected(self):
        raw = envelope()
        with self.assertRaisesRegex(TrustConfigError, "canonical"):
            accept(raw + b" ", MemoryCASStore())
        with self.assertRaisesRegex(TrustConfigError, "duplicate"):
            accept(b'{"schema_version":1,"schema_version":1}', MemoryCASStore())
        with self.assertRaises(TrustConfigError):
            accept(b"\xff", MemoryCASStore())

    def test_digest_mismatch_and_malformed_trust_store_rejected(self):
        with self.assertRaisesRegex(TrustConfigError, "digest"):
            accept(envelope(digest_override="0" * 64), MemoryCASStore())
        with self.assertRaisesRegex(TrustConfigError, "trust store"):
            accept(envelope(trust_override=b"{}"), MemoryCASStore())

    def test_lower_epoch_and_lower_trust_store_version_rejected(self):
        accept(envelope(epoch=5, version=5), self.store)
        with self.assertRaisesRegex(TrustConfigError, "rollback"):
            accept(envelope(epoch=4, version=6), self.store)
        with self.assertRaisesRegex(TrustConfigError, "rollback"):
            accept(envelope(epoch=6, version=4), self.store)

    def test_same_epoch_different_envelope_is_conflict(self):
        accept(envelope(epoch=7), self.store)
        with self.assertRaisesRegex(TrustConfigError, "conflict"):
            accept(envelope(epoch=7, expires="2026-11-24T08:31:00Z"), self.store)

    def test_cas_race_does_not_return_accepted_config(self):
        class RacingStore(MemoryCASStore):
            def compare_and_swap(self, audience, expected_revision, new_state, audit_record):
                return False
        with self.assertRaisesRegex(TrustConfigError, "CAS race"):
            accept(envelope(), RacingStore())

    def test_store_read_and_atomic_audit_commit_fail_closed(self):
        unavailable = MemoryCASStore(); unavailable.fail_read = True
        with self.assertRaisesRegex(TrustConfigError, "unavailable"):
            accept(envelope(), unavailable)
        broken = MemoryCASStore(); broken.fail_commit = True
        with self.assertRaisesRegex(TrustConfigError, "transaction"):
            accept(envelope(), broken)
        self.assertIsNone(broken.state)
        self.assertEqual(broken.audit, [])

    def test_rejects_boolean_counters_non_ed25519_and_bad_time_source(self):
        for raw in (envelope(epoch=True), envelope(version=True)):
            with self.assertRaises(TrustConfigError): accept(raw, MemoryCASStore())
        doc = json.loads(envelope())
        doc["signature_algorithm"] = "RSA"
        with self.assertRaisesRegex(TrustConfigError, "Ed25519"):
            accept(canonical(doc), MemoryCASStore())
        with self.assertRaisesRegex(TrustConfigError, "UTC"):
            accept(envelope(), MemoryCASStore(), now=datetime(2026,11,24,8,0))

    def test_envelope_size_and_nesting_limits(self):
        with self.assertRaisesRegex(TrustConfigError, "size"):
            accept(b"x" * (128 * 1024 + 1), MemoryCASStore())
        doc = json.loads(envelope())
        doc["extra"] = [[[[[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]]]]]
        with self.assertRaisesRegex(TrustConfigError, "fields|nesting"):
            accept(canonical(doc), MemoryCASStore())

if __name__ == "__main__": unittest.main()
