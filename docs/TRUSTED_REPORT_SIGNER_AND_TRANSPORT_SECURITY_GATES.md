# Trusted Report Signing, Host–Observer Transport, and Persistence Security Gates

**Status:** implementation contracts and pre-implementation boundary assessment; not an independent security approval.
**Scope:** schema-v3 acceptance only. No production KMS/HSM, mTLS deployment, durable replay database, cloud resource, or untrusted execution is provisioned by this change.

## 1. Trusted Report Signer boundary

The report builder is deterministic and unsigned. The independent schema-v3 verifier reconstructs the report from exact raw evidence, retained observer envelopes, pinned observer identities, and replay receipts. The signer must not accept a caller-created Python result object, a boolean such as `validated=true`, a draft object, or an arbitrary report digest supplied without proof.

The signer contract therefore requires a short-lived, verifier-signed authorization attestation. Its canonical signed payload binds exactly:
- verifier identity and signer audience;
- schema-v3 report SHA-256;
- retained observer-envelope manifest SHA-256;
- unique verification ID;
- issue and expiry times (maximum 120 seconds);
- explicit Ed25519 algorithm identifier.

The signer independently verifies that attestation against a verifier public key pinned outside the repository and checks both exact digests against the bytes supplied for signing. It also checks the report's schema and pinned signing key ID. The attestation does not authorize a different report, manifest, audience, verifier, or key.

Before calling the KMS/HSM signing adapter, the signer atomically consumes the verification ID in a durable one-time authorization ledger. Reuse, store outage, uncertain transaction outcome, signature failure, expiry, digest mismatch, or key mismatch must fail closed. If signing fails after the authorization ID is consumed, issue a new verifier attestation after re-verification; do not make the consumed authorization reusable.

### Mandatory production properties

- The verifier attestation signing key is distinct from the report signing key.
- The signer is a separate process/workload and has no API that accepts arbitrary report bytes without a verifier attestation.
- Verifier public-key pin, signer key ID, audience, and trust epoch come from protected deployment configuration, not request fields.
- Report private key is non-exportable and held by a KMS/HSM or equivalent isolated signing boundary.
- KMS/HSM policy allows signing only to the signer workload identity; CI, guest, provider, observer, PR branch, and report submitter cannot invoke it.
- Signer authorization ledger is durable, atomic, anti-replay, and independently monitored.
- Audit includes report/manifest digest, verifier identity, verification ID, signer key ID, timestamp, and outcome; never private keys or credentials.
- Rotation and revocation are controlled by the protected trust control plane, with overlap and emergency-revocation semantics.
- A report signature proves only that the protected verifier authorized those exact bytes. It does not itself authorize code execution or establish that an external runtime was safe.

The repository implementation in this change is a fail-closed contract adapter with injected verifier, ledger, clock, and signing backend. Test fakes are not production trust anchors. A production Ed25519 verifier and KMS/HSM backend require separate implementation and review.

## 2. Host–Observer authenticated transport boundary

The current host challenge factory generates a 32-byte nonce using the operating-system CSPRNG and binds it to the pinned observer identity, audience, attempt, runtime, policy digest, and probe. This is a local issuance primitive, not a network protocol.

A production Host↔Observer channel must provide:
1. TLS 1.3 with mutual authentication; TLS 1.2 only if explicitly justified by the deployment security policy.
2. Workload identities issued by a protected identity provider, with certificate SAN/URI identity mapped to the exact `observer_id` and trust domain.
3. Host-side certificate-chain, issuer, SAN, EKU, validity, revocation, audience, and expected service-name validation. Never disable hostname or certificate verification.
4. Observer-side validation of the host workload identity and authorization for the exact challenge audience and operation.
5. Message-level Ed25519 signatures even over TLS, because evidence must remain independently verifiable after transport termination.
6. Strict request/response size limits, bounded deadlines, rate limits, connection pool isolation, and fail-closed behavior on timeout or trust-provider outage.
7. Challenge delivery and response bound to one request ID; no cross-audience forwarding, redirects to untrusted origins, or challenge reuse.
8. Certificate/key rotation with bounded overlap, revocation propagation SLA, and audit.
9. Secrets and private keys held outside guest, provider, task worktree, CI artifacts, and logs.

