# Sandbox Observer Authenticity — Signed Envelope Contract

## Status and scope

This is a non-production verification contract. It adds a pure envelope verifier that converts an authenticated, signed observer message into the existing typed `ProbeObservation` record. It does not open sockets, implement TLS, issue challenges, generate random nonces, provision keys, persist replay state, launch probes, or start a VM.

Implementation: `tools/task_orchestrator/sandbox_observer_auth.py`.

## Trust chain

The intended production chain has three independently controlled layers:

1. **Protected control plane:** delivers an observer registry digest/version/audience and a pinned Ed25519 trust-store digest/version through the existing root-signed trust configuration process. The provider, guest, task, PR branch, and observer cannot choose or lower these values.
2. **Pinned observer registry:** maps each observer ID to exactly one trust domain and key ID, with active/revoked status and a validity window. Registry bytes are canonical JSON; the exact SHA-256, minimum version, and audience are supplied from protected configuration outside the registry. This module checks the pin but does not authenticate or provision its source.
3. **Observer signing key:** the key ID is resolved by the existing pinned Ed25519 trust-store verifier. Production callers must use `PinnedTrustStoreVerifier` backed by the audited Ed25519 implementation; fake verifiers are test fixtures only.

Use separate keys and identities for `host_controller`, `guest`, and `external_canary`. Never let a guest identity stand in for host or canary evidence. The external canary must be administered outside the provider/guest trust domain.

## One-time host challenge

The trusted host controller must generate a cryptographically random 32-byte nonce and issue a short-lived challenge bound to:

- exact audience;
- observer ID and trust domain;
- attempt ID and runtime ID;
- pinned policy digest;
- exact probe ID from the acceptance suite inventory;
- host issue and expiry times.

The hard challenge lifetime is 120 seconds. Observation freshness is configurable from 1 second to a hard maximum of one hour; clock skew is configurable from zero to a hard maximum of 120 seconds. The challenge must be delivered over an authenticated channel and held by the host; it must not be generated from guest/provider input. This module validates a supplied challenge but does not generate or transport it.

## Signed observer envelope

Version 1 requires an exact canonical JSON schema containing:

- schema version and audience;
- observer ID, domain, and key ID;
- attempt, runtime, policy digest, and probe ID;
- base64 challenge nonce;
- strictly increasing observer sequence number;
- UTC observation timestamp and monotonic start/end offsets;
- pass/fail outcome;
- base64 raw payload and recomputed payload SHA-256;
- canonical base64 Ed25519 signature.

The signature covers canonical UTF-8 JSON containing every field except `signature_b64`. The verifier rejects duplicate JSON keys, unknown/missing fields, noncanonical serialization/base64, invalid timestamps, oversized payloads, payload-digest mismatch, invalid signature, identity/domain/key mismatch, stale/future observations, and challenge-context mismatch. Registry identity validity is checked again at the verifier's trusted acceptance time, not only when the registry object is constructed.

A valid envelope returns an `AuthenticatedObserverResult` only after the replay store accepts its nonce and sequence. The wrapper contains the `ProbeObservation` plus registry digest/version, key ID, sequence, nonce digest, and exact envelope digest. Pass only `result.observation` to `HostEvidenceCollector`, and preserve the wrapper's provenance fields in host-side audit.

## Anti-replay and durable state

`ObserverReplayStore` is an injected protocol. Its `consume` operation must be one atomic, durable transaction that:

- rejects a previously consumed nonce digest;
- requires a sequence strictly greater than the last accepted sequence for that observer (across attempts);
- records the envelope digest and accepted sequence together with nonce consumption;
- survives process restart and failover without rolling sequence state backward;
- fails closed when unavailable, corrupt, or inconsistent.

The included tests use an in-memory fake only. It is not suitable for production. A production replay store needs a separately reviewed transactional implementation and recovery/backup design. If a process crashes after nonce consumption but before evidence assembly, retry with a newly issued nonce and higher sequence; do not reaccept the old envelope.

## Evidence assembly integration

The returned `ProbeObservation` retains the original probe ID, observer domain/ID, attempt/runtime/policy bindings, monotonic offsets, UTC timestamp, outcome, and exact raw payload. It can then be passed to `HostEvidenceCollector`, which still checks the manifest-defined observer-domain ownership and complete probe inventory.

The authenticator does not change the evidence collector's allowlist semantics and does not create the final signed acceptance report. The current `CollectedEvidenceBundle` does not yet carry the wrapper's registry/envelope/sequence provenance. A later integration must bind those provenance fields and the assembled evidence digest into the signed report without treating a caller assertion as signature proof. Construct the pinned Ed25519 verifier with the same trusted acceptance time used by this envelope verifier so key-validity windows cannot drift.

See [the durable replay-store design](SANDBOX_REPLAY_STORE_DESIGN.md) for the transaction model, unique constraints, fencing, anti-rollback checkpoint, retention, recovery, and required test matrix.

## Rotation, revocation, and operational requirements

- Publish registry changes only through the protected root-signed trust configuration flow with a strictly higher registry version/config epoch.
- Planned rotation may use a bounded overlap of old/new observer keys; retired keys must fail after the overlap.
- Emergency revocation must publish a higher protected epoch and invalidate cached registry state within a defined maximum TTL.
- Root-key rotation remains governed by the offline/cross-sign ceremony in the protected trust control-plane design.
- Use mutual TLS/workload identity for host-to-canary transport in production; message signatures remain necessary for end-to-end provenance and replay protection.
- Audit identity changes, key rotation/revocation, challenge issuance, accepted/rejected envelope digests, replay-store failures, and recovery events. Never log private keys, raw credentials, or private source.
- The guest must not be able to access registry bytes, trust-store secrets, replay-store state, host challenge-generation secrets, or control-plane credentials.

## Tests

`tools/task_orchestrator/tests/test_sandbox_observer_auth.py` uses a deterministic fake signature verifier and in-memory replay store. It covers valid envelopes, signature tampering, exact challenge binding, nonce replay, sequence rollback, registry pin/version/audience/status checks, malformed JSON, payload digest/size, time windows, monotonic bounds, and replay-store failure.

Run:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_sandbox_observer_auth.py' -v
```

No production keys, real network transport, durable replay store, VM, provider, filesystem, or untrusted code are used.

## Non-authorization

This contract does not establish that a registry pin was provisioned correctly, that the replay store is durable, that TLS transport is authenticated, that a probe actually ran, or that a VM is isolated. Both `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## Replay acceptance receipt readback — PR #84

- `ObserverReplayStore.consume` now returns an immutable `ObserverReplayReceipt` after the nonce/sequence/audit transaction commits.
- The protocol also requires read-only `get_acceptance(observer_id, envelope_sha256)`. The verifier reads the receipt back and requires exact equality with the commit result before returning an `AuthenticatedObserverResult`.
- The receipt includes the complete acceptance context, challenge expiry, trusted acceptance time, ledger revision and fencing epoch. The result carries these values for later signed-report binding.
- The in-memory test fake is deterministic and non-durable. Its revision/fencing values are not production anti-rollback or an authenticated trust assertion.
