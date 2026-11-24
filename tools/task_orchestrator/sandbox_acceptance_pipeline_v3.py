"""Integrated non-executing schema-v3 acceptance assembly.

This adapter connects authenticated observer envelopes, replay acceptance,
host evidence collection, and deterministic report drafting. It does not
provision transport, persist data, sign reports, launch probes, or authorize
untrusted execution.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from tools.task_orchestrator.sandbox_acceptance_provenance import AcceptanceProvenanceExpectation
from tools.task_orchestrator.sandbox_acceptance_report_v3 import (
    SchemaV3ReportDraft,
    build_schema_v3_report_draft,
)
from tools.task_orchestrator.sandbox_host_evidence import (
    CollectedEvidenceBundle,
    HostEvidenceCollector,
    ProbeObservation,
    _required_domains,
)
from tools.task_orchestrator.sandbox_observer_auth import (
    AuthenticatedObserverResult,
    ObserverChallenge,
    ObserverEnvelopeVerifier,
    ObserverReplayStore,
    ObserverSignatureVerifier,
    ObserverReplayReceipt,
    PinnedObserverRegistry,
)


class AcceptancePipelineError(ValueError):
    """The integrated acceptance pipeline could not establish a complete result."""


@dataclass(frozen=True)
class SchemaV3AcceptanceAssembly:
    evidence: CollectedEvidenceBundle
    report_draft: SchemaV3ReportDraft
    authenticated_observer_count: int
    execution_authorized: bool = False
    eligible_for_untrusted_execution: bool = False
    patch_applied: bool = False


def assemble_schema_v3_acceptance(
    expectation: AcceptanceProvenanceExpectation,
    *,
    started_at: str,
    completed_at: str,
    raw_observer_envelopes: Mapping[tuple[str, str], bytes],
    challenges: Mapping[tuple[str, str], ObserverChallenge],
    registry: PinnedObserverRegistry,
    observer_signature_verifier: ObserverSignatureVerifier,
    replay_store: ObserverReplayStore,
    replay_receipt_reader,
    trusted_observers: Mapping[str, frozenset[str]],
    now: datetime,
) -> SchemaV3AcceptanceAssembly:
    """Verify all envelopes, collect exact probe evidence, and draft schema v3.

    Envelopes are ordered by their claimed observer ID/sequence solely to avoid
    rejecting valid monotonic streams due to map iteration order. The observer
    verifier still validates canonical bytes, signatures, identity, challenge,
    and replay state before any observation reaches the evidence collector.
    """
    expectation.validate()
    if not isinstance(registry, PinnedObserverRegistry):
        raise AcceptancePipelineError("Pinned observer registry is required.")
    if (
        registry.sha256 != expectation.observer_registry_sha256
        or registry.version != expectation.observer_registry_version
    ):
        raise AcceptancePipelineError("Registry does not match the protected acceptance expectation.")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise AcceptancePipelineError("Trusted pipeline time must be timezone-aware.")
    required_pairs = {
        (probe_id, domain)
        for probe_id, domains in _required_domains().items()
        for domain in domains
    }
    if not isinstance(raw_observer_envelopes, Mapping) or set(raw_observer_envelopes) != required_pairs:
        raise AcceptancePipelineError("Raw observer envelope inventory must exactly cover all required probe/domain pairs.")
    if not isinstance(challenges, Mapping) or set(challenges) != required_pairs:
        raise AcceptancePipelineError("A separately issued host challenge is required for every probe/domain pair.")

    ordered = []
    for pair in required_pairs:
        raw = raw_observer_envelopes[pair]
        if not isinstance(raw, bytes) or not raw:
            raise AcceptancePipelineError("Every retained observer envelope must be non-empty bytes.")
        try:
            envelope = json.loads(raw.decode("utf-8", errors="strict"))
            observer_id = envelope["observer_id"]
            sequence = envelope["sequence"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AcceptancePipelineError("Envelope cannot be indexed for ordered verification.") from exc
        if (
            not isinstance(observer_id, str)
            or isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 1
        ):
            raise AcceptancePipelineError("Envelope observer ID or sequence is invalid.")
        ordered.append((observer_id, sequence, pair))

    verifier = ObserverEnvelopeVerifier(
        registry=registry,
        signature_verifier=observer_signature_verifier,
        replay_store=replay_store,
        now=now,
    )
    results: dict[tuple[str, str], AuthenticatedObserverResult] = {}
    observations: list[ProbeObservation] = []
    for _, _, pair in sorted(ordered):
        try:
            result = verifier.verify(
                raw_observer_envelopes[pair],
                challenge=challenges[pair],
            )
        except Exception as exc:
            raise AcceptancePipelineError(
                f"Observer envelope failed authentication/replay acceptance for {pair[0]}/{pair[1]}."
            ) from exc
        if (result.observation.probe_id, result.observation.observer_domain) != pair:
            raise AcceptancePipelineError("Authenticated envelope identity does not match its inventory key.")
        results[pair] = result
        observations.append(result.observation)

    collector = HostEvidenceCollector(
        trusted_observers=trusted_observers,
        runtime_id=expectation.runtime_id,
        policy_digest=expectation.acceptance.policy_digest,
        now=now,
    )
    try:
        evidence = collector.collect(
            attempt_id=expectation.acceptance.attempt_id,
            observations=observations,
        )
    except Exception as exc:
        raise AcceptancePipelineError("Host evidence collection failed closed.") from exc

    draft = build_schema_v3_report_draft(
        expectation,
        started_at=started_at,
        completed_at=completed_at,
        probe_evidence=evidence.probe_evidence,
        observer_results=results,
        raw_observer_envelopes=raw_observer_envelopes,
        registry=registry,
        observer_signature_verifier=observer_signature_verifier,
        replay_receipt_reader=replay_receipt_reader,
    )
    return SchemaV3AcceptanceAssembly(
        evidence=evidence,
        report_draft=draft,
        authenticated_observer_count=len(results),
    )
