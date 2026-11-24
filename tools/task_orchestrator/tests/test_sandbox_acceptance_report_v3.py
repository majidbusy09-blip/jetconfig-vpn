import base64
import hashlib
import json
import unittest
from datetime import datetime, timezone

from tools.task_orchestrator.sandbox_acceptance import AcceptanceExpectation, REQUIRED_PROBES
from tools.task_orchestrator.sandbox_acceptance_provenance import AcceptanceProvenanceExpectation
from tools.task_orchestrator.sandbox_acceptance_report_v3 import (
    AcceptanceReportV3Error,
    build_schema_v3_report_draft,
)
from tools.task_orchestrator.sandbox_host_evidence import ProbeObservation, _required_domains
from tools.task_orchestrator.sandbox_observer_auth import (
    AuthenticatedObserverResult,
    ObserverReplayReceipt,
    PinnedObserverRegistry,
)

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
ATTEMPT = "attempt-v3-001"
RUNTIME = "runtime-v3-001"
POLICY = "sha256:" + "a" * 64
IMAGE = "sha256:" + "b" * 64
REGISTRY_VERSION = 5
AUDIENCE = "jetvpn-host-acceptance"


def canonical(value, *, ascii_only=False):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=ascii_only, allow_nan=False,
    ).encode("ascii" if ascii_only else "utf-8")


class FakeObserverVerifier:
    def sign(self, key_id, message):
        return hashlib.sha512(key_id.encode("ascii") + b"\x00" + message).digest()

    def verify(self, key_id, message, signature):
        return signature == self.sign(key_id, message)


class MemoryReceiptReader:
    def __init__(self):
        self.receipts = {}

    def get_acceptance(self, *, observer_id, envelope_sha256):
        return self.receipts.get((observer_id, envelope_sha256))


