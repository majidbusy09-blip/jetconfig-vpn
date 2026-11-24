# Raw Observer Envelope Retention — Design Contract

## Status

Design only. No filesystem collector, object store, database, credentials, network endpoint, retention worker, or production storage was created.

This design preserves the exact signed observer envelope bytes so an auditor can independently re-check the Ed25519 signature and the relationship between the observer message, evidence payload, registry version, and signed acceptance report.

## Current gap

- `AuthenticatedObserverResult` preserves the exact envelope SHA-256 digest and verification context, but it does not contain the raw envelope bytes.
- Schema-v2 acceptance reports sign the envelope digest and cross-bind the payload digest to the raw probe evidence. They do not include the raw envelope bytes or a pre-acceptance envelope-manifest digest.
- The current artifact collector is a pure in-memory validator and requires an already-verified acceptance reference. It is therefore a post-acceptance packaging contract, not a pre-acceptance envelope staging implementation.
- A future design must close this gap without creating a circular report/artifact dependency.

## Two-phase retention model

### Phase A — pre-acceptance envelope staging

The trusted host controller retains the exact original bytes of each successfully verified envelope before the acceptance report is signed.

For each envelope:

1. Preserve the exact received canonical bytes. Do not parse and reserialize before storage; signature verification and digest must refer to the same bytes.
2. Recompute `sha256(envelope_bytes)` and require an exact match with `AuthenticatedObserverResult.envelope_sha256`.
3. Check the envelope is bounded by the observer protocol's 96 KiB maximum and the attempt's aggregate/count limits.
4. Derive the storage path from trusted host metadata, never from guest/provider fields. Suggested content-addressed layout:
   `artifacts/observer-envelopes/{attempt_id}/{digest-prefix}/{envelope-sha256}.json`.
5. Record a canonical staging-manifest entry containing path, size, envelope digest, observer ID/domain, key ID, attempt/runtime/policy/probe, registry digest/version, sequence, nonce digest, challenge expiry, and trusted accepted time.
6. Sort entries deterministically and compute the canonical staging-manifest SHA-256.

The staging store must be outside guest/provider visibility and use authenticated host-only access. The observer must not choose its path, storage key, retention policy, or registry pin.

### Phase B — signed report and post-acceptance artifact packaging

The next acceptance-report schema version should add a pinned `observer_envelope_manifest_sha256` and bind it to the signed report. This avoids changing schema v2's already-defined contract.

The trusted report signer must:
- accept only successful `AuthenticatedObserverResult` values from the host verifier;
- require the exact staged envelope bytes for each provenance record;
- recompute each envelope digest and the staging-manifest digest;
- require exact coverage of all observer provenance records;
- sign the manifest digest together with evidence and provenance;
- retain the raw envelopes under the same protected attempt/runtime/policy boundary.

After the report is signed and independently verified, the existing artifact-inventory contract can package the staged envelopes and other artifacts into the final post-acceptance artifact manifest, binding that final manifest to the signed report digest.

The resulting chain is:

```
signed observer envelopes
        |
        v
pre-acceptance content-addressed envelope store
        |
        v
canonical envelope staging manifest (digest)
        |
        v
next signed acceptance report (includes staging-manifest digest)
        |
        v
report signature verification
        |
        v
post-acceptance artifact manifest (includes report digest)
```

Schema v2 remains unchanged. Until the next schema version is implemented, v2 reports bind envelope digests but do not prove that the corresponding raw envelope bytes were retained.

## Storage and path safety

- Use a host-owned, pre-opened storage root with descriptor-relative operations and no-follow semantics for every path component.
- Reject symlinks, directories, devices, sockets, FIFOs, hard links, traversal, absolute paths, and platform-specific separators.
- Use exclusive create semantics for content-addressed objects; if a path already exists, re-read and hash the existing bytes before treating it as the same artifact.
- Hash bytes from the same open descriptor used for storage; do not hash a path and reopen it later.
- Use restrictive ownership/permissions and authenticated host-only access. The guest/provider must have no mount, path, credential, or API access to the staging store.
- Bound per-envelope size, total attempt bytes, file count, concurrent uploads, and retention.
- The artifact validator's current hard ceilings are 64 artifacts, 256 KiB per artifact, and 2 MiB aggregate. A production envelope-staging policy may set lower limits; it must not silently raise them without a reviewed policy change.

## Retention and cleanup

- Retain staged envelope bytes at least until the acceptance report and post-acceptance artifact manifest are verified and durably committed.
- Keep raw envelopes for the configured audit/reverification period. Deletion must be driven by a separate trusted retention policy and append-only audit.
- A failed report, failed signature, incomplete evidence, or uncertain commit must quarantine rather than delete the envelope set.
- Cleanup must be idempotent, bounded, crash-safe, and attempt-scoped. It must not delete data belonging to another attempt/runtime.
- Store a retention policy ID and expiry in the staging manifest; actual deletion requires a separately reviewed trusted storage lifecycle.
- Do not use the replay ledger as the raw-envelope store. The replay ledger stores hashes and audit context only.

## Independent re-verification

An auditor with:
- the raw envelope bytes;
- the pinned observer registry and trust-store versions;
- the host challenge record;
- the signed acceptance report and its trusted signing key;
- the canonical staging manifest;

must be able to recompute every digest, re-verify the observer signature, confirm challenge and sequence context, match payload bytes to probe evidence, and verify the acceptance report signature without trusting guest/provider metadata.

The challenge record must be retained or reconstructible from protected host audit data. The observer envelope itself carries the nonce but not the full challenge issue/expiry metadata.

## Required tests before implementation

- Exact-byte round trip (no reserialization).
- Envelope digest mismatch, truncated/oversized bytes, duplicate content-addressed path, and existing-object hash mismatch.
- Symlink/device/hard-link/traversal/TOCTOU races.
- Attempt/runtime/policy/registry/key/probe binding mismatch.
- Missing/extra/duplicate provenance entries and payload digest mismatch.
- Staging manifest deterministic serialization and digest.
- Crash between object write, manifest write, report signing, and post-acceptance packaging.
- Quarantine and cleanup retry behavior.
- Concurrent writes for same digest and different attempts.
- Retention boundary and deletion authorization.
- Independent offline re-verification using retained raw bytes.

## Non-authorization

This design does not create or operate a storage service, perform filesystem access, implement a trusted host collector, retain actual envelope bytes, sign reports, or prove sandbox isolation. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.
