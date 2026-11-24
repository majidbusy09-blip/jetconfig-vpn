import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.task_orchestrator.sandbox_host_evidence import (
    HostEvidenceCollector,
    HostEvidenceError,
    ProbeObservation,
)
from tools.task_orchestrator.sandbox_acceptance import REQUIRED_PROBES


MANIFEST = json.loads(
    (Path(__file__).resolve().parents[1] / "runtime_probe_manifest.json").read_text(encoding="utf-8")
)
OWNER_DOMAINS = {
    "host_controller": ("host_controller",),
    "guest_plus_host": ("guest", "host_controller"),
    "host_controller_plus_guest": ("host_controller", "guest"),
    "external_canary_plus_host": ("external_canary", "host_controller"),
    "external_canary": ("external_canary",),
}
NOW = datetime(2026, 11, 24, 11, 0, 0, tzinfo=timezone.utc)
ATTEMPT = "attempt-fixture-001"
RUNTIME = "vm-fixture-001"
POLICY = "sha256:" + "a" * 64
TRUSTED = {
    "host_controller": frozenset({"host-ci-fixture-1"}),
    "guest": frozenset({"guest-fixture-1"}),
    "external_canary": frozenset({"canary-fixture-1"}),
}


def make_observations(*, outcome="pass", observed_at="2026-11-24T10:59:30Z"):
    records = []
    for probe in MANIFEST["probes"]:
        for domain in OWNER_DOMAINS[probe["evidence_owner"]]:
            observer_id = {
                "host_controller": "host-ci-fixture-1",
                "guest": "guest-fixture-1",
                "external_canary": "canary-fixture-1",
            }[domain]
            records.append(
                ProbeObservation(
                    probe_id=probe["probe_id"],
                    observer_domain=domain,
                    observer_id=observer_id,
                    attempt_id=ATTEMPT,
                    runtime_id=RUNTIME,
                    policy_digest=POLICY,
                    monotonic_start_ns=1_000_000,
                    monotonic_end_ns=2_000_000,
                    observed_at=observed_at,
                    outcome=outcome,
                    payload=("fixture:" + probe["probe_id"] + ":" + domain).encode("ascii"),
                )
            )
    return records


class HostEvidenceCollectorTests(unittest.TestCase):
    def setUp(self):
        self.collector = HostEvidenceCollector(trusted_observers=TRUSTED, runtime_id=RUNTIME, policy_digest=POLICY, now=NOW)

    def test_complete_independently_observed_bundle_is_bounded_and_never_authorizes(self):
        result = self.collector.collect(attempt_id=ATTEMPT, observations=make_observations())
        self.assertEqual(result.status, "all_observers_reported_pass")
        self.assertEqual(set(result.probe_evidence), REQUIRED_PROBES)
        self.assertEqual(set(result.probe_outcomes), REQUIRED_PROBES)
        self.assertEqual(set(result.probe_digests), REQUIRED_PROBES)
        self.assertTrue(all(value == "pass" for value in result.probe_outcomes.values()))
        self.assertTrue(all(len(value) <= 128 * 1024 for value in result.probe_evidence.values()))
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.eligible_for_untrusted_execution)

    def test_failed_observer_is_preserved_as_failure_not_promoted_to_pass(self):
        records = make_observations()
        records[0] = ProbeObservation(**{
            **records[0].__dict__,
            "outcome": "fail",
        })
        result = self.collector.collect(attempt_id=ATTEMPT, observations=records)
        self.assertEqual(result.status, "one_or_more_probes_failed")
        self.assertIn("fail", result.probe_outcomes.values())
        self.assertFalse(result.execution_authorized)

    def test_missing_required_independent_observer_fails_closed(self):
        records = make_observations()
        records = [item for item in records if not (
            item.probe_id == "guest_non_root_no_capabilities" and item.observer_domain == "host_controller"
        )]
        with self.assertRaisesRegex(HostEvidenceError, "lacks required independent observers"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_guest_self_report_cannot_replace_host_evidence(self):
        records = [
            item for item in make_observations()
            if item.probe_id != "runtime_vm_boundary"
        ]
        records.append(ProbeObservation(
            probe_id="runtime_vm_boundary",
            observer_domain="guest",
            observer_id="guest-fixture-1",
            attempt_id=ATTEMPT,
            runtime_id=RUNTIME,
            policy_digest=POLICY,
            monotonic_start_ns=1_000_000,
            monotonic_end_ns=2_000_000,
            observed_at="2026-11-24T10:59:30Z",
            outcome="pass",
            payload=b"guest claims host boundary is safe",
        ))
        with self.assertRaises(HostEvidenceError):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_untrusted_observer_identity_is_rejected(self):
        records = make_observations()
        records[0] = ProbeObservation(**{
            **records[0].__dict__,
            "observer_id": "attacker-controlled",
        })
        with self.assertRaisesRegex(HostEvidenceError, "not in the out-of-band trust configuration"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_wrong_attempt_and_unknown_probe_are_rejected(self):
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "attempt_id": "other-attempt"})
        with self.assertRaisesRegex(HostEvidenceError, "different attempt"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "probe_id": "arbitrary-command"})
        with self.assertRaises(HostEvidenceError):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_runtime_and_policy_binding_and_monotonic_offsets_are_enforced(self):
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "runtime_id": "other-runtime"})
        with self.assertRaisesRegex(HostEvidenceError, "different runtime"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "policy_digest": "sha256:" + "b" * 64})
        with self.assertRaisesRegex(HostEvidenceError, "policy digest"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "monotonic_end_ns": 0})
        with self.assertRaisesRegex(HostEvidenceError, "precedes its start"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_duplicate_observer_domain_is_rejected(self):
        records = make_observations()
        records.append(records[0])
        with self.assertRaisesRegex(HostEvidenceError, "Duplicate observation"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_stale_future_and_malformed_timestamps_are_rejected(self):
        for timestamp in ("2026-11-24T10:00:00Z", "2026-11-24T11:01:00Z", "not-a-time"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(HostEvidenceError):
                    self.collector.collect(
                        attempt_id=ATTEMPT,
                        observations=make_observations(observed_at=timestamp),
                    )

    def test_oversized_or_empty_payload_is_rejected(self):
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "payload": b"x" * (48 * 1024 + 1)})
        with self.assertRaisesRegex(HostEvidenceError, "size limit"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "payload": b""})
        with self.assertRaisesRegex(HostEvidenceError, "missing or invalid"):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)

    def test_unconfigured_or_empty_trust_domains_are_rejected(self):
        with self.assertRaises(HostEvidenceError):
            HostEvidenceCollector(trusted_observers={"host_controller": frozenset()}, runtime_id=RUNTIME, policy_digest=POLICY, now=NOW)
        with self.assertRaises(HostEvidenceError):
            HostEvidenceCollector(trusted_observers={"host_controller": frozenset({"host"})}, runtime_id=RUNTIME, policy_digest=POLICY, now=NOW)

    def test_non_pass_or_malformed_contract_fields_are_rejected(self):
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "outcome": "maybe"})
        with self.assertRaises(HostEvidenceError):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)
        records = make_observations()
        records[0] = ProbeObservation(**{**records[0].__dict__, "observer_domain": "provider_api"})
        with self.assertRaises(HostEvidenceError):
            self.collector.collect(attempt_id=ATTEMPT, observations=records)


if __name__ == "__main__":
    unittest.main()
