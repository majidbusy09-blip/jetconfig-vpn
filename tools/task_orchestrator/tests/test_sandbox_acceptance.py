import hashlib
import unittest
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_acceptance import (
    AcceptanceExpectation,
    REQUIRED_PROBES,
    SUITE_ID,
    SUITE_VERSION,
    SandboxEvidenceError,
    canonical_report_bytes,
    verify_signed_acceptance_report,
)

IMAGE = "sha256:" + "1" * 64
POLICY = "sha256:" + "2" * 64
NOW = datetime(2026, 11, 24, 7, 0, 0, tzinfo=timezone.utc)


class FakeTrustedVerifier:
    """Test double only; never use as a production trust anchor."""

    def verify(self, key_id, message, signature):
        return key_id == "trusted-acceptance-key-1" and signature == hashlib.sha256(message).digest()


def expectation(**changes):
    values = {
        "provider_id": "candidate-vm-provider",
        "region": "eu-central",
        "task_id": "task-123",
        "attempt_id": "attempt-456",
        "image_digest": IMAGE,
        "policy_digest": POLICY,
        "trusted_key_id": "trusted-acceptance-key-1",
        "now": NOW,
    }
    values.update(changes)
    return AcceptanceExpectation(**values)


def valid_report(**changes):
    report = {
        "schema_version": 1,
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "key_id": "trusted-acceptance-key-1",
        "provider_id": "candidate-vm-provider",
        "region": "eu-central",
        "runtime_id": "vm-instance-789",
        "task_id": "task-123",
        "attempt_id": "attempt-456",
        "image_digest": IMAGE,
        "policy_digest": POLICY,
        "started_at": "2026-11-24T06:50:00Z",
        "completed_at": "2026-11-24T06:55:00Z",
        "probes": [
            {
                "probe_id": probe_id,
                "outcome": "pass",
                "evidence_sha256": hashlib.sha256(b"JETVPN-PROBE-EVIDENCE:" + probe_id.encode()).hexdigest(),
            }
            for probe_id in sorted(REQUIRED_PROBES)
        ],
    }
    report.update(changes)
    return report


def evidence_for(report):
    return {
        probe["probe_id"]: b"JETVPN-PROBE-EVIDENCE:" + probe["probe_id"].encode()
        for probe in report["probes"]
    }


def signed(report):
    raw = canonical_report_bytes(report)
    return raw, hashlib.sha256(raw).digest()


