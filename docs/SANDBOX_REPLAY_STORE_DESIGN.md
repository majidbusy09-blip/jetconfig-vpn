# Durable Observer Replay Store — Design Contract

## Status

Design only. No database, service, credential, network endpoint, production replay store, or persistent state was created. The only executable implementation remains the in-memory test fake in `test_sandbox_observer_auth.py`.

The interface contract is `ObserverReplayStore.consume` in `sandbox_observer_auth.py`. It now carries the full audit context needed for durable transaction, replay, retention, and incident investigation.

## Required atomic input record

Each accepted envelope must commit these fields together:

- observer ID and trust domain;
- attempt ID, runtime ID, policy digest, and probe ID;
- observer registry digest and version;
- observer signing key ID;
- nonce SHA-256 digest;
- strictly increasing observer sequence;
- exact signed-envelope SHA-256 digest;
- challenge expiry timestamp;
- trusted host acceptance timestamp.

The store must never receive raw private keys or credentials. Challenge expiry uses exact UTC-second precision; host acceptance time preserves microseconds. Raw signed envelopes remain in the separately protected artifact-retention path; this replay ledger stores their digest and context.

## Logical state model

A production implementation should separate:

1. **Observer sequence state:** one durable row per stable observer ID containing the highest accepted sequence, current fencing epoch, and last accepted timestamp.
2. **Replay/audit ledger:** append-only accepted records with nonce digest, envelope digest, sequence, observer/domain/key, attempt/runtime/policy/probe, registry digest/version, challenge expiry, and acceptance time.
3. **Protected monotonic checkpoint:** an out-of-band high-water mark/epoch that prevents a restored database snapshot from silently rolling sequence state backward.

Recommended uniqueness constraints:

- global unique `nonce_sha256`;
- global unique `envelope_sha256`;
- unique `(observer_id, sequence)`;
- primary key `observer_id` in sequence state.

The observer ID must remain stable across planned key rotation so sequence continuity is preserved when `key_id` changes. A new identity ID is a new sequence namespace and requires a protected registry epoch change.

## Atomic transaction

Use a serializable transaction or a demonstrably equivalent compare-and-swap primitive. A transaction must:

1. Authenticate the host caller using a dedicated workload identity; reject guest/provider access.
2. Validate record types, digest formats, timestamp ordering, registry epoch, and the active fencing token.
3. Reject an existing nonce digest or envelope digest.
4. Advance sequence state only if the stored sequence is strictly lower than the submitted sequence. The update must affect exactly one row.
5. Insert the replay ledger record with all audit fields.
6. Append the audit event in the same transaction.
7. Commit all state together.

If any step fails, roll back the complete transaction and return failure. Never update sequence state separately from the nonce ledger/audit event. Do not use last-writer-wins semantics.

Example compare-and-swap condition:

```sql
UPDATE observer_sequence
SET last_sequence = :sequence,
    updated_at = :accepted_at,
    fencing_epoch = :fencing_epoch
WHERE observer_id = :observer_id
  AND last_sequence < :sequence
  AND fencing_epoch <= :fencing_epoch;
```

The production implementation must additionally verify that the supplied fencing epoch is the current active writer epoch; the SQL fragment alone is not a complete security boundary.

## Concurrency, failover, and rollback

- Two concurrent requests for the same observer sequence: exactly one may commit; the other fails.
- Same nonce with a higher sequence: reject.
- New nonce with a sequence equal to or below the high-water mark: reject.
- A database leader must hold a monotonically increasing fencing token. A stale leader must not be able to commit after failover.
- Backup restore must compare the restored sequence/epoch state with a protected external high-water checkpoint. A stale backup must be quarantined and reconciled, never accepted as current.
- Replication lag, split-brain, partial transaction, audit write failure, corruption, or uncertain commit outcome must fail closed.
- Do not fall back to an in-memory cache or local SQLite file for acceptance decisions.

## Retention

- Keep nonce tombstones at least through `challenge_expires_at + maximum_allowed_clock_skew`; a longer replay/audit window may be required by policy.
- Keep sequence high-water state for the full lifetime of the observer identity and preserve it after key rotation/revocation.
- Keep audit records under a separate bounded retention policy. Deleting audit payloads must not delete sequence high-water state.
- Expiry cleanup must be transactional and must not remove records needed for restore/recovery or an active investigation.
- Use a trusted UTC clock for `accepted_at` (UTC ISO-8601 with microseconds); never accept a caller-provided timestamp as the authoritative commit time. The verifier rejects challenge issue/expiry values with fractional seconds so nonce tombstone expiry cannot be shortened by truncation.

## Retry and idempotency

The current verifier treats a repeated nonce as replay and returns failure, even if the exact envelope was previously committed. This is intentional fail-closed behavior. If the host loses the response after commit, it must issue a fresh challenge and use a higher observer sequence. Do not introduce idempotent duplicate acceptance unless a separately reviewed protocol defines exactly how the prior accepted result is recovered without duplicating evidence.

## Security controls

- Store is reachable only from the trusted host controller using mutually authenticated workload identity.
- Guest, provider runtime, task branch, and observer cannot read or write replay state.
- Protect transport with TLS, storage with encryption at rest, and database credentials with a separately managed secret boundary.
- Audit every accepted/rejected transaction, sequence conflict, nonce collision, store outage, fencing change, restore, key rotation, and revocation. Do not log private keys or credentials.
- Keep database administrator credentials separate from host controller credentials; administrative access must not allow silent history rewrite.
- Bind the store to the protected observer registry digest/version and trust-control-plane epoch.

## Required test matrix before implementation

- Parallel requests with same nonce, same sequence, and different observers.
- Concurrent sequence 10/11 arrival in both orders.
- Crash/fault injection before and after every transaction operation.
- Audit insert failure and uncertain commit response.
- Database outage, replication lag, network partition, corrupt rows, and recovery.
- Leader failover with stale fencing token.
- Restore from an older backup against a newer protected checkpoint.
- Planned key rotation with stable observer ID and sequence continuity.
- Revocation and registry epoch change.
- Nonce expiry boundary and cleanup race.
- Attempt/runtime/policy/registry context mismatch.
- Audit retention expiry without sequence-state deletion.

Tests must run against a real isolated test database only after the database implementation and trust boundary are separately reviewed. Current tests remain in-memory fakes.

## Non-authorization

This design does not establish a production persistence boundary, durability, anti-rollback, database isolation, or runtime safety. No live store or external service was created. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## In-process acceptance receipt contract — PR #84

The observer verifier now requires a replay store to return an immutable `ObserverReplayReceipt` from the atomic `consume` operation and expose a read-only `get_acceptance(observer_id, envelope_sha256)` lookup.

The receipt carries the complete committed audit context plus `ledger_revision` and `fencing_epoch`. The verifier rejects missing/malformed receipt data, context mismatch, non-positive revision/epoch, readback failure, or any mismatch between the returned receipt and the independently read-back receipt. The resulting `AuthenticatedObserverResult` carries challenge expiry, accepted timestamp, ledger revision and fencing epoch for later report binding.

The in-memory fake increments a deterministic ledger revision and exposes immutable receipts. Tests cover successful readback, frozen receipt values, a missing readback, and a consume-only store that lacks the read API.

**Important limitation:** this is an API contract and test fake only. The in-memory revision and fixed fencing epoch do not provide durable monotonicity, multi-process consistency, anti-rollback, or cryptographic authenticity. A production reader must authenticate the host caller, read from the authoritative durable ledger, enforce current fencing, and compare against the protected external high-water checkpoint. The Python receipt object itself is not a trust root.
