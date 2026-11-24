import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_acceptance import AcceptanceExpectation, REQUIRED_PROBES
from tools.task_orchestrator.sandbox_acceptance_provenance import (
    AcceptanceProvenanceError,
    AcceptanceProvenanceExpectation,
    verify_signed_acceptance_report_v2,
)
from tools.task_orchestrator.sandbox_host_evidence import _required_domains


NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
REGISTRY_SHA = "d" * 64
REGISTRY_VERSION = 5
ACCEPTANCE_KEY = "acceptance-key-01"
ATTEMPT = "attempt-v2-001"
RUNTIME = "runtime-v2-001"
POLICY = "sha256:" + "a" * 64
IMAGE = "sha256:" + "b" * 64
PROVIDER = "fixture-provider"
REGION = "eu-test-1"
TASK = "fixture-task"


def canonical(value, *, ascii_only=False):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only, allow_nan=False
    ).encode("ascii" if ascii_only else "utf-8")


class FakeReportVerifier:
    def verify(self, key_id, message, signature):
        expected = hashlib.sha512(key_id.encode("ascii") + b"\x00" + message).digest()
        return signature == expected


def expectation(registry_sha=REGISTRY_SHA, registry_version=REGISTRY_VERSION):
    base = AcceptanceExpectation(
        provider_id=PROVIDER,
        region=REGION,
        task_id=TASK,
        attempt_id=ATTEMPT,
        image_digest=IMAGE,
        policy_digest=POLICY,
        trusted_key_id=ACCEPTANCE_KEY,
        now=NOW,
    )
    return AcceptanceProvenanceExpectation(
        acceptance=base,
        runtime_id=RUNTIME,
        observer_registry_sha256=registry_sha,
        observer_registry_version=registry_version,
    )


def build_case():
    required_domains = _required_domains()
    evidence = {}
    provenance = []
    sequence_by_observer = {}
    for probe_id in sorted(REQUIRED_PROBES):
        observations = []
        for domain in sorted(required_domains[probe_id]):
            observer_id = f"{domain}-observer-01"
            key_id = f"{domain}-key-01"
            sequence_by_observer[observer_id] = sequence_by_observer.get(observer_id, 0) + 1
            payload = f"payload:{probe_id}:{domain}".encode("ascii")
            payload_sha = hashlib.sha256(payload).hexdigest()
            observations.append({
                "observer_domain": domain,
                "observer_id": observer_id,
                "runtime_id": RUNTIME,
                "policy_digest": POLICY,
                "monotonic_start_ns": 100,
                "monotonic_end_ns": 200,
                "observed_at": "2026-11-24T11:59:45Z",
                "outcome": "pass",
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "payload_sha256": payload_sha,
            })
            provenance.append({
                "probe_id": probe_id,
                "observer_domain": domain,
                "observer_id": observer_id,
                "key_id": key_id,
                "observer_registry_sha256": REGISTRY_SHA,
                "observer_registry_version": REGISTRY_VERSION,
                "sequence": sequence_by_observer[observer_id],
                "nonce_sha256": hashlib.sha256(f"nonce:{probe_id}:{domain}".encode()).hexdigest(),
                "envelope_sha256": hashlib.sha256(f"envelope:{probe_id}:{domain}".encode()).hexdigest(),
                "payload_sha256": payload_sha,
                "signature_algorithm": "Ed25519",
            })
        evidence_doc = {
            "schema_version": 1,
            "suite_id": "jetvpn-sandbox-runtime-acceptance",
            "suite_version": "1.0.0",
            "attempt_id": ATTEMPT,
            "runtime_id": RUNTIME,
            "policy_digest": POLICY,
            "probe_id": probe_id,
            "observations": observations,
        }
        evidence[probe_id] = canonical(evidence_doc, ascii_only=True)

    report = {
        "schema_version": 2,
        "suite_id": "jetvpn-sandbox-runtime-acceptance",
        "suite_version": "1.0.0",
        "key_id": ACCEPTANCE_KEY,
        "provider_id": PROVIDER,
        "region": REGION,
        "runtime_id": RUNTIME,
        "task_id": TASK,
        "attempt_id": ATTEMPT,
        "image_digest": IMAGE,
        "policy_digest": POLICY,
        "started_at": "2026-11-24T11:55:00Z",
        "completed_at": "2026-11-24T11:59:50Z",
        "probes": [
            {
                "probe_id": probe_id,
                "outcome": "pass",
                "evidence_sha256": hashlib.sha256(evidence[probe_id]).hexdigest(),
            }
            for probe_id in sorted(REQUIRED_PROBES)
        ],
        "observer_registry_sha256": REGISTRY_SHA,
        "observer_registry_version": REGISTRY_VERSION,
        "observer_provenance_sha256": hashlib.sha256(canonical(provenance)).hexdigest(),
        "observer_provenance": provenance,
    }
    return report, evidence


