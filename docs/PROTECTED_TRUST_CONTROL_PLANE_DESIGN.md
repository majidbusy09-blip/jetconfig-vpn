# Protected Trust Control Plane — Design and Acceptance Contract

**Status:** design only; no control-plane service, KMS integration, persistent monotonic store, signing key, or provider connection is implemented.

**Baseline:** PR #55 added the PyCA Ed25519 verification backend; PR #56 refreshed repository memory. The trust-store policy adapter remains a verifier, not a configuration-delivery or rollback-prevention system.

## 1. Objective and non-goals

Provide a host-side, independently administered mechanism that supplies the verifier with:
- canonical trust-store bytes;
- the SHA-256 digest pinned independently of those bytes;
- a monotonic trust-store version floor;
- a monotonic configuration epoch/revision;
- an audience binding (environment, provider, region, verifier deployment);
- bounded validity metadata and key lifecycle state.

The provider, guest, model, task artifact, PR branch, and trust-store document itself must not be able to choose or lower these values.

This phase does **not** connect a provider, create or use a signing key, provision a cloud service, transfer private source, or authorize untrusted execution. The existing verifier continues to return evidence decisions only.

## 2. Trust domains and authority

| Component | Trust level / responsibility |
|---|---|
| Offline root / deployment trust anchor | Highest authority. Public root key or equivalent immutable trust anchor is provisioned out of band into the host verifier deployment. Private root material remains offline or in a dedicated HSM/KMS. |
| Control-plane configuration service | Authenticates the verifier workload, serves an authenticated configuration envelope, enforces audience and expiry, and coordinates atomic updates. It is outside provider and guest. |
| Monotonic state store | Durable transactional store supporting conditional compare-and-swap / serializable transactions. Stores highest accepted epoch and trust-store version per audience. |
| HSM/KMS signer | Signs configuration envelopes and audit checkpoints. Private signing material is never exported to application code, CI artifacts, provider, guest, or repository. |
| Host verifier | Validates root signature, audience, expiry, epoch, version, and trust-store digest before constructing `PinnedTrustStoreVerifier`. |
| Provider / guest | Untrusted. May submit evidence, but cannot fetch control-plane secrets, change trust configuration, or sign acceptance reports. |

A repository file, GitHub variable, workflow artifact, provider response, guest environment variable, or trust-store sidecar digest is not an independent trust root by itself.

## 3. Signed configuration envelope

The service returns one canonical, size-bounded envelope. Version 1 should contain exactly:

- `schema_version`: integer, fixed at 1;
- `audience`: exact environment + verifier deployment + provider + region identity;
- `config_epoch`: positive monotonically increasing integer;
- `trust_store_version_floor`: positive monotonically increasing integer;
- `trust_store_sha256`: lowercase SHA-256 of the exact canonical trust-store bytes;
- `trust_store_bytes`: canonical UTF-8 trust-store document (or an immutable content-addressed reference whose bytes are independently fetched and re-hashed);
- `issued_at`, `expires_at`: strict UTC timestamps;
- `root_key_id`: pinned root signer identifier;
- `signature_algorithm`: explicit supported algorithm identifier.

The signature covers the canonical envelope excluding only its signature field. Reject duplicate JSON keys, unknown fields, noncanonical encodings, invalid UTF-8, non-finite numbers, excessive nesting/size, invalid timestamps, unknown schema/algorithm, audience mismatch, expired/future-issued envelopes, and digest mismatch. The root verification key is provisioned independently of the envelope.

Do not accept a configuration merely because its own payload says which key should verify it. The root key identity and algorithm policy come from the verifier deployment's independent trust anchor.

## 4. Anti-rollback and atomic update protocol

For each exact audience, the monotonic state store maintains:
- `highest_config_epoch`;
- `highest_trust_store_version`;
- `accepted_envelope_sha256`;
- last accepted root key ID and acceptance timestamp.

Acceptance must be a single transaction:

1. Fetch the envelope over authenticated TLS using workload identity. No provider/guest credential is accepted.
2. Verify the envelope signature against the out-of-band root trust anchor.
3. Verify exact audience, bounded lifetime, schema, canonical bytes, and trust-store digest.
4. Validate trust-store canonical schema and require its version to meet the envelope floor.
5. Begin a serializable transaction / conditional compare-and-swap against the previously read monotonic state.
6. Require the new epoch and trust-store version to be strictly greater, or permit an exact same-epoch/same-digest idempotent read only. Same epoch with different bytes is a hard conflict.
7. Atomically persist the new epoch, version, envelope digest, and audit record. If the transaction fails or state is unavailable, reject; do not fall back to a local file or guest state.
8. Only after durable commit, construct the host-side verifier using the accepted bytes, pinned digest, and floor.

The verifier must not accept an older epoch even if its signature is valid. Database restore, region failover, or disaster recovery must not silently reset the monotonic floor. Recovery requires independently authenticated checkpoint reconciliation and an explicitly authorized higher epoch; it must never lower the floor.