def make_case():
    required_domains = _required_domains()
    identities = []
    for domain in sorted({d for ds in required_domains.values() for d in ds}):
        identities.append({
            "observer_id": f"{domain}-observer-01",
            "observer_domain": domain,
            "key_id": f"{domain}-key-01",
            "status": "active",
            "not_before": "2026-11-24T10:00:00Z",
            "not_after": "2026-11-24T13:00:00Z",
        })
    registry_raw = canonical({
        "schema_version": 1,
        "version": REGISTRY_VERSION,
        "audience": AUDIENCE,
        "identities": identities,
    })
    registry_sha = hashlib.sha256(registry_raw).hexdigest()
    registry = PinnedObserverRegistry(
        registry_raw,
        expected_sha256=registry_sha,
        minimum_version=REGISTRY_VERSION,
        expected_audience=AUDIENCE,
        now=NOW,
    )
    signature_verifier = FakeObserverVerifier()
    reader = MemoryReceiptReader()
    evidence = {}
    results = {}
    envelopes = {}
    sequences = {}

    for probe_id in sorted(REQUIRED_PROBES):
        evidence_observations = []
        for domain in sorted(required_domains[probe_id]):
            pair = (probe_id, domain)
            observer_id = f"{domain}-observer-01"
            key_id = f"{domain}-key-01"
            sequences[observer_id] = sequences.get(observer_id, 0) + 1
            sequence = sequences[observer_id]
            nonce = hashlib.sha256(f"nonce:{probe_id}:{domain}".encode()).digest()
            payload = f"payload:{probe_id}:{domain}".encode()
            payload_sha = hashlib.sha256(payload).hexdigest()
            observed_at = "2026-11-24T11:59:45Z"
            start_ns, end_ns = 100, 200
            unsigned = {
                "schema_version": 1,
                "audience": AUDIENCE,
                "observer_id": observer_id,
                "observer_domain": domain,
                "key_id": key_id,
                "attempt_id": ATTEMPT,
                "runtime_id": RUNTIME,
                "policy_digest": POLICY,
                "probe_id": probe_id,
                "nonce_b64": base64.b64encode(nonce).decode("ascii"),
                "sequence": sequence,
                "observed_at": observed_at,
                "monotonic_start_ns": start_ns,
                "monotonic_end_ns": end_ns,
                "outcome": "pass",
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "payload_sha256": payload_sha,
            }
            signature = signature_verifier.sign(key_id, canonical(unsigned))
            envelope = dict(unsigned)
            envelope["signature_b64"] = base64.b64encode(signature).decode("ascii")
            raw_envelope = canonical(envelope)
            envelope_sha = hashlib.sha256(raw_envelope).hexdigest()
            nonce_sha = hashlib.sha256(nonce).hexdigest()
            accepted_at = "2026-11-24T11:59:50.000000Z"
            expires_at = "2026-11-24T12:00:00Z"
            receipt = ObserverReplayReceipt(
                observer_id=observer_id,
                observer_domain=domain,
                attempt_id=ATTEMPT,
                runtime_id=RUNTIME,
                policy_digest=POLICY,
                probe_id=probe_id,
                observer_registry_sha256=registry_sha,
                observer_registry_version=REGISTRY_VERSION,
                key_id=key_id,
                nonce_sha256=nonce_sha,
                sequence=sequence,
                envelope_sha256=envelope_sha,
                challenge_expires_at=expires_at,
                accepted_at=accepted_at,
                ledger_revision=sequence,
                fencing_epoch=1,
            )
            reader.receipts[(observer_id, envelope_sha)] = receipt
            observation = ProbeObservation(
                probe_id=probe_id,
                observer_domain=domain,
                observer_id=observer_id,
                attempt_id=ATTEMPT,
                runtime_id=RUNTIME,
                policy_digest=POLICY,
                monotonic_start_ns=start_ns,
                monotonic_end_ns=end_ns,
                observed_at=observed_at,
                outcome="pass",
                payload=payload,
            )
            results[pair] = AuthenticatedObserverResult(
                observation=observation,
                observer_registry_sha256=registry_sha,
                observer_registry_version=REGISTRY_VERSION,
                key_id=key_id,
                sequence=sequence,
                nonce_sha256=nonce_sha,
                envelope_sha256=envelope_sha,
                challenge_expires_at=expires_at,
                accepted_at=accepted_at,
                ledger_revision=sequence,
                fencing_epoch=1,
            )
            envelopes[pair] = raw_envelope
            evidence_observations.append({
                "observer_domain": domain,
                "observer_id": observer_id,
                "runtime_id": RUNTIME,
                "policy_digest": POLICY,
                "monotonic_start_ns": start_ns,
                "monotonic_end_ns": end_ns,
                "observed_at": observed_at,
                "outcome": "pass",
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "payload_sha256": payload_sha,
            })
        evidence[probe_id] = canonical({
            "schema_version": 1,
            "suite_id": "jetvpn-sandbox-runtime-acceptance",
            "suite_version": "1.0.0",
            "attempt_id": ATTEMPT,
            "runtime_id": RUNTIME,
            "policy_digest": POLICY,
            "probe_id": probe_id,
            "observations": evidence_observations,
        }, ascii_only=True)

    base = AcceptanceExpectation(
        provider_id="fixture-provider",
        region="eu-test-1",
        task_id="fixture-task",
        attempt_id=ATTEMPT,
        image_digest=IMAGE,
        policy_digest=POLICY,
        trusted_key_id="acceptance-key-01",
        now=NOW,
    )
    expected = AcceptanceProvenanceExpectation(
        acceptance=base,
        runtime_id=RUNTIME,
        observer_registry_sha256=registry_sha,
        observer_registry_version=REGISTRY_VERSION,
    )
    return expected, registry, signature_verifier, reader, evidence, results, envelopes


