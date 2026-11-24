import base64
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from test_sandbox_acceptance_report_v3 import FakeObserverVerifier, make_case
from tools.task_orchestrator.sandbox_acceptance_pipeline_v3 import (
    AcceptancePipelineError,
    assemble_schema_v3_acceptance,
)
from tools.task_orchestrator.sandbox_observer_auth import ObserverChallenge, ObserverReplayReceipt

NOW = datetime(2026, 11, 24, 11, 59, 50, tzinfo=timezone.utc)


class FixtureReplayStore:
    def __init__(self, reader):
        self.reader = reader
        self.nonces = set()
        self.sequences = {}

    def consume(self, **record):
        nonce = record["nonce_sha256"]
        observer = record["observer_id"]
        if nonce in self.nonces or record["sequence"] <= self.sequences.get(observer, 0):
            return None
        receipt = self.reader.get_acceptance(
            observer_id=observer, envelope_sha256=record["envelope_sha256"]
        )
        if type(receipt) is not ObserverReplayReceipt:
            return None
        expected = {key: value for key, value in record.items()}
        if any(getattr(receipt, key) != value for key, value in expected.items()):
            return None
        self.nonces.add(nonce)
        self.sequences[observer] = record["sequence"]
        return receipt

    def get_acceptance(self, *, observer_id, envelope_sha256):
        return self.reader.get_acceptance(observer_id=observer_id, envelope_sha256=envelope_sha256)


def make_challenges(envelopes):
    challenges = {}
    for pair, raw in envelopes.items():
        envelope = json.loads(raw)
        challenges[pair] = ObserverChallenge(
            nonce=base64.b64decode(envelope["nonce_b64"]),
            audience=envelope["audience"],
            observer_id=envelope["observer_id"],
            observer_domain=envelope["observer_domain"],
            attempt_id=envelope["attempt_id"],
            runtime_id=envelope["runtime_id"],
            policy_digest=envelope["policy_digest"],
            probe_id=envelope["probe_id"],
            issued_at=datetime(2026, 11, 24, 11, 59, 30, tzinfo=timezone.utc),
            expires_at=datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
    return challenges


class SchemaV3AcceptancePipelineTests(unittest.TestCase):
    def assemble(self, case=None, **overrides):
        case = case or make_case()
        expected, registry, signature_verifier, reader, _, _, envelopes = case
        args = {
            "started_at": "2026-11-24T11:55:00Z",
            "completed_at": "2026-11-24T11:59:55Z",
            "raw_observer_envelopes": envelopes,
            "challenges": make_challenges(envelopes),
            "registry": registry,
            "observer_signature_verifier": signature_verifier,
            "replay_store": FixtureReplayStore(reader),
            "replay_receipt_reader": reader,
            "trusted_observers": {
                domain: frozenset({f"{domain}-observer-01"})
                for domain in ("host_controller", "guest", "external_canary")
            },
            "now": NOW,
        }
        args.update(overrides)
        return assemble_schema_v3_acceptance(expected, **args)

    def test_integrates_envelope_auth_evidence_collection_and_report_draft(self):
        result = self.assemble()
        self.assertEqual(result.authenticated_observer_count, result.report_draft.observer_count)
        self.assertEqual(result.report_draft.probe_count, 20)
        self.assertEqual(len(result.evidence.probe_evidence), 20)
        self.assertEqual(result.report_draft.report_sha256, hashlib.sha256(result.report_draft.report_bytes).hexdigest())
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.eligible_for_untrusted_execution)
        self.assertFalse(result.patch_applied)

    def test_missing_envelope_or_challenge_is_rejected_before_collection(self):
        case = make_case()
        expected, registry, verifier, reader, _, _, envelopes = case
        challenges = make_challenges(envelopes)
        missing = dict(envelopes)
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(AcceptancePipelineError, "exactly cover"):
            self.assemble(case, raw_observer_envelopes=missing)
        challenges.pop(next(iter(challenges)))
        with self.assertRaisesRegex(AcceptancePipelineError, "separately issued"):
            self.assemble(case, challenges=challenges)

    def test_invalid_envelope_fails_before_evidence_or_report(self):
        case = make_case()
        _, _, _, _, _, _, envelopes = case
        altered = dict(envelopes)
        pair = next(iter(altered))
        altered[pair] = altered[pair] + b" "
        with self.assertRaisesRegex(AcceptancePipelineError, "failed authentication"):
            self.assemble(case, raw_observer_envelopes=altered)

    def test_wrong_observer_trust_configuration_fails_closed(self):
        with self.assertRaisesRegex(AcceptancePipelineError, "collection failed"):
            self.assemble(trusted_observers={
                "host_controller": frozenset({"wrong-host"}),
                "guest": frozenset({"guest-observer-01"}),
                "external_canary": frozenset({"external_canary-observer-01"}),
            })


if __name__ == "__main__":
    unittest.main()