def signed(report):
    raw = canonical(report)
    signature = hashlib.sha512(ACCEPTANCE_KEY.encode("ascii") + b"\x00" + raw).digest()
    return raw, signature


def refresh_provenance_digest(report):
    report["observer_provenance_sha256"] = hashlib.sha256(
        canonical(report["observer_provenance"])
    ).hexdigest()


class AcceptanceProvenanceV2Tests(unittest.TestCase):
    def verify(self, report, evidence, *, expected=None, signature_override=None):
        raw, signature = signed(report)
        if signature_override is not None:
            signature = signature_override
        return verify_signed_acceptance_report_v2(
            raw,
            signature,
            expected or expectation(),
            FakeReportVerifier(),
            probe_evidence=evidence,
        )

    def test_valid_v2_report_verifies_and_keeps_execution_disabled(self):
        report, evidence = build_case()
        result = self.verify(report, evidence)
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["status"], "runtime_acceptance_evidence_verified_with_observer_provenance")
        self.assertEqual(result["probe_count"], len(REQUIRED_PROBES))
        self.assertEqual(result["observer_registry_sha256"], REGISTRY_SHA)
        self.assertEqual(result["observer_registry_version"], REGISTRY_VERSION)
        self.assertEqual(result["observer_provenance_count"], len(report["observer_provenance"]))
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["eligible_for_untrusted_execution"])
        self.assertFalse(result["patch_applied"])

    def test_report_signature_is_verified_over_provenance_and_evidence_bindings(self):
        report, evidence = build_case()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "signature is invalid"):
            self.verify(report, evidence, signature_override=b"X" * 64)

    def test_runtime_id_must_match_protected_expectation(self):
        report, evidence = build_case()
        base = AcceptanceExpectation(
            provider_id=PROVIDER, region=REGION, task_id=TASK, attempt_id=ATTEMPT,
            image_digest=IMAGE, policy_digest=POLICY, trusted_key_id=ACCEPTANCE_KEY, now=NOW,
        )
        wrong_runtime = AcceptanceProvenanceExpectation(
            acceptance=base, runtime_id="different-runtime",
            observer_registry_sha256=REGISTRY_SHA, observer_registry_version=REGISTRY_VERSION,
        )
        with self.assertRaisesRegex(AcceptanceProvenanceError, "runtime_id does not match"):
            self.verify(report, evidence, expected=wrong_runtime)

    def test_registry_digest_and_version_must_match_protected_expectation(self):
        report, evidence = build_case()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "digest does not match"):
            self.verify(report, evidence, expected=expectation(registry_sha="e" * 64))
        with self.assertRaisesRegex(AcceptanceProvenanceError, "version does not match"):
            self.verify(report, evidence, expected=expectation(registry_version=6))

    def test_provenance_digest_is_recomputed(self):
        report, evidence = build_case()
        report["observer_provenance"][0]["key_id"] = "different-key"
        with self.assertRaisesRegex(AcceptanceProvenanceError, "provenance digest"):
            self.verify(report, evidence)

    def test_provenance_must_be_complete_and_sorted(self):
        report, evidence = build_case()
        report["observer_provenance"].pop()
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "exactly match raw evidence"):
            self.verify(report, evidence)

        report, evidence = build_case()
        report["observer_provenance"][0], report["observer_provenance"][1] = (
            report["observer_provenance"][1], report["observer_provenance"][0]
        )
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "uniquely sorted"):
            self.verify(report, evidence)

    def test_replayed_nonce_envelope_and_observer_sequence_are_rejected(self):
        report, evidence = build_case()
        report["observer_provenance"][1]["nonce_sha256"] = report["observer_provenance"][0]["nonce_sha256"]
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "replayed nonce"):
            self.verify(report, evidence)

        report, evidence = build_case()
        report["observer_provenance"][1]["envelope_sha256"] = report["observer_provenance"][0]["envelope_sha256"]
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "replayed nonce"):
            self.verify(report, evidence)

        report, evidence = build_case()
        first = report["observer_provenance"][0]
        other = next(
            item for item in report["observer_provenance"]
            if item["observer_id"] == first["observer_id"] and item is not first
        )
        other["sequence"] = first["sequence"]
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "replayed nonce"):
            self.verify(report, evidence)

    def test_provenance_must_match_exact_evidence_observer_and_payload(self):
        report, evidence = build_case()
        report["observer_provenance"][0]["observer_id"] = "forged-observer"
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "does not match raw evidence"):
            self.verify(report, evidence)

        report, evidence = build_case()
        report["observer_provenance"][0]["payload_sha256"] = "f" * 64
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "does not match raw evidence"):
            self.verify(report, evidence)

    def test_wrong_domain_key_or_algorithm_is_rejected(self):
        report, evidence = build_case()
        report["observer_provenance"][0]["observer_domain"] = "provider_api"
        refresh_provenance_digest(report)
        with self.assertRaises(AcceptanceProvenanceError):
            self.verify(report, evidence)

        report, evidence = build_case()
        report["observer_provenance"][0]["signature_algorithm"] = "RSA"
        refresh_provenance_digest(report)
        with self.assertRaisesRegex(AcceptanceProvenanceError, "Only Ed25519"):
            self.verify(report, evidence)

    def test_raw_evidence_digest_and_payload_digest_are_recomputed(self):
        report, evidence = build_case()
        evidence[sorted(REQUIRED_PROBES)[0]] += b"tamper"
        with self.assertRaisesRegex(AcceptanceProvenanceError, "digest does not match the signed report"):
            self.verify(report, evidence)

        report, evidence = build_case()
        probe_id = sorted(REQUIRED_PROBES)[0]
        doc = json.loads(evidence[probe_id])
        payload = b"modified-payload"
        doc["observations"][0]["payload_b64"] = base64.b64encode(payload).decode("ascii")
        evidence[probe_id] = canonical(doc, ascii_only=True)
        probe = next(item for item in report["probes"] if item["probe_id"] == probe_id)
        probe["evidence_sha256"] = hashlib.sha256(evidence[probe_id]).hexdigest()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "payload digest mismatch"):
            self.verify(report, evidence)

    def test_observation_time_and_monotonic_bounds_are_checked(self):
        report, evidence = build_case()
        probe_id = sorted(REQUIRED_PROBES)[0]
        doc = json.loads(evidence[probe_id])
        doc["observations"][0]["observed_at"] = "2026-11-24T10:00:00Z"
        evidence[probe_id] = canonical(doc, ascii_only=True)
        next(item for item in report["probes"] if item["probe_id"] == probe_id)["evidence_sha256"] = hashlib.sha256(evidence[probe_id]).hexdigest()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "stale"):
            self.verify(report, evidence)

        report, evidence = build_case()
        probe_id = sorted(REQUIRED_PROBES)[0]
        doc = json.loads(evidence[probe_id])
        doc["observations"][0]["monotonic_start_ns"] = 201
        doc["observations"][0]["monotonic_end_ns"] = 200
        evidence[probe_id] = canonical(doc, ascii_only=True)
        next(item for item in report["probes"] if item["probe_id"] == probe_id)["evidence_sha256"] = hashlib.sha256(evidence[probe_id]).hexdigest()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "interval is reversed"):
            self.verify(report, evidence)

    def test_evidence_inventory_probe_order_and_report_schema_are_strict(self):
        report, evidence = build_case()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "exactly match"):
            self.verify(report, {key: value for key, value in evidence.items() if key != sorted(REQUIRED_PROBES)[0]})

        report, evidence = build_case()
        report["probes"][0], report["probes"][1] = report["probes"][1], report["probes"][0]
        with self.assertRaisesRegex(AcceptanceProvenanceError, "sorted by probe"):
            self.verify(report, evidence)

        report, evidence = build_case()
        report["schema_version"] = 1
        with self.assertRaisesRegex(AcceptanceProvenanceError, "schema version 2"):
            self.verify(report, evidence)

    def test_evidence_context_and_canonical_encoding_are_strict(self):
        report, evidence = build_case()
        probe_id = sorted(REQUIRED_PROBES)[0]
        doc = json.loads(evidence[probe_id])
        doc["runtime_id"] = "different-runtime"
        evidence[probe_id] = canonical(doc, ascii_only=True)
        next(item for item in report["probes"] if item["probe_id"] == probe_id)["evidence_sha256"] = hashlib.sha256(evidence[probe_id]).hexdigest()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "context does not match"):
            self.verify(report, evidence)

        report, evidence = build_case()
        probe_id = sorted(REQUIRED_PROBES)[0]
        evidence[probe_id] = json.dumps(json.loads(evidence[probe_id]), indent=2).encode("ascii")
        next(item for item in report["probes"] if item["probe_id"] == probe_id)["evidence_sha256"] = hashlib.sha256(evidence[probe_id]).hexdigest()
        with self.assertRaisesRegex(AcceptanceProvenanceError, "canonical signed form"):
            self.verify(report, evidence)

    def test_duplicate_json_keys_and_invalid_expectation_fail_closed(self):
        report, evidence = build_case()
        raw = b'{"schema_version":2,"schema_version":2}'
        with self.assertRaisesRegex(AcceptanceProvenanceError, "duplicate JSON keys"):
            verify_signed_acceptance_report_v2(
                raw, b"x", expectation(), FakeReportVerifier(), probe_evidence=evidence
            )
        with self.assertRaises(AcceptanceProvenanceError):
            self.verify(report, evidence, expected=expectation(registry_sha="not-a-digest"))


if __name__ == "__main__":
    unittest.main()
