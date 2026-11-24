# Signed Acceptance Report v2 — Observer Provenance Binding

## Status

This is a local verification contract with deterministic fixtures. It does not create or sign reports, generate observer challenges, provision keys, launch probes, or authorize code execution. Existing schema-v1 reports and `verify_signed_acceptance_report` remain unchanged.

Implementation: `tools/task_orchestrator/sandbox_acceptance_provenance.py`.

## Why schema v2 is separate

Schema v1 binds the signed report to the raw per-probe evidence digests, but it does not include observer-envelope signature provenance. Schema v2 adds a strict, signed provenance inventory while preserving the v1 verifier unchanged. Consumers must explicitly choose v2 when authenticated observer provenance is required; a v1 report is not upgraded or implicitly treated as v2.

## Protected expectations

`AcceptanceProvenanceExpectation` wraps the existing pinned `AcceptanceExpectation` and adds:

- exact expected runtime ID;
- observer registry SHA-256 digest;
- observer registry version.

These values must come from trusted host/control-plane configuration, not the report, guest, provider, or observer. The existing acceptance expectation continues to pin provider, region, task, attempt, image, policy, signing key, and trusted time.

## Schema-v2 report fields

The v2 report retains all v1 fields and adds:

- `observer_registry_sha256`;
- `observer_registry_version`;
- `observer_provenance_sha256`;
- `observer_provenance`.

The provenance list is sorted by `(probe_id, observer_domain)`. Each record contains:

- probe ID, observer domain and observer ID;
- observer signing key ID;
- observer registry digest and version;
- per-observer sequence number;
- nonce digest and exact signed-envelope digest;
- raw observer payload digest;
- signature algorithm (Ed25519 only).

The report signature covers the entire canonical v2 document, including all provenance records and their digest. The provenance digest is recomputed over canonical UTF-8 JSON.

## Cross-binding to raw evidence

The verifier does not trust a provenance array merely because the report contains it. It independently:

1. Checks the exact v2 report schema, suite, signing key, attempt/provider/region/task/image/policy/runtime, timestamps, and protected observer-registry pin.
2. Requires the exact 20-probe inventory and all probes passing.
3. Requires the exact raw evidence inventory and recomputes every per-probe evidence SHA-256.
4. Parses each canonical host-assembled evidence blob and validates attempt/runtime/policy/probe context.
5. Derives required observer domains from the pinned runtime probe manifest and checks exact domain coverage/order.
6. Decodes each raw payload, recomputes its SHA-256, and cross-checks observer ID/domain and payload digest against the signed provenance record.
7. Rejects duplicate nonce digests, envelope digests, observer sequence pairs, missing/extra provenance records, invalid algorithms, malformed timestamps, stale/future evidence, and invalid monotonic intervals.
8. Verifies the acceptance-suite signature over the exact canonical v2 report bytes.

This binds the signed provenance records to the exact evidence bytes. The acceptance-suite signing key is the authority attesting that the observer envelopes were already verified by the trusted host-side observer verifier. The v2 verifier does not independently re-verify each observer signature because raw signed envelope bytes are represented by their digest and are not included in this report schema.

## Trust boundaries and remaining work

- The protected observer registry digest/version must be independently provisioned through the existing root-signed trust configuration path.
- The report signer must accept provenance only from successful `AuthenticatedObserverResult` values produced by the trusted host verifier; it must not trust caller-created records.
- The report signer must retain the exact raw observer envelope artifacts in a separately protected artifact set if later independent re-verification is required. The report binds their digests but does not contain the raw signed envelopes.
- The acceptance-suite signing key must be outside provider/guest control and remain pinned through the existing trust policy.
- No report signer, private key, durable replay store, observer transport, or production registry provisioning is implemented here.
- Schema v1 remains available for legacy verification; callers requiring observer authenticity must explicitly require schema v2 and must not silently fall back to v1.

Raw envelope retention and the next report-schema binding are specified separately in [the protected observer-envelope retention design](SANDBOX_OBSERVER_ENVELOPE_RETENTION.md). Schema v2 itself remains unchanged and does not include the pre-acceptance staging-manifest digest.

## Tests

`tools/task_orchestrator/tests/test_sandbox_acceptance_provenance.py` creates all 20 probe evidence blobs with fake observer provenance and a deterministic fake acceptance signer. It covers signature validation, registry/runtime pins, provenance digest, completeness/order, nonce/envelope/sequence uniqueness, observer/payload cross-binding, raw evidence digest, payload digest, probe context, timestamp/monotonic checks, strict schema, and non-authorization flags.

Run:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_sandbox_acceptance_provenance.py' -v
```

No production signing keys, real observer keys, VM, provider, network, filesystem collector, or untrusted code are used.

## Non-authorization

A valid v2 report is verified evidence only. It does not prove a VM boundary, actual probe execution, trusted replay-store durability, or host isolation. It does not authorize patch application or untrusted code execution. Both `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.
