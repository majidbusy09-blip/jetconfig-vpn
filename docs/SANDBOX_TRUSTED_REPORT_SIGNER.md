# Trusted Acceptance Report Signer — Contract

## Status and scope

Design contract only. This document specifies the trusted host-side boundary that may assemble and sign an acceptance report after observer verification. It does not implement signing, generate or provision a private key, create a signing service, retain files, access a replay database, launch probes, or authorize untrusted execution.

The current schema-v2 verifier remains read-only and unchanged. The next report format should be schema v3 because it must bind the pre-acceptance raw-envelope staging-manifest digest defined in `SANDBOX_OBSERVER_ENVELOPE_RETENTION.md`.

## Security objective

The acceptance-suite signature must attest to one exact, complete attempt:

- the pinned provider, region, task, attempt, runtime, image and policy;
- all required probe outcomes and exact raw evidence bytes;
- the pinned observer registry digest and version;
- every observer's identity, trust domain, key ID, strictly increasing sequence, nonce digest, exact envelope digest and payload digest;
- a deterministic manifest of the exact raw signed observer-envelope bytes;
- the suite start/completion interval and the signer key identity.

A report must not be signed if any required probe failed, any observer is missing/extra/duplicated, any envelope is absent or altered, the replay acceptance cannot be confirmed, or any binding is inconsistent.

## Trust boundaries

The future signer runs only in the trusted host control plane. It must not be loaded into the guest, provider runtime, untrusted worker, or model agent. The report signing key must be isolated from guest/provider access and selected through the protected trust configuration path.

The following values are not trust roots by themselves:

- a caller-created `AuthenticatedObserverResult`;
- a caller-supplied observer ID allowlist;
- a guest/provider success status;
- a claimed file type, link count, path, digest, or retention timestamp;
- an unverified replay-store response;
- an unsigned or self-described report.

`AuthenticatedObserverResult` is a Python dataclass and can be constructed by ordinary in-process code. Type checking it is useful API validation, but is not cryptographic proof that the observer verifier produced it. The signer must independently validate the raw envelope and query a trusted replay ledger for the committed acceptance receipt.

## Required signer interface

The implementation should expose narrow, provider-neutral protocols, with no shell, network, filesystem, provider, key-generation, or patch-application capability:

- `AcceptanceReportSigner.sign(key_id, canonical_report_bytes) -> signature_bytes`
- `ObserverSignatureVerifier.verify(key_id, signed_envelope_bytes, signature_bytes) -> bool`
- `ObserverReplayReceiptReader.get_acceptance(observer_id, envelope_sha256) -> immutable receipt | None`
- a pinned observer registry resolver;
- an immutable attempt expectation and exact raw evidence/envelope byte maps.

The signing interface accepts only an explicit key ID and exact canonical bytes. It must not expose private-key bytes, key generation, arbitrary key selection, or a generic signing oracle. Production implementation must use a separately approved protected signing backend; tests use deterministic fakes only.

The replay receipt reader is a read-only interface. Its returned receipt must originate from the same trusted durable transaction that consumed the nonce and advanced the observer sequence. The receipt must include at least:

- observer ID and trust domain;
- attempt, runtime, policy and probe IDs;
- observer registry digest and version;
- key ID, nonce digest, sequence and exact envelope digest;
- challenge expiry and trusted acceptance timestamp;
- a durable transaction/ledger revision or fencing epoch sufficient to identify the accepted state.

A missing, malformed, stale, mismatched, rolled-back, or unavailable receipt is a hard failure. The signer must not call `consume` again, fall back to an in-memory receipt, or accept a caller-created receipt object without an authenticated trusted-store boundary.

## Required pre-sign validation

Before invoking the report signer, the trusted report builder must:

1. Validate the pinned attempt expectation and schema-v3 policy; bind provider, region, task, attempt, runtime, image and policy exactly.
2. Require the exact 20-probe inventory and derive the exact observer-domain pairs from the pinned `runtime_probe_manifest.json`.
3. Require exactly one successful authenticated result, exact raw envelope byte string, and replay receipt for every required (probe, domain) pair. Reject missing, extra, duplicate, or failed records.
4. Enforce the observer registry digest/version pin and resolve the observer/domain/key mapping at the receipt's trusted acceptance time. Revoked, retired, expired, unknown, or mismatched identities fail closed.
5. Recompute SHA-256 over each exact raw envelope byte string and match it to both the verifier result and replay receipt. Never parse and reserialize the envelope before digest calculation.
6. Parse each envelope as strict canonical UTF-8 JSON, reject duplicate keys/non-finite values/unknown fields, decode canonical base64, and independently verify its Ed25519 signature over the exact unsigned canonical envelope.
7. Cross-check envelope audience, observer/domain/key, attempt/runtime/policy/probe, nonce digest, sequence, observed time, outcome and payload digest against the host challenge, result, replay receipt and pinned attempt.
8. Require the receipt's nonce, sequence, envelope digest, challenge expiry and accepted timestamp to match the authenticated envelope and attempt. Verify that the ledger revision/fencing epoch is current and not rolled back.
9. Recompute every raw probe-evidence digest; parse each evidence blob; require exact suite, attempt, runtime, policy and probe bindings; require all outcomes to pass; and cross-check every observation's observer ID/domain/payload digest against the corresponding verified envelope.
10. Build the canonical sorted observer-provenance inventory and the canonical raw-envelope staging manifest. Recompute both digests from exact bytes and require exact coverage of the verified records.
11. Enforce suite start/completion ordering, maximum duration, trusted clock skew/freshness, challenge validity, payload/envelope/report size limits, and aggregate byte limits.
12. Construct the schema-v3 report deterministically and invoke the signer exactly once with its canonical bytes.