class SandboxAcceptanceEvidenceTests(unittest.TestCase):
    def verify(self, report=None, signature=None, expected=None, verifier=None, raw=None, probe_evidence=None):
        source_report = valid_report() if report is None else report
        if raw is None:
            raw, generated_signature = signed(source_report)
            signature = generated_signature if signature is None else signature
        return verify_signed_acceptance_report(
            raw,
            signature,
            expectation() if expected is None else expected,
            FakeTrustedVerifier() if verifier is None else verifier,
            probe_evidence=evidence_for(source_report) if probe_evidence is None else probe_evidence,
        )

    def test_complete_fresh_signed_report_passes_but_never_authorizes_execution(self):
        result = self.verify()
        self.assertEqual(result["status"], "runtime_acceptance_evidence_verified")
        self.assertEqual(result["probe_count"], len(REQUIRED_PROBES))
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["eligible_for_untrusted_execution"])
        self.assertFalse(result["patch_applied"])

    def test_rejects_missing_probe(self):
        report = valid_report()
        report["probes"] = report["probes"][:-1]
        with self.assertRaises(SandboxEvidenceError):
            self.verify(report)

    def test_rejects_duplicate_probe(self):
        report = valid_report()
        report["probes"][-1] = dict(report["probes"][0])
        with self.assertRaises(SandboxEvidenceError):
            self.verify(report)

    def test_rejects_failed_or_unknown_probe(self):
        for mutation in (
            lambda p: p["probes"][0].update(outcome="fail"),
            lambda p: p["probes"][0].update(probe_id="arbitrary-command"),
        ):
            report = valid_report()
            mutation(report)
            with self.subTest(mutation=mutation):
                with self.assertRaises(SandboxEvidenceError):
                    self.verify(report)

    def test_rejects_wrong_provider_region_task_attempt_or_digests(self):
        for field, value in (
            ("provider_id", "other-provider"),
            ("region", "other-region"),
            ("task_id", "other-task"),
            ("attempt_id", "other-attempt"),
            ("image_digest", "sha256:" + "3" * 64),
            ("policy_digest", "sha256:" + "4" * 64),
        ):
            report = valid_report()
            report[field] = value
            with self.subTest(field=field):
                with self.assertRaises(SandboxEvidenceError):
                    self.verify(report)

    def test_rejects_stale_future_and_overlong_reports(self):
        cases = (
            ("2026-11-24T06:00:00Z", "2026-11-24T06:10:00Z"),
            ("2026-11-24T07:01:00Z", "2026-11-24T07:02:00Z"),
            ("2026-11-24T06:00:00Z", "2026-11-24T06:40:00Z"),
        )
        for started, completed in cases:
            report = valid_report(started_at=started, completed_at=completed)
            with self.subTest(started=started, completed=completed):
                with self.assertRaises(SandboxEvidenceError):
                    self.verify(report)

    def test_recomputes_each_digest_from_raw_probe_evidence(self):
        report = valid_report()
        evidence = evidence_for(report)
        first_probe = report["probes"][0]["probe_id"]
        evidence[first_probe] = b"tampered evidence"
        with self.assertRaisesRegex(SandboxEvidenceError, "digest does not match"):
            self.verify(report, probe_evidence=evidence)

    def test_rejects_missing_extra_empty_and_oversized_raw_evidence(self):
        report = valid_report()
        evidence = evidence_for(report)
        evidence.pop(next(iter(evidence)))
        with self.assertRaisesRegex(SandboxEvidenceError, "inventory"):
            self.verify(report, probe_evidence=evidence)

        evidence = evidence_for(report)
        evidence["unexpected-probe"] = b"unexpected"
        with self.assertRaisesRegex(SandboxEvidenceError, "inventory"):
            self.verify(report, probe_evidence=evidence)

        evidence = evidence_for(report)
        first_probe = report["probes"][0]["probe_id"]
        evidence[first_probe] = b""
        with self.assertRaisesRegex(SandboxEvidenceError, "missing or invalid"):
            self.verify(report, probe_evidence=evidence)

        evidence = evidence_for(report)
        evidence[first_probe] = b"x" * (128 * 1024 + 1)
        with self.assertRaisesRegex(SandboxEvidenceError, "per-probe size"):
            self.verify(report, probe_evidence=evidence)

    def test_rejects_aggregate_raw_evidence_overflow(self):
        report = valid_report()
        evidence = evidence_for(report)
        # Each blob is within its individual cap, but the combined bundle is not.
        for probe in report["probes"]:
            evidence[probe["probe_id"]] = b"x" * (110 * 1024)
            probe["evidence_sha256"] = hashlib.sha256(evidence[probe["probe_id"]]).hexdigest()
        with self.assertRaisesRegex(SandboxEvidenceError, "aggregate size"):
            self.verify(report, probe_evidence=evidence)

    def test_rejects_bad_signature_and_untrusted_key(self):
        raw, signature = signed(valid_report())
        with self.assertRaises(SandboxEvidenceError):
            self.verify(raw=raw, signature=b"not-a-signature")
        report = valid_report(key_id="attacker-key")
        with self.assertRaises(SandboxEvidenceError):
            self.verify(report)

    def test_rejects_noncanonical_json_and_duplicate_json_keys(self):
        raw, signature = signed(valid_report())
        with self.assertRaises(SandboxEvidenceError):
            self.verify(raw=raw + b" ", signature=signature)
        with self.assertRaises(SandboxEvidenceError):
            self.verify(raw=b'{"schema_version":1,"schema_version":1}', signature=signature)

    def test_rejects_unknown_schema_fields_and_wrong_suite_version(self):
        report = valid_report(extra="not-allowed")
        with self.assertRaises(SandboxEvidenceError):
            self.verify(report)
        report = valid_report(suite_version="2.0.0")
        with self.assertRaises(SandboxEvidenceError):
            self.verify(report)

    def test_rejects_oversized_report_and_signature(self):
        with self.assertRaises(SandboxEvidenceError):
            self.verify(raw=b"x" * (256 * 1024 + 1), signature=b"x")
        raw, signature = signed(valid_report())
        with self.assertRaises(SandboxEvidenceError):
            self.verify(raw=raw, signature=b"x" * 1025)

    def test_signature_verifier_exception_fails_closed(self):
        class BrokenVerifier:
            def verify(self, key_id, message, signature):
                raise RuntimeError("sensitive verifier detail")

        with self.assertRaisesRegex(SandboxEvidenceError, "failed closed"):
            self.verify(verifier=BrokenVerifier())

    def test_rejects_untrusted_clock_and_invalid_expectations(self):
        with self.assertRaises(SandboxEvidenceError):
            self.verify(expected=expectation(now=datetime(2026, 11, 24, 7, 0)))
        with self.assertRaises(SandboxEvidenceError):
            self.verify(expected=expectation(max_age_seconds=True))


if __name__ == "__main__":
    unittest.main()
