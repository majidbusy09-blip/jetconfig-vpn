import base64
import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_trust import (
    PinnedTrustStoreVerifier,
    TrustStoreError,
)


NOW = datetime(2026, 11, 24, 8, 0, 0, tzinfo=timezone.utc)
PUBLIC_KEY = bytes(range(32))


class FakeEd25519Backend:
    """Deterministic test double; this is not cryptographic verification."""

    def verify(self, public_key, message, signature):
        return public_key == PUBLIC_KEY and signature == hashlib.sha256(public_key + message).digest()


def document(**changes):
    key = {
        "key_id": "sandbox-acceptance-2026-01",
        "algorithm": "Ed25519",
        "public_key_b64": base64.b64encode(PUBLIC_KEY).decode("ascii"),
        "not_before": "2026-01-01T00:00:00Z",
        "not_after": "2027-01-01T00:00:00Z",
        "status": "active",
    }
    result = {"schema_version": 1, "version": 3, "keys": [key]}
    result.update(changes)
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verifier(raw=None, *, digest=None, minimum_version=3, now=NOW, backend=None):
    raw = canonical(document()) if raw is None else raw
    return PinnedTrustStoreVerifier(
        trust_store_bytes=raw,
        expected_sha256=hashlib.sha256(raw).hexdigest() if digest is None else digest,
        minimum_version=minimum_version,
        now=now,
        backend=FakeEd25519Backend() if backend is None else backend,
    )


class PinnedSandboxTrustStoreTests(unittest.TestCase):
    def test_active_pinned_key_verifies_through_injected_backend(self):
        trusted = verifier()
        message = b"canonical acceptance report"
        signature = hashlib.sha256(PUBLIC_KEY + message).digest()
        self.assertTrue(trusted.verify("sandbox-acceptance-2026-01", message, signature))
        self.assertFalse(trusted.verify("unknown-key", message, signature))
        self.assertFalse(trusted.verify("sandbox-acceptance-2026-01", message, b"bad"))

    def test_rejects_digest_mismatch_and_noncanonical_store(self):
        raw = canonical(document())
        with self.assertRaisesRegex(TrustStoreError, "pinned digest"):
            verifier(raw, digest="0" * 64)
        with self.assertRaisesRegex(TrustStoreError, "canonical"):
            verifier(raw + b" ")

    def test_rejects_rollback_below_protected_minimum_version(self):
        raw = canonical(document(version=2))
        with self.assertRaisesRegex(TrustStoreError, "below the protected minimum"):
            verifier(raw, minimum_version=3)

    def test_rejects_duplicate_ids_and_duplicate_json_keys(self):
        duplicate = document()
        duplicate["keys"].append(dict(duplicate["keys"][0]))
        with self.assertRaisesRegex(TrustStoreError, "duplicate key ID"):
            verifier(canonical(duplicate))
        with self.assertRaisesRegex(TrustStoreError, "duplicate JSON"):
            verifier(b'{"schema_version":1,"schema_version":1,"version":3,"keys":[]}')

    def test_rejects_revoked_retired_and_out_of_window_keys(self):
        for status in ("revoked", "retired"):
            value = document()
            value["keys"][0]["status"] = status
            trusted = verifier(canonical(value))
            self.assertFalse(trusted.verify(value["keys"][0]["key_id"], b"message", b"signature"))
        for field, value in (
            ("not_before", "2027-01-01T00:00:00Z"),
            ("not_after", "2026-01-01T00:00:00Z"),
        ):
            item = document()
            item["keys"][0][field] = value
            trusted = verifier(canonical(item))
            self.assertFalse(trusted.verify(item["keys"][0]["key_id"], b"message", b"signature"))

    def test_rejects_wrong_algorithm_bad_key_length_and_invalid_validity(self):
        mutations = (
            lambda d: d["keys"][0].update(algorithm="RSA"),
            lambda d: d["keys"][0].update(public_key_b64=base64.b64encode(b"short").decode()),
            lambda d: d["keys"][0].update(not_after="2025-01-01T00:00:00Z"),
            lambda d: d["keys"][0].update(status="pending"),
        )
        for mutate in mutations:
            value = document()
            mutate(value)
            with self.subTest(mutation=mutate):
                with self.assertRaises(TrustStoreError):
                    verifier(canonical(value))

    def test_rejects_malformed_or_untrusted_inputs(self):
        for raw in (b"", b"not-json", b"{}"):
            with self.subTest(raw=raw):
                with self.assertRaises(TrustStoreError):
                    verifier(raw)
        with self.assertRaises(TrustStoreError):
            verifier(b"x" * (64 * 1024 + 1))
        with self.assertRaises(TrustStoreError):
            verifier(minimum_version=True)
        with self.assertRaises(TrustStoreError):
            verifier(now=datetime(2026, 11, 24, 8, 0))

    def test_backend_errors_and_non_true_results_fail_closed(self):
        class Broken:
            def verify(self, public_key, message, signature):
                raise RuntimeError("do not leak")

        class Truthy:
            def verify(self, public_key, message, signature):
                return 1

        for backend in (Broken(), Truthy()):
            self.assertFalse(verifier(backend=backend).verify("sandbox-acceptance-2026-01", b"m", b"s"))

    def test_rejects_excessive_key_inventory(self):
        value = document()
        value["keys"] = [dict(value["keys"][0], key_id=f"key-{i}") for i in range(65)]
        with self.assertRaisesRegex(TrustStoreError, "between 1 and 64"):
            verifier(canonical(value))


if __name__ == "__main__":
    unittest.main()