No report signature is produced for partial evidence, failed probes, a stale or uncertain replay ledger, a changed registry, incomplete envelope staging, or any mismatch.

## Schema-v3 report bindings

Schema v3 should preserve the existing v2 fields and add:

- `observer_envelope_manifest_sha256`: digest of the canonical pre-acceptance staging manifest;
- optionally `observer_envelope_manifest_version` if the manifest format will evolve independently.

The report signature covers all fields, including the provenance inventory digest and the raw-envelope manifest digest. The manifest itself lists, in deterministic `(probe_id, observer_domain)` order, the host-derived content-addressed path, exact byte length, envelope SHA-256, observer/domain/key, attempt/runtime/policy/probe, registry digest/version, sequence, nonce digest, challenge expiry and trusted accepted time.

Do not add raw envelope bytes to the signed report. Retain them as separate protected artifacts and bind their exact manifest digest. Schema v1 and v2 remain unchanged; v2 must not be silently upgraded or treated as v3.

## Atomicity, consistency and failure behavior

The signer must operate on one immutable attempt snapshot. The replay receipt set, registry pin, evidence bundle, raw-envelope staging manifest and attempt metadata must share the same attempt/runtime/policy and a stable ledger revision/fencing epoch.

Before signing, re-read or transactionally pin the replay-ledger revision and manifest digest. If either changes, abort and rebuild from a fresh consistent snapshot. A production design should define how this snapshot is obtained without holding a long database transaction while cryptographic work occurs.

Signing success is not acceptance by itself. The host must independently verify the produced report signature using the pinned acceptance trust policy, then run the existing schema-v3 verifier over the exact report bytes, raw evidence and retained envelope manifest before marking the report accepted.

On signer timeout, uncertain commit, process crash, storage failure, signature verification failure, or lost response:
- do not mark the attempt accepted;
- do not fall back to another key or signer;
- preserve/quarantine the staged envelope/evidence set;
- record a bounded audit failure without leaking secret material;
- permit retry only through an idempotent attempt-scoped operation that recomputes the same canonical report bytes.

The signing backend should provide deterministic Ed25519 signatures for identical key/message inputs. If the backend cannot establish whether signing occurred, the caller must verify the stored output or fail closed; it must not invent a success response.

## Output contract

A successful test-only builder may return immutable values containing:

- exact canonical schema-v3 report bytes;
- signature bytes;
- report SHA-256;
- provenance-manifest SHA-256;
- raw-envelope staging-manifest SHA-256;
- signer key ID;
- verification summary with `signature_verified: true`;
- `execution_authorized: false`;
- `eligible_for_untrusted_execution: false`;
- `patch_applied: false`.

The production host must independently verify the returned report before accepting it. The builder must never set either execution flag to true.

## Required adversarial tests

- Caller-created or mutated `AuthenticatedObserverResult` with no matching replay receipt.
- Forged, missing, duplicate, stale, mismatched, or rolled-back replay receipts.
- Envelope digest mismatch, non-canonical bytes, duplicate JSON keys, malformed base64, invalid Ed25519 signature, wrong key, revoked key and registry-version mismatch.
- Challenge nonce, expiry, audience, attempt/runtime/policy/probe mismatch.
- Sequence rollback, duplicate nonce, duplicate envelope digest, duplicate observer/domain pair.
- Missing/extra/duplicate probe, observer, raw evidence, raw envelope or staging-manifest entry.
- Failed probe/outcome, altered payload, evidence digest mismatch, envelope payload mismatch.
- Non-deterministic ordering, canonicalization mismatch and manifest digest mismatch.
- Stale/future timestamps, suite duration overrun, oversized individual/aggregate input.
- Replay-ledger revision changes during preparation, fencing-token change, store outage and uncertain commit.
- Signer exception, invalid signature, wrong signer key ID, altered report bytes, retry and lost-response behavior.
- End-to-end fake-only verification of the generated report using the existing independent schema verifier.

## Implementation sequence

1. Add a read-only replay acceptance receipt protocol and strengthen the in-memory fake to expose immutable receipts; keep production persistence absent.
2. Add a pure report-v3 builder that consumes pinned expectations, verified result records, exact raw envelope bytes, exact evidence bytes and receipts; independently rechecks envelope signatures and every binding.
3. Add an injected report-signing protocol and deterministic fake signer. No private key or real signing service.
4. Add a strict schema-v3 verifier and adversarial tests; keep v1/v2 verifiers unchanged.
5. Bind the pre-acceptance envelope manifest and post-acceptance artifact manifest to the signed report digest.
6. Refresh project memory and review the trust-boundary design before considering any production signer.

## Non-authorization

This contract does not create a signing key, sign a production report, establish a production trust root, implement a durable replay database, retain actual files, execute runtime probes, provision a VM/provider, or authorize untrusted code. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.
