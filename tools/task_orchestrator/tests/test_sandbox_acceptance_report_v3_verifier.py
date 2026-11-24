import base64
import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from test_sandbox_acceptance_report_v3 import (
    FakeObserverVerifier,
    make_case,
)
from tools.task_orchestrator.sandbox_acceptance_report_v3 import build_schema_v3_report_draft
from tools.task_orchestrator.sandbox_acceptance_report_v3_verifier import (
    AcceptanceReportV3Error,
    SchemaV3VerificationAttestor,
    verify_signed_acceptance_report_v3,
)


class SchemaV3IndependentVerifierTests(unittest.TestCase):
    def make_signed_case(self):
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
        signer = FakeObserverVerifier()
        signature = signer.sign(expected.acceptance.trusted_key_id, draft.report_bytes)
        return {
            "expected": expected,
            "registry": registry,
            "observer_verifier": observer_verifier,
            "reader": reader,
            "evidence": evidence,
            "envelopes": envelopes,
            "draft": draft,
            "signer": signer,
            "signature": signature,
        }

    def verify(self, case, **overrides):
        args = {
            "report_bytes": case["draft"].report_bytes,
            "signature": case["signature"],
            "expectation": case["expected"],
            "report_signature_verifier": case["signer"],
            "probe_evidence": case["evidence"],
            "raw_observer_envelopes": case["envelopes"],
            "envelope_manifest_bytes": case["draft"].envelope_manifest_bytes,
            "registry": case["registry"],
            "observer_signature_verifier": case["observer_verifier"],
            "replay_receipt_reader": case["reader"],
        }
        args.update(overrides)
        return verify_signed_acceptance_report_v3(**args)

    def test_valid_v3_report_and_exact_manifest_verify(self):
        case = self.make_signed_case()
        result = self.verify(case)
        self.assertEqual(result["schema_version"], 3)
        self.assertEqual(result["status"], "runtime_acceptance_evidence_verified_with_observer_provenance_and_retained_envelopes")
        self.assertEqual(result["probe_count"], 20)
        self.assertEqual(result["observer_count"], case["draft"].observer_count)
        self.assertEqual(result["report_sha256"], case["draft"].report_sha256)
        self.assertEqual(result["observer_envelope_manifest_sha256"], case["draft"].observer_envelope_manifest_sha256)
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["eligible_for_untrusted_execution"])
        self.assertFalse(result["patch_applied"])

    def test_invalid_acceptance_report_signature_is_rejected(self):
        case = self.make_signed_case()
        with self.assertRaisesRegex(AcceptanceReportV3Error, "signature is invalid"):
            self.verify(case, signature=b"X" * 64)

    def test_manifest_tampering_is_rejected_before_report_acceptance(self):
        case = self.make_signed_case()
        altered = case["draft"].envelope_manifest_bytes + b" "
        with self.assertRaisesRegex(AcceptanceReportV3Error, "manifest digest"):
            self.verify(case, envelope_manifest_bytes=altered)

    def test_report_tampering_is_rejected(self):
        case = self.make_signed_case()
        altered = case["draft"].report_bytes + b" "
        with self.assertRaises(ValueError):
            self.verify(case, report_bytes=altered)

    def test_missing_raw_envelope_is_rejected(self):
        case = self.make_signed_case()
        envelopes = dict(case["envelopes"])
        envelopes.pop(next(iter(envelopes)))
        with self.assertRaisesRegex(AcceptanceReportV3Error, "exactly match"):
            self.verify(case, raw_observer_envelopes=envelopes)

    def test_missing_replay_receipt_is_rejected(self):
        case = self.make_signed_case()
        case["reader"].receipts.clear()
        with self.assertRaisesRegex(AcceptanceReportV3Error, "receipt is missing"):
            self.verify(case)


if __name__ == "__main__":
    unittest.main()


class FakeVerifierAttestationSigner:
    def __init__(self):
        self.calls = []
    def sign(self, key_id, message):
        self.calls.append((key_id, message))
        return hashlib.sha512(key_id.encode() + b"\\x00" + message).digest()


