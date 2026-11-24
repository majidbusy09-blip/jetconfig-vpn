import base64
import hashlib
import json
import unittest
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_trusted_report_signer import (
    TrustedReportSigner,
    TrustedReportSigningError,
)


NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
VERIFIER = "independent-verifier-prod"
AUDIENCE = "sandbox-acceptance-prod"
KEY_ID = "acceptance-report-key-01"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class FakeAttestationVerifier:
    def verify(self, verifier_id, message, signature):
        return signature == hashlib.sha512(verifier_id.encode() + b"\x00" + message).digest()


class FakeAuthorizationStore:
    def __init__(self):
        self.used = set()
    def consume(self, *, verification_id, report_sha256, accepted_at, expires_at):
        if verification_id in self.used:
            return False
        self.used.add(verification_id)
        return True


class FakeSigningBackend:
    def __init__(self):
        self.calls = []
    def sign(self, key_id, message):
        self.calls.append((key_id, message))
        return hashlib.sha512(key_id.encode() + b"\x00" + message).digest()


class TrustedReportSignerTests(unittest.TestCase):
    def setUp(self):
        self.report = canonical({
            "schema_version": 3, "key_id": KEY_ID,
            "attempt_id": "attempt-001", "probes": [{"probe_id": "p1", "outcome": "pass"}],
        })
        self.manifest = canonical({"schema_version": 1, "attempt_id": "attempt-001", "entries": []})
        self.store = FakeAuthorizationStore()
        self.backend = FakeSigningBackend()
        self.signer = TrustedReportSigner(
            verifier_id=VERIFIER, audience=AUDIENCE, signing_key_id=KEY_ID,
            attestation_verifier=FakeAttestationVerifier(),
            authorization_store=self.store, signing_backend=self.backend,
            trusted_clock=lambda: NOW,
        )

    def attestation(self, **overrides):
        value = {
            "schema_version": 1, "verifier_id": VERIFIER, "audience": AUDIENCE,
            "report_sha256": hashlib.sha256(self.report).hexdigest(),
            "envelope_manifest_sha256": hashlib.sha256(self.manifest).hexdigest(),
            "verification_id": "verify-0001", "issued_at": "2026-11-24T11:59:30Z",
            "expires_at": "2026-11-24T12:00:30Z", "signature_algorithm": "Ed25519",
        }
        value.update(overrides)
        signature = hashlib.sha512(VERIFIER.encode() + b"\x00" + canonical(value)).digest()
        value["signature_b64"] = base64.b64encode(signature).decode()
        return canonical(value)

    def test_only_verifier_attested_exact_report_and_manifest_are_signed(self):
        attestation = self.attestation()
        signed = self.signer.sign(self.report, attestation, self.manifest)
        self.assertEqual(signed.report_bytes, self.report)
        self.assertEqual(signed.report_sha256, hashlib.sha256(self.report).hexdigest())
        self.assertEqual(signed.key_id, KEY_ID)
        self.assertEqual(len(signed.signature), 64)
        self.assertEqual(self.backend.calls, [(KEY_ID, self.report)])

    def test_report_or_manifest_tampering_is_rejected_before_signing(self):
        with self.assertRaisesRegex(TrustedReportSigningError, "exact report/manifest"):
            self.signer.sign(self.report + b" ", self.attestation(), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "exact report/manifest"):
            self.signer.sign(self.report, self.attestation(), self.manifest + b" ")
        self.assertEqual(self.backend.calls, [])

    def test_wrong_verifier_audience_or_key_id_is_rejected(self):
        with self.assertRaises(TrustedReportSigningError):
            self.signer.sign(self.report, self.attestation(verifier_id="untrusted-verifier"), self.manifest)
        with self.assertRaises(TrustedReportSigningError):
            self.signer.sign(self.report, self.attestation(audience="wrong-audience"), self.manifest)
        wrong_key = canonical({"schema_version": 3, "key_id": "other-key"})
        with self.assertRaises(TrustedReportSigningError):
            self.signer.sign(wrong_key, self.attestation(), self.manifest)
        self.assertEqual(self.backend.calls, [])

    def test_invalid_signature_expired_and_overlong_attestations_fail_closed(self):
        bad = json.loads(self.attestation())
        bad["signature_b64"] = base64.b64encode(b"X" * 64).decode()
        with self.assertRaisesRegex(TrustedReportSigningError, "signature is invalid"):
            self.signer.sign(self.report, canonical(bad), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "expired"):
            self.signer.sign(self.report, self.attestation(expires_at="2026-11-24T11:59:59Z"), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "hard limit"):
            self.signer.sign(self.report, self.attestation(expires_at="2026-11-24T12:05:00Z"), self.manifest)
        self.assertEqual(self.backend.calls, [])

    def test_attestation_is_one_time_and_store_failure_blocks_signing(self):
        attestation = self.attestation()
        self.signer.sign(self.report, attestation, self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "already consumed"):
            self.signer.sign(self.report, attestation, self.manifest)
        self.assertEqual(len(self.backend.calls), 1)

    def test_noncanonical_or_non_v3_reports_are_rejected(self):
        with self.assertRaisesRegex(TrustedReportSigningError, "canonical"):
            self.signer.sign(self.report + b" ", self.attestation(), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "schema-v3"):
            self.signer.sign(canonical({"schema_version": 2, "key_id": KEY_ID}), self.attestation(), self.manifest)
        self.assertEqual(self.backend.calls, [])


if __name__ == "__main__":
    unittest.main()
