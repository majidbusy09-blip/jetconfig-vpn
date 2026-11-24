import unittest

from test_sandbox_acceptance_report_v3 import (
    FakeObserverVerifier,
    make_case,
)
from tools.task_orchestrator.sandbox_acceptance_report_v3 import build_schema_v3_report_draft
from tools.task_orchestrator.sandbox_acceptance_report_v3_verifier import (
    AcceptanceReportV3Error,
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