class SchemaV3VerificationAttestorTests(SchemaV3IndependentVerifierTests):
    def setUp(self):
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
        self.case = {
            "expected": expected, "registry": registry,
            "observer_verifier": observer_verifier, "reader": reader,
            "evidence": evidence, "envelopes": envelopes, "draft": draft,
        }
        self.backend = FakeVerifierAttestationSigner()
        self.attestor = SchemaV3VerificationAttestor(
            verifier_id="independent-verifier-prod",
            verifier_key_id="verifier-attestation-key-01",
            audience="sandbox-acceptance-prod",
            attestation_signer=self.backend,
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
            lifetime_seconds=45,
        )

    def attest(self, **overrides):
        case = self.case
        args = {
            "report_bytes": case["draft"].report_bytes,
            "expectation": case["expected"],
            "probe_evidence": case["evidence"],
            "raw_observer_envelopes": case["envelopes"],
            "envelope_manifest_bytes": case["draft"].envelope_manifest_bytes,
            "registry": case["registry"],
            "observer_signature_verifier": case["observer_verifier"],
            "replay_receipt_reader": case["reader"],
        }
        args.update(overrides)
        return self.attestor.verify_and_attest(**args)

    def test_attestation_is_issued_only_after_full_independent_verification(self):
        result = self.attest()
        attestation = json.loads(result.attestation_bytes)
        self.assertTrue(result.verification_result["content_verified"])
        self.assertFalse(result.verification_result["report_signature_verified"])
        self.assertFalse(result.verification_result["signature_verified"])
        self.assertFalse(result.verification_result["execution_authorized"])
        self.assertFalse(result.verification_result["eligible_for_untrusted_execution"])
        self.assertEqual(attestation["verifier_id"], "independent-verifier-prod")
        self.assertEqual(attestation["verifier_key_id"], "verifier-attestation-key-01")
        self.assertEqual(attestation["audience"], "sandbox-acceptance-prod")
        self.assertEqual(attestation["report_sha256"], hashlib.sha256(self.case["draft"].report_bytes).hexdigest())
        self.assertEqual(attestation["envelope_manifest_sha256"], self.case["draft"].observer_envelope_manifest_sha256)
        self.assertEqual(attestation["verification_id"], result.verification_id)
        self.assertEqual(attestation["expires_at"], "2026-11-24T12:00:45Z")
        signature = base64.b64decode(attestation.pop("signature_b64"))
        message = json.dumps(attestation, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(signature, hashlib.sha512(b"verifier-attestation-key-01\\x00" + message).digest())
        self.assertEqual(len(self.backend.calls), 1)

    def test_invalid_report_or_manifest_never_reaches_attestation_signer(self):
        with self.assertRaises(ValueError):
            self.attest(report_bytes=self.case["draft"].report_bytes + b" ")
        with self.assertRaises(AcceptanceReportV3Error):
            self.attest(envelope_manifest_bytes=b"tampered")
        self.assertEqual(self.backend.calls, [])

    def test_attestation_key_cannot_equal_report_signing_key(self):
        case = self.case
        invalid = SchemaV3VerificationAttestor(
            verifier_id="independent-verifier-prod",
            verifier_key_id=case["expected"].acceptance.trusted_key_id,
            audience="sandbox-acceptance-prod",
            attestation_signer=self.backend,
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        original = self.attestor
        self.attestor = invalid
        with self.assertRaisesRegex(AcceptanceReportV3Error, "must be distinct"):
            self.attest()
        self.attestor = original
        self.assertEqual(self.backend.calls, [])

    def test_verifier_attestation_randomness_and_signer_fail_closed(self):
        with patch("tools.task_orchestrator.sandbox_acceptance_report_v3_verifier.secrets.token_hex", side_effect=OSError("entropy unavailable")):
            with self.assertRaisesRegex(AcceptanceReportV3Error, "CSPRNG"):
                self.attest()
        class FailingBackend:
            def sign(self, key_id, message):
                raise OSError("HSM unavailable")
        failing = SchemaV3VerificationAttestor(
            verifier_id="independent-verifier-prod",
            verifier_key_id="verifier-attestation-key-01",
            audience="sandbox-acceptance-prod",
            attestation_signer=FailingBackend(),
            trusted_clock=lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        original = self.attestor
        self.attestor = failing
        with self.assertRaisesRegex(AcceptanceReportV3Error, "signing failed"):
            self.attest()
        self.attestor = original


if __name__ == "__main__":
    unittest.main()