A local JSON file, process memory, Git ref, or CI cache is not sufficient persistent anti-rollback storage. A filesystem implementation may be used only as a test fake and must be labelled non-production.

## 5. Rotation, revocation, and emergency response

- **Planned rotation:** publish a new trust-store version with old and new public keys overlapping for a bounded window; deploy a higher signed config epoch; verify the new key through known-answer and integration tests; retire the old key only after all verifier audiences acknowledge the new epoch.
- **Revocation:** publish a higher epoch immediately marking the key revoked; acceptance must fail closed for that key. Cache lifetime must be short and bounded by envelope expiry. Emergency revocation cannot wait for a normal rotation window.
- **Root rotation:** require a cross-signed transition or a separately provisioned new root through the offline deployment process. The envelope cannot self-authorize a root change.
- **Compromised signer:** freeze config writes, revoke the signer in the offline root policy, rotate through the break-glass ceremony, invalidate cached envelopes, and record the incident.
- **Break glass:** two-person approval, authenticated operator identities, reason/ticket, bounded scope and duration, append-only audit, and a new strictly higher epoch. No “set version back” operation exists.
- **Recovery:** restore service availability from replicated monotonic state and signed checkpoints. If consistency cannot be proven, fail closed and require operator reconciliation.

## 6. Audit and observability

Append-only audit records should include audience, previous/new epoch, previous/new trust-store version, old/new digest, root key ID, operator or workload identity, reason, timestamps, transaction ID, and outcome. Never record private keys, API credentials, raw provider secrets, or private source.

Alert on stale configuration, failed signature, digest mismatch, audience mismatch, same-epoch conflict, rollback attempt, unexpected root key, revocation propagation delay, monotonic-store unavailability, and audit write failure. Audit failure blocks acceptance of a configuration update.

## 7. Host-verifier interface boundary

The future implementation should expose a narrow interface equivalent to:

```python
class ProtectedTrustConfigProvider(Protocol):
    def load_for_audience(self, audience: TrustAudience) -> AcceptedTrustConfig:
        """Return only a root-verified, unexpired, durably anti-rollback-accepted config."""
```

`AcceptedTrustConfig` must be immutable and carry exact trust-store bytes, independently verified digest, minimum version, config epoch, audience, expiry, and acceptance transaction/audit reference. It must not accept caller-provided overrides from the provider, guest, report, or task payload.

The host adapter must then pass only the verified values to `PinnedTrustStoreVerifier`. Do not change that verifier to silently fetch network configuration or persist state itself; keep I/O, identity, durable state, and cryptographic policy boundaries explicit.

## 8. Required test matrix before implementation is accepted

Use deterministic fake root keys and an in-memory transactional store in unit tests only. Required cases:

1. valid envelope accepted and exact trust-store digest rechecked;
2. wrong root signature, unknown root key, and altered signed bytes rejected;
3. audience/provider/region/environment mismatch rejected;
4. expired, future-issued, excessive-lifetime, malformed timestamp rejected;
5. duplicate keys, unknown fields, noncanonical JSON, invalid UTF-8, oversize and deep JSON rejected;
6. lower epoch rejected even when correctly signed;
7. lower trust-store version rejected even when correctly signed;
8. same epoch + same digest idempotent; same epoch + different digest rejected;
9. concurrent updates cannot both commit from the same prior epoch;
10. transaction failure does not expose new config to verifier;
11. monotonic store unavailable, corrupted, restored from stale backup, or inconsistent across failover fails closed;
12. revocation propagates within a defined maximum cache TTL;
13. rotation overlap works, retired/revoked keys fail closed;
14. root rotation requires the offline/cross-sign ceremony;
15. audit write failure blocks config acceptance;
16. break-glass requires two distinct authorized principals and a higher epoch;
17. no configuration or state is readable from guest/provider;
18. secrets/private keys never enter logs, artifacts, or repository;
19. config cache cannot outlive signed expiry;
20. host verifier uses trusted time and rejects untrusted guest timestamps.

The tests must assert both positive behavior and fail-closed behavior, including transaction races and restart/recovery.

## 9. Operational acceptance gates

Before a real control-plane pilot, separately review:
- chosen cloud/KMS/HSM and region/data residency;
- workload identity and least-privilege policy;
- transactional monotonic store guarantees, backup/restore, and failover semantics;
- signer ceremony, dual control, root rotation, and incident response;
- audit retention, tamper resistance, monitoring, and operator access;
- dependency hashes/provenance and reproducible build;
- threat model and independent security review.

Provisioning accounts, KMS keys, paid resources, provider services, or transferring private source requires separate owner approval. This design document alone does not satisfy any operational gate.

## 10. Execution policy

Even after protected trust configuration is implemented, a verified trust store is only one prerequisite. The 20-probe runtime suite still needs a real independently controlled host controller, guest probes, external canary, signing service, and execution against the exact candidate VM. Until all independent runtime gates and separate owner approval are complete:

- `execution_authorized: false`;
- `eligible_for_untrusted_execution: false`;
- no provider connection, untrusted code execution, source transfer, VM provisioning, or spend.
