import base64
import hashlib
import json
import unittest
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES, SUITE_ID, SUITE_VERSION
from tools.task_orchestrator.sandbox_trusted_report_signer import (
    TrustedReportSigner,
    TrustedReportSigningError,
)


NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
VERIFIER = "independent-verifier-prod"
VERIFIER_KEY_ID = "verifier-attestation-key-01"
AUDIENCE = "sandbox-acceptance-prod"
KEY_ID = "acceptance-report-key-01"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class FakeAttestationVerifier:
    def verify(self, verifier_id, verifier_key_id, message, signature):
        material = verifier_id.encode() + b"\x00" + verifier_key_id.encode() + b"\x00" + message
        return signature == hashlib.sha512(material).digest()


class FakeAuthorizationStore:
    def __init__(self):
        self.used = set()
        self.records = []
    def consume(self, *, verifier_id, verifier_key_id, audience, verification_id, report_sha256, envelope_manifest_sha256, accepted_at, expires_at):
        if verification_id in self.used:
            return False
        self.used.add(verification_id)
        self.records.append({
            "verifier_id": verifier_id, "verifier_key_id": verifier_key_id,
            "audience": audience, "verification_id": verification_id,
            "report_sha256": report_sha256,
            "envelope_manifest_sha256": envelope_manifest_sha256,
            "accepted_at": accepted_at, "expires_at": expires_at,
        })
        return True


class FakeSigningBackend:
    def __init__(self):
        self.calls = []
    def sign(self, key_id, message):
        self.calls.append((key_id, message))
        return hashlib.sha512(key_id.encode() + b"\x00" + message).digest()


class TrustedReportSignerTests(unittest.TestCase):
    def setUp(self):
        self.manifest = canonical({"schema_version": 1, "attempt_id": "attempt-001", "entries": []})
        self.report = canonical({
            "schema_version": 3,
            "suite_id": SUITE_ID,
            "suite_version": SUITE_VERSION,
            "key_id": KEY_ID,
            "provider_id": "fixture-provider",
            "region": "eu-test-1",
            "runtime_id": "runtime-001",
            "task_id": "task-001",
            "attempt_id": "attempt-001",
            "image_digest": "sha256:" + "b" * 64,
            "policy_digest": "sha256:" + "a" * 64,
            "started_at": "2026-11-24T11:55:00Z",
            "completed_at": "2026-11-24T11:59:55Z",
            "probes": [
                {"probe_id": probe_id, "outcome": "pass", "evidence_sha256": hashlib.sha256(probe_id.encode()).hexdigest()}
                for probe_id in sorted(REQUIRED_PROBES)
            ],
            "observer_registry_sha256": "c" * 64,
            "observer_registry_version": 3,
            "observer_provenance_sha256": hashlib.sha256(b"[]").hexdigest(),
            "observer_provenance": [],
            "observer_envelope_manifest_version": 1,
            "observer_envelope_manifest_sha256": hashlib.sha256(self.manifest).hexdigest(),
        })
        self.store = FakeAuthorizationStore()
        self.backend = FakeSigningBackend()
        self.signer = TrustedReportSigner(
            verifier_id=VERIFIER, verifier_key_id=VERIFIER_KEY_ID, audience=AUDIENCE, signing_key_id=KEY_ID,
            attestation_verifier=FakeAttestationVerifier(),
            authorization_store=self.store, signing_backend=self.backend,
            trusted_clock=lambda: NOW,
        )

    def attestation(self, **overrides):
        value = {
            "schema_version": 1, "verifier_id": VERIFIER, "verifier_key_id": VERIFIER_KEY_ID, "audience": AUDIENCE,
            "report_sha256": hashlib.sha256(self.report).hexdigest(),
            "envelope_manifest_sha256": hashlib.sha256(self.manifest).hexdigest(),
            "verification_id": "verify-0001", "issued_at": "2026-11-24T11:59:30Z",
            "expires_at": "2026-11-24T12:00:30Z", "signature_algorithm": "Ed25519",
        }
        value.update(overrides)
        material = VERIFIER.encode() + b"\x00" + VERIFIER_KEY_ID.encode() + b"\x00" + canonical(value)
        signature = hashlib.sha512(material).digest()
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
        with self.assertRaisesRegex(TrustedReportSigningError, "canonical JSON object"):
            self.signer.sign(self.report + b" ", self.attestation(), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "exact supplied envelope-manifest"):
            self.signer.sign(self.report, self.attestation(), self.manifest + b" ")
        self.assertEqual(self.backend.calls, [])

    def test_wrong_verifier_audience_or_key_id_is_rejected(self):
        with self.assertRaises(TrustedReportSigningError):
            self.signer.sign(self.report, self.attestation(verifier_id="untrusted-verifier"), self.manifest)
        with self.assertRaises(TrustedReportSigningError):
            self.signer.sign(self.report, self.attestation(verifier_key_id="untrusted-key"), self.manifest)
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
        record = self.store.records[0]
        self.assertEqual(record["verifier_id"], VERIFIER)
        self.assertEqual(record["verifier_key_id"], VERIFIER_KEY_ID)
        self.assertEqual(record["audience"], AUDIENCE)
        self.assertEqual(record["report_sha256"], hashlib.sha256(self.report).hexdigest())
        self.assertEqual(record["envelope_manifest_sha256"], hashlib.sha256(self.manifest).hexdigest())
        with self.assertRaisesRegex(TrustedReportSigningError, "already consumed"):
            self.signer.sign(self.report, attestation, self.manifest)
        self.assertEqual(len(self.backend.calls), 1)

    def test_verifier_and_report_signing_keys_must_be_distinct(self):
        with self.assertRaisesRegex(TrustedReportSigningError, "must be distinct"):
            TrustedReportSigner(
                verifier_id=VERIFIER,
                verifier_key_id=KEY_ID,
                audience=AUDIENCE,
                signing_key_id=KEY_ID,
                attestation_verifier=FakeAttestationVerifier(),
                authorization_store=FakeAuthorizationStore(),
                signing_backend=FakeSigningBackend(),
                trusted_clock=lambda: NOW,
            )

    def test_noncanonical_or_non_v3_reports_are_rejected(self):
        with self.assertRaisesRegex(TrustedReportSigningError, "canonical"):
            self.signer.sign(self.report + b" ", self.attestation(), self.manifest)
        with self.assertRaisesRegex(TrustedReportSigningError, "strict schema-v3"):
            self.signer.sign(canonical({"schema_version": 2, "key_id": KEY_ID}), self.attestation(), self.manifest)
        self.assertEqual(self.backend.calls, [])


if __name__ == "__main__":
    unittest.main()