The transport adapter should expose a narrow interface that accepts a typed challenge and returns raw bounded envelope bytes plus authenticated peer identity metadata. The envelope verifier remains responsible for message signature, nonce, sequence, identity registry, attempt/runtime/policy binding, and replay acceptance. TLS identity must not replace message-level verification.

No network transport is implemented or enabled by this change. Certificate authority selection, workload identity provider, trust roots, DNS/service discovery, network policy, secret delivery, deployment environment, and operational ownership must be selected and independently reviewed before implementation.

## 3. Durable Replay Store security boundary

The existing `ObserverReplayStore` is a protocol; the in-memory fake is test-only. The design in `SANDBOX_REPLAY_STORE_DESIGN.md` remains the source of transaction requirements. This assessment confirms that a production store must not be implemented as a local file, SQLite database, process cache, or ordinary database table without the protected monotonic/fencing boundary.

### Required security properties before choosing a database

- Atomic nonce consumption, envelope digest uniqueness, observer-wide monotonic sequence advancement, and immutable audit receipt creation in one serializable transaction.
- Stable sequence namespace keyed by observer identity, not key ID, so key rotation cannot reset replay protection.
- Current fencing-token validation on every writer transaction; stale leaders cannot commit after failover.
- Protected external high-water checkpoint for restore/rollback detection. A database backup alone is not a trust root.
- Read-after-commit receipt retrieval from the authoritative ledger, with authenticated host workload identity and exact field comparison.
- Guest, provider, observer, task branch, CI, and report submitter have no read/write access.
- Database outage, replication lag, partition, uncertain commit, corrupt state, stale restore, audit failure, or inconsistent epoch fails closed.
- Encryption at rest and in transit, separate database administration, least-privilege credentials, append-only audit, backup/restore drills, and incident response.
- Defined retention for nonce tombstones, observer sequence high-water state, and audit records; expiry cleanup cannot erase anti-replay state.
- Concurrency/fault-injection tests for races, failover, restore, and transaction failures against the selected real database in an isolated environment.

### Decision

Do not create a production Replay Store until the owner selects the persistence platform and trust-control-plane operator, supplies the intended deployment identity model, and an independent reviewer signs off on the data-flow diagram, transaction isolation/fencing semantics, restore protocol, IAM policy, network boundary, and test plan. This is an explicit security gate, not a coding backlog item that can safely be bypassed for speed.

## 4. Integrated acceptance flow and trust transitions

The non-executing in-repository flow is:

```text
Host challenge issuer (OS CSPRNG)
          |
          v
Authenticated Host–Observer transport [not implemented]
          |
          v
Observer envelope verifier
  - pinned identity/key registry
  - Ed25519 message signature
  - exact challenge/audience/context
  - replay consume + receipt readback
          |
          v
Host evidence collector
  - exact probe/domain inventory
  - trusted observer allowlist
  - raw payload and time/size checks
          |
          v
Schema-v3 report draft builder
  - exact raw envelope re-verification
  - receipt and provenance binding
  - deterministic report + envelope manifest
          |
          v
Independent schema-v3 report verifier
  - reconstruct report and manifest from exact bytes
  - verify observer signatures and replay receipts
  - verify acceptance report signature when present
          |
          v
Verifier-signed, short-lived authorization attestation [issuer integration pending]
          |
          v
Trusted Report Signer [KMS/HSM backend not implemented]
          |
          v
Signed report + independently retained audit evidence
```

The integrated pipeline added in this change connects envelope authentication, replay acceptance, host evidence collection, and deterministic report drafting. It does not create the missing network, durable store, attestation issuer, or production signing infrastructure.

## 5. Execution gate

Until every independent runtime, trust, persistence, and owner-approval gate is complete:
- `execution_authorized: false`;
- `eligible_for_untrusted_execution: false`;
- no provider connection, source transfer, VM provisioning, untrusted code execution, production key creation, deployment, or spend.