class SchemaV3ReportDraftTests(unittest.TestCase):
    def build(self, case=None, **overrides):
        case = case or make_case()
        expected, registry, verifier, reader, evidence, results, envelopes = case
        args = {
            "started_at": "2026-11-24T11:55:00Z",
            "completed_at": "2026-11-24T11:59:55Z",
            "probe_evidence": evidence,
            "observer_results": results,
            "raw_observer_envelopes": envelopes,
            "registry": registry,
            "observer_signature_verifier": verifier,
            "replay_receipt_reader": reader,
        }
        args.update(overrides)
        return build_schema_v3_report_draft(expected, **args)

    def test_valid_draft_is_deterministic_and_keeps_authorization_disabled(self):
        case = make_case()
        first = self.build(case)
        second = self.build(case)
        self.assertEqual(first, second)
        report = json.loads(first.report_bytes)
        manifest = json.loads(first.envelope_manifest_bytes)
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["observer_envelope_manifest_sha256"], first.observer_envelope_manifest_sha256)
        self.assertEqual(hashlib.sha256(first.envelope_manifest_bytes).hexdigest(), first.observer_envelope_manifest_sha256)
        self.assertEqual(len(report["probes"]), len(REQUIRED_PROBES))
        self.assertEqual(len(manifest["entries"]), first.observer_count)
        self.assertFalse(first.signature_verified)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.eligible_for_untrusted_execution)
        self.assertFalse(first.patch_applied)

    def test_missing_observer_pair_is_rejected(self):
        case = list(make_case())
        case[5] = dict(case[5])
        case[5].pop(next(iter(case[5])))
        with self.assertRaisesRegex(AcceptanceReportV3Error, "exactly cover"):
            self.build(tuple(case))

    def test_missing_receipt_fails_closed(self):
        case = list(make_case())
        reader = case[3]
        reader.receipts.clear()
        with self.assertRaisesRegex(AcceptanceReportV3Error, "committed immutable replay receipt"):
            self.build(tuple(case))

    def test_tampered_raw_envelope_is_rejected(self):
        case = list(make_case())
        envelopes = dict(case[6])
        pair = next(iter(envelopes))
        envelopes[pair] += b" "
        case[6] = envelopes
        with self.assertRaises(ValueError):
            self.build(tuple(case))

    def test_invalid_observer_signature_is_rejected(self):
        case = list(make_case())
        verifier = case[2]

        class RejectingVerifier:
            def verify(self, key_id, message, signature):
                return False

        case[2] = RejectingVerifier()
        with self.assertRaisesRegex(AcceptanceReportV3Error, "signature is invalid"):
            self.build(tuple(case))

    def test_altered_evidence_is_rejected(self):
        case = list(make_case())
        evidence = dict(case[4])
        first_probe = sorted(REQUIRED_PROBES)[0]
        evidence[first_probe] += b" "
        case[4] = evidence
        with self.assertRaises(AcceptanceReportV3Error):
            self.build(tuple(case))

    def test_failed_probe_observation_is_rejected(self):
        case = list(make_case())
        results = dict(case[5])
        pair = next(iter(results))
        old = results[pair]
        old_obs = old.observation
        failed = ProbeObservation(
            probe_id=old_obs.probe_id,
            observer_domain=old_obs.observer_domain,
            observer_id=old_obs.observer_id,
            attempt_id=old_obs.attempt_id,
            runtime_id=old_obs.runtime_id,
            policy_digest=old_obs.policy_digest,
            monotonic_start_ns=old_obs.monotonic_start_ns,
            monotonic_end_ns=old_obs.monotonic_end_ns,
            observed_at=old_obs.observed_at,
            outcome="fail",
            payload=old_obs.payload,
        )
        results[pair] = AuthenticatedObserverResult(
            observation=failed,
            observer_registry_sha256=old.observer_registry_sha256,
            observer_registry_version=old.observer_registry_version,
            key_id=old.key_id,
            sequence=old.sequence,
            nonce_sha256=old.nonce_sha256,
            envelope_sha256=old.envelope_sha256,
            challenge_expires_at=old.challenge_expires_at,
            accepted_at=old.accepted_at,
            ledger_revision=old.ledger_revision,
            fencing_epoch=old.fencing_epoch,
        )
        case[5] = results
        with self.assertRaisesRegex(AcceptanceReportV3Error, "does not match verified"):
            self.build(tuple(case))


if __name__ == "__main__":
    unittest.main()
