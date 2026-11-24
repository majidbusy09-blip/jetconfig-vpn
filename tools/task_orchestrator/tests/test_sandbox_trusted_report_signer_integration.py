import unittest
from datetime import datetime, timezone
import hashlib

from test_sandbox_acceptance_report_v3 import make_case
from tools.task_orchestrator.sandbox_acceptance_report_v3 import build_schema_v3_report_draft
from tools.task_orchestrator.sandbox_acceptance_report_v3_verifier import verify_signed_acceptance_report_v3
from test_sandbox_trusted_report_signer import (
    AUDIENCE,
    VERIFIER,
    VERIFIER_KEY_ID,
    FakeAttestationVerifier,
    FakeAuthorizationStore,
    FakeSigningBackend,
)
from tools.task_orchestrator.sandbox_acceptance_report_v3_verifier import SchemaV3VerificationAttestor
from tools.task_orchestrator.sandbox_trusted_report_signer import TrustedReportSigner


class FakeReportSignatureVerifier:
    def verify(self, key_id, message, signature):
        return signature == hashlib.sha512(key_id.encode() + b"\x00" + message).digest()


def make_unsigned_case():
    expected, registry, observer_verifier, reader, evidence, results, envelopes = make_case()
    draft = build_schema_v3_report_draft(
        expected,
        started_at="2026-11-24T11:55:00Z",
        completed_at="2026-11-24T11:59:55Z",
        probe_evidence=evidence,
        observer_results=results,
        raw_observer_envelopes=envelopes,
        registry=registry,
        observer_signature_verifier=observer_verifier,
        replay_receipt_reader=reader,
    )
    return {
        "expected": expected, "registry": registry,
        "observer_verifier": observer_verifier, "reader": reader,
        "evidence": evidence, "envelopes": envelopes, "draft": draft,
    }


class BoundVerifierAttestationSigner:
    def __init__(self, verifier_id):
        self.verifier_id = verifier_id
        self.calls = []
    def sign(self, key_id, message):
        self.calls.append((key_id, message))
        material = self.verifier_id.encode() + b"\x00" + key_id.encode() + b"\x00" + message
        return hashlib.sha512(material).digest()


class TrustedReportSignerIntegrationTests(unittest.TestCase):
    def test_only_fully_verified_schema_v3_report_reaches_report_signing_backend(self):
        case = make_unsigned_case()
        verifier_attestation_backend = BoundVerifierAttestationSigner(VERIFIER)
        attestor = SchemaV3VerificationAttestor(
            verifier_id=VERIFIER,
            verifier_key_id=VERIFIER_KEY_ID,
            audience=AUDIENCE,
            attestation_signer=verifier_attestation_backend,
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
            lifetime_seconds=60,
        )
        authorization = attestor.verify_and_attest(
            case["draft"].report_bytes,
            case["expected"],
            probe_evidence=case["evidence"],
            raw_observer_envelopes=case["envelopes"],
            envelope_manifest_bytes=case["draft"].envelope_manifest_bytes,
            registry=case["registry"],
            observer_signature_verifier=case["observer_verifier"],
            replay_receipt_reader=case["reader"],
        )

        report_backend = FakeSigningBackend()
        report_signer = TrustedReportSigner(
            verifier_id=VERIFIER,
            verifier_key_id=VERIFIER_KEY_ID,
            audience=AUDIENCE,
            signing_key_id=case["expected"].acceptance.trusted_key_id,
            attestation_verifier=FakeAttestationVerifier(),
            authorization_store=FakeAuthorizationStore(),
            signing_backend=report_backend,
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 1, tzinfo=timezone.utc),
        )
        signed = report_signer.sign(
            case["draft"].report_bytes,
            authorization.attestation_bytes,
            case["draft"].envelope_manifest_bytes,
        )
        self.assertEqual(signed.report_sha256, case["draft"].report_sha256)
        self.assertEqual(signed.key_id, case["expected"].acceptance.trusted_key_id)
        self.assertEqual(len(verifier_attestation_backend.calls), 1)
        self.assertEqual(len(report_backend.calls), 1)
        self.assertEqual(report_backend.calls[0][1], case["draft"].report_bytes)
        final_verification = verify_signed_acceptance_report_v3(
            case["draft"].report_bytes,
            signed.signature,
            case["expected"],
            FakeReportSignatureVerifier(),
            probe_evidence=case["evidence"],
            raw_observer_envelopes=case["envelopes"],
            envelope_manifest_bytes=case["draft"].envelope_manifest_bytes,
            registry=case["registry"],
            observer_signature_verifier=case["observer_verifier"],
            replay_receipt_reader=case["reader"],
        )
        self.assertTrue(final_verification["signature_verified"])
        self.assertTrue(final_verification["content_verified"])

    def test_invalid_report_never_produces_attestation_or_report_signature(self):
        case = make_unsigned_case()
        verifier_backend = BoundVerifierAttestationSigner(VERIFIER)
        attestor = SchemaV3VerificationAttestor(
            verifier_id=VERIFIER,
            verifier_key_id=VERIFIER_KEY_ID,
            audience=AUDIENCE,
            attestation_signer=verifier_backend,
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        with self.assertRaises(Exception):
            attestor.verify_and_attest(
                case["draft"].report_bytes + b" ",
                case["expected"],
                probe_evidence=case["evidence"],
                raw_observer_envelopes=case["envelopes"],
                envelope_manifest_bytes=case["draft"].envelope_manifest_bytes,
                registry=case["registry"],
                observer_signature_verifier=case["observer_verifier"],
                replay_receipt_reader=case["reader"],
            )
        self.assertEqual(verifier_backend.calls, [])


if __name__ == "__main__":
    unittest.main()
