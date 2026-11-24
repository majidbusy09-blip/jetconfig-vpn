# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `3e613a8c03a39e4440c3702ac3505acb7b2eae27` (PR #53 squash merge).
- PR #20, PRs #38–#44, and PRs #46–#53 are merged.
- PR #47 introduced the synthetic-only sandbox lifecycle contract.
- PR #48 refreshed project memory after PR #47.
- PR #49 added the independent signed-evidence verifier and its 12 adversarial tests.
- PR #50 refreshed project memory after PR #49.
- PR #53 adds `sandbox_trust.py`, a strict trust-store policy adapter with canonical parsing, independent SHA-256 pinning, minimum-version enforcement, and active/in-window Ed25519 key selection; signature math remains injected and rollback state is external.
- PR #53 head `b0b5f72c1d8c7f0940b1c1cfb8cb5dacdb1cb11b` passed Task Orchestrator Tests #45334662136 (271 tests), Project Memory Audit #45334662120, Non-production PR Validation #45334662100, and Agent PR Lease and Scope Guard #45334659579; squash-merged as `3e613a8c03a39e4440c3702ac3505acb7b2eae27`.
- PR #51 binds every signed probe digest to the exact supplied raw evidence bytes, recomputes SHA-256, enforces exact evidence inventory, and caps each blob at 128 KiB / aggregate evidence at 2 MiB.
- PR #49 verification: Task Orchestrator Tests #45320041554 passed 259 tests; Project Memory Audit #45320041561 passed; Agent PR Lease and Scope Guard #45320038880 passed.
- PR #50 validation runs #45320512137 and related required checks completed successfully.
- PR #51 head `42c208398ef0b044ba54c17ca183957022eb0288`: Task Orchestrator Tests #45325193322, Project Memory Audit #45325193253, Agent PR Lease and Scope Guard #45325195790, and Non-production PR Validation #45325193266 all completed successfully; PR #51 merged as `1438d0a047523a22fee26e72ae12cf34cebbb95e`.
- Non-production PR Validation #45320041553 remained pending at merge. PR #49 changed only developer tooling and documentation; application source and version were unchanged.
- App source/version: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; `2.4.5+284`.
- Source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, context/impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. No automatic model wake-up or live provider dispatch exists.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch, local result ingestion, SHA-256 patch storage, and fail-closed live review authorization are implemented and integration-tested. Patches are not automatically applied.
- `sandbox_contract.py` supports only a fixed synthetic acceptance payload and fake-provider lifecycle tests.
- `sandbox_acceptance.py` verifies a strict signed report from a separate trusted runtime suite: pinned provider/region/task/attempt/image/policy, freshness, canonical JSON, signature, exact 20-probe inventory, and independently recomputed SHA-256 over all supplied raw evidence bytes. The signing verifier remains injected. `sandbox_trust.py` now validates an externally pinned trust-store digest, minimum version, key status, validity window, and Ed25519 public-key shape; signature mathematics still requires an audited injected backend, and the independent external probe suite is not installed.
- `runtime_acceptance_probe.py` is only a controlled benign Bubblewrap self-check; `runtime_probe.py` is host inventory/preflight. Neither is the independent 20-probe suite nor evidence of a production sandbox.
- Even a passing evidence report explicitly remains `execution_authorized: false` and `eligible_for_untrusted_execution: false`.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner remains opt-in and metadata-only; no live request has been made.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path.
- Neither E2B nor Daytona is approved for a pilot under current constraints. E2B requires prior written consent before testing and a payment method for EU workspace verification; Daytona's strict sandbox-level egress policy is tier-gated with a documented $500 Tier 3 top-up.
- No vendor account, API key, payment method, sandbox, private-source transfer, provider signing key, or provider spend has been created or authorized.
- No production release, deployment, version bump, signing change, app behavior, bot, payment, backend, or server change is in scope.
- CI/build success is not proof of physical-device VPN runtime behavior or sandbox isolation.

## Next engineering objective

Next implement the independent 20-probe host/guest runtime acceptance suite and protected trust-configuration control plane. Review audited Ed25519 dependency options without adding an unapproved dependency. Real VM/provider validation remains blocked pending separate account, consent, data-governance, and cost approval. Keep the runtime synthetic-only and do not run untrusted code.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.

## Latest verified snapshot — PR #55 merged (2026-11-24)

This section supersedes the earlier PR #53 baseline above.

- Current main merge commit: `3cc2e200dd02416d7b2fba02725b6734dffede39` (PR #55 squash merge).
- PR #55: [real Ed25519 sandbox evidence verifier](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/55), final head `56e48fac7e5cfdf25c07492daef9ed3cdd3c0805`.
- Final-head checks all passed: Task Orchestrator Tests run `45354914545`; Project Memory Audit run `45354914553`; Non-production PR Validation run `45354914620`.
- Added `tools/task_orchestrator/ed25519_backend.py`, implementing public-key Ed25519 verification with PyCA `cryptography`. Invalid signatures return false; malformed key/signature lengths and non-byte inputs are rejected. The implementation exposes no private-key, signing, or key-generation API.
- Added `tools/task_orchestrator/requirements-sandbox-crypto.txt` with exact pins: `cryptography==50.0.2`, `cffi==2.1.1`, `pycparser==3.12`. Both Python CI workflows install binary wheels. Pins are not hash-locked; provenance/hash verification remains open.
- Tests include RFC 8032 test vector 1, tampered message/signature rejection, and integration with `PinnedTrustStoreVerifier`.
- This closes the missing cryptographic-math backend only. Protected out-of-band trust-store digest/minimum-version delivery, persistent anti-rollback, key rotation/revocation operations, independent 20-probe host/guest suite, external canary, and real VM acceptance remain incomplete.
- No provider, API key, private-source transfer, VM, untrusted execution, production signing, release, deployment, or spend was used.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.

## Latest verified update — PR #56 merged; trust-control design added (2026-11-24)

- PR #55 merged as `3cc2e200dd02416d7b2fba02725b6734dffede39`.
- PR #56 project-memory refresh merged as `5354ba7c38d1b27ff75ace2ed288feb50551d701`.
- PR #56 final head `e07b35b4ccde0b78c50bf3bada16b1ad1ca9bf3f` passed Project Memory Audit run `45356110882` and Non-production PR Validation run `45356110761`.
- Added design-only trust-control-plane contract at `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md` and decision D-013. It defines root-authenticated config envelopes, audience binding, monotonic epochs/version floors, atomic CAS acceptance, rotation/revocation, audit, and fail-closed recovery.
- No actual control-plane service, persistent monotonic store, KMS/HSM integration, root signing key, or provider is implemented. The design does not create execution authorization.
- Next safe code phase: provider-neutral envelope validator + monotonic-store protocol, tested only with fake in-memory components; clearly label it non-production. Then implement the independent 20-probe host/guest runner architecture.
- Dependency pins are exact but not hash-locked. Supply-chain provenance remains open.
- No provider, API key, private-source transfer, VM, untrusted execution, signing key, production release, deployment, or spend was used.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.




## Latest authoritative snapshot — PR #57 merged (2026-11-24)

- Current main includes PR #57 squash merge `e28e16ba9b4021d3974085639df4c461774e8eaf`; PR #57 final head: `d60cf18554f37b0387bc6c5738edefdd2f04f602`.
- Final-head CI all passed: Task Orchestrator Tests run `45358099449`; Project Memory Audit run `45358099476`; Non-production PR Validation run `45358099550`.
- PR #57 is design/documentation only. `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md` specifies an out-of-band root trust anchor, signed configuration envelope, audience/expiry/digest binding, monotonic epoch/version floor, atomic CAS, rotation/revocation, audit, and recovery requirements. Decision D-013 records the choice.
- No control-plane service, root key, KMS/HSM, transactional monotonic store, provider, VM, or production anti-rollback implementation was created.
- Next safe coding step: provider-neutral signed-envelope acceptance module plus monotonic-store protocol, using deterministic fake verifier and in-memory CAS only in unit tests. Production persistence and trust must not be claimed.
- Execution remains disabled: `execution_authorized: false`, `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #59 merged (2026-11-24)

- Current `main` includes PR #59, squash merge commit `1e332fcd8f13c5ccebb352c31b72bbf09a27a1bb`. This supersedes earlier main HEAD values in this document.
- PR #59 adds:
  - `tools/task_orchestrator/trust_config_acceptance.py`
  - `tools/task_orchestrator/tests/test_trust_config_acceptance.py`
- The module validates a canonical schema-v1 signed trust-configuration envelope against an explicit audience, trusted UTC time, expiry/lifetime, root-signature verifier interface, trust-store SHA-256 digest, and the existing pinned trust-store verifier.
- Its monotonic-store Protocol requires atomic compare-and-swap and append-only audit to commit in one durable transaction. The acceptance result is returned only after that commit succeeds.
- Test coverage includes success/idempotency, rollback and same-epoch conflict, malformed and oversized input, expiry/digest failures, CAS races, invalid monotonic state, and store/audit failure paths. Test fakes are in-memory only.
- Final PR head `177a4090effd838add36188578a5d7e8a7c671f5` passed:
  - Task Orchestrator Tests run `45361973408`
  - Project Memory Audit run `45361973336`
  - Non-production PR Validation run `45361973411`
  - `validate-agent-pr` check `138334033651`
- Important limitations: root verifier is injected and no production root key is provisioned; no production durable monotonic store or atomic audit implementation exists; no live provider/network client/KMS/HSM/VM was introduced.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain unchanged. PR #59 does not authorize untrusted code execution.


## Latest authoritative snapshot — PR #68 merged (2026-11-24)

- Current main includes PR #67 merge `b0b0b80515f17c01836f558ff5700189c9a7bf32` and PR #68 merge `90dd9f848998ebb0c18b6c584938fee148d6fced`. PR #68 final head: `f76cdf060a2d7166639f6469bbcdf453d52b539b`.
- PR #67 final-head CI passed: Task Orchestrator Tests `45371950918`, Project Memory Audit `45371951039`, Non-production PR Validation `45371950980`.
- PR #68 final-head CI passed: Task Orchestrator Tests `45376199406`, Project Memory Audit `45376199527`, Non-production PR Validation `45376199739`.
- The 20 runtime probes are now specified in `tools/task_orchestrator/runtime_probe_manifest.json`; this is a contract inventory, not executable probes.
- `tools/task_orchestrator/sandbox_host_evidence.py` implements deterministic, fail-closed evidence assembly from typed observations. It validates exact probe/observer inventory, trusted observer ID allowlists supplied by the caller, attempt/runtime/policy binding, monotonic offsets, UTC freshness, payload bounds, deterministic evidence serialization, and host-side SHA-256 digests. Failed outcomes remain failed.
- The collector is not a host runtime controller: it cannot launch or inspect a VM, process, guest, filesystem, network, or provider; it does not cryptographically authenticate observer IDs or sign acceptance reports. Out-of-band identity provisioning remains unimplemented.
- PR #67 also adds a unit-tested CI path classifier. Tooling-only changes retain Python safety checks and can skip Flutter/Android APK build steps; application/build-affecting paths still trigger full app validation.
- No production Sandbox or untrusted-code execution was enabled. `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## Latest host lifecycle update — PR #70 merged (2026-11-24)

- PR #70 squash merge: `e699293c1495f3137dd319e37764a2db6c5dfff3`; final head `a4b79467d850663ae10f8ffebb8e544f9ecf199e`.
- Final-head CI passed: Task Orchestrator Tests `45377376254`, Non-production PR Validation `45377376173`, Project Memory Audit `45377376300`.
- `tools/task_orchestrator/sandbox_host_lifecycle.py` adds a pure lifecycle state-transition validator. It pins attempt/runtime/policy identity and monotonic deadline, restricts event names and transitions, distinguishes accepted/rejected evidence, and requires explicit termination plus cleanup confirmation. Cleanup failure is terminal.
- The module performs no I/O and invokes no adapter; it is not a process supervisor, timeout killer, VM controller, or proof of cleanup. The state machine only validates reported events.
- No runtime probes have been executed and no untrusted-code execution is enabled. Both execution flags remain false.


## Latest authoritative snapshot — PR #72 merged (2026-11-24)

- Current `main` HEAD: `a199b82ef70f492c2b8df42087992a917d293c7c` (PR #72 squash merge).
- PR #72 final head `26edb96019e3816e4e23cff24b957f2d0187ca12` passed:
  - Task Orchestrator Tests run `45379646169`
  - Non-production PR Validation run `45379646094`
  - Project Memory Audit run `45379646100`
- Added `tools/task_orchestrator/sandbox_artifacts.py`, `tools/task_orchestrator/tests/test_sandbox_artifacts.py`, and `docs/SANDBOX_ARTIFACT_COLLECTOR.md`; orchestrator README documents the contract.
- The validator enforces relative path allowlisting (`artifacts/`, `reports/`), traversal and unsupported component rejection, regular-file candidate declarations, symlink metadata rejection, single-link candidate declarations, duplicate and empty-file rejection, 64-file / 256 KiB-per-file / 2 MiB-total limits, bounded retention metadata (1 second to 30 days), SHA-256 recomputation from supplied bytes, and deterministic canonical manifest serialization.
- The manifest binds attempt ID, runtime ID, policy digest, evidence digest, signed acceptance-report digest, retention metadata, and each artifact's path/size/digest.
- Critical limitation: candidate bytes and metadata are supplied to a pure validator. It does not open or stat filesystem objects, prove that file-kind/link-count claims are true, verify report signatures, authenticate artifact provenance, store/delete files, or enforce retention. A trusted host-side collector remains unimplemented.
- No application source, native source, app version, payment/backend/server behavior, release workflow, or deployment was changed. No runtime probes or untrusted code were executed.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #74 merged (2026-11-24)

- Current `main` HEAD: `b40642e9cb58446b60cc356f349656c31818d898` (PR #74 squash merge).
- PR #74 final head `f633295b6c5ceb64eef183340d1fe5162b5edf59` passed:
  - Task Orchestrator Tests run `45382515116`
  - Non-production PR Validation run `45382515212`
  - Project Memory Audit run `45382515188`
- Added `tools/task_orchestrator/sandbox_observer_auth.py`, `tools/task_orchestrator/tests/test_sandbox_observer_auth.py`, and `docs/SANDBOX_OBSERVER_AUTHENTICITY.md`; orchestrator README documents the contract.
- The verifier checks a canonical observer registry against an independently supplied SHA-256 pin, minimum version and audience; binds observer IDs to trust domains and signing key IDs; validates one-time 32-byte host challenges (maximum 120 seconds); verifies canonical signed envelopes through an injected signature verifier; checks payload SHA-256, size, timestamps, monotonic offsets, and exact attempt/runtime/policy/probe bindings; and requires an injected atomic replay-store protocol to consume nonces and enforce increasing per-observer sequence numbers.
- Successful verification returns an `AuthenticatedObserverResult` containing a `ProbeObservation` plus registry/key/sequence/nonce/envelope provenance fields.
- Critical gaps: no protected registry provisioning, host nonce generation, authenticated TLS/workload-identity transport, durable replay-store implementation, or report-signature integration. The current evidence bundle does not yet retain authenticated envelope provenance. Production must use `PinnedTrustStoreVerifier` with time aligned to the observer verifier.
- CI used deterministic fake signatures and an in-memory replay store. No production keys, real canary, network, VM, runtime probe, filesystem collector, or untrusted code was used.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #76 merged (2026-11-24)

- Current `main` HEAD: `d393d2e5bb0a93390b8d572bf540ff9ec3f1fe7c` (PR #76 squash merge).
- PR #76 final head `87c19d15f714f4a21200d469ed828d4b83026861` passed:
  - Task Orchestrator Tests run `45384423673` — 355 tests passed
  - Non-production PR Validation run `45384423800`
  - Project Memory Audit run `45384423642`
- Added `tools/task_orchestrator/sandbox_acceptance_provenance.py`, `tools/task_orchestrator/tests/test_sandbox_acceptance_provenance.py`, and `docs/SANDBOX_ACCEPTANCE_PROVENANCE_V2.md`; updated orchestrator README.
- Schema v2 is separate from and does not modify schema v1. It pins exact runtime ID and observer registry digest/version; includes a sorted signed provenance list; recomputes its digest; checks exact 20-probe inventory; recomputes every raw evidence digest; parses canonical evidence and validates suite/attempt/runtime/policy/probe context; derives required observer domains from the pinned manifest; and cross-checks observer ID/domain and payload SHA-256 against provenance.
- V2 rejects duplicate nonce/envelope/observer-sequence tuples, incomplete/extra or unsorted provenance, stale/future observations, invalid monotonic intervals, noncanonical evidence, and unsupported signature algorithm labels. The signed report signature covers the complete provenance inventory.
- Trust limitation: v2 report signature is an attestation by the trusted acceptance-suite signer that observer envelopes were verified upstream. Raw observer envelope bytes are not included in the report and must be retained as separate protected artifacts for independent re-verification.
- No report signer, private key, durable replay store, nonce generator, TLS transport, VM, provider, network, filesystem collector, or untrusted code was implemented or used.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #78 merged (2026-11-24)

- Current `main` HEAD: `74a5b2b760362494711949b799031dc628612671` (PR #78 squash merge).
- PR #78 final head `156511739d82de7dac02adedb31aebc4e3ce4adb` passed:
  - Task Orchestrator Tests run `45385761279`
  - Non-production PR Validation run `45385761459`
  - Project Memory Audit run `45385761392`
- Expanded `ObserverReplayStore.consume` to persist the complete acceptance audit context: observer/domain, attempt/runtime/policy/probe, registry digest/version, key ID, nonce/envelope digest, sequence, challenge expiry, and trusted acceptance time.
- The verifier sends the replay store this context only after challenge, signature, payload, time, and identity checks succeed. Challenge expiry is whole UTC seconds; acceptance time preserves microseconds.
- The in-memory test fake rejects duplicate nonce/envelope digests and non-increasing sequence, and records all audit fields. It is not durable and is not a production replay store.
- Added `docs/SANDBOX_REPLAY_STORE_DESIGN.md` describing serializable transaction/CAS, unique constraints, atomic audit, fencing tokens, protected anti-rollback checkpoint, nonce tombstones, sequence retention, failover, backup restore, and recovery tests.
- No database/service, credentials, network endpoint, durable storage, KMS/HSM, provider, VM, or untrusted execution was created.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #80 merged (2026-11-24)

- Current `main` HEAD: `6666266f59877e9a066188d418938661075ae38e` (PR #80 squash merge).
- PR #80 final head `f41cee3685c3315ae3373f5c21f9fbaab9fa03dc` passed:
  - Task Orchestrator Tests run `45386943800`
  - Non-production PR Validation run `45386943924`
  - Project Memory Audit run `45386943682`
- Added `docs/SANDBOX_OBSERVER_ENVELOPE_RETENTION.md`, specifying protected exact-byte retention for observer envelopes.
- The design uses two phases: pre-acceptance content-addressed envelope staging with a deterministic manifest; then signed acceptance report binding of that manifest digest in the next schema version; finally post-acceptance artifact packaging bound to the verified report digest.
- Schema v2 remains unchanged and does not bind the pre-acceptance staging-manifest digest or include raw envelope bytes. It currently binds only envelope digests/provenance metadata to raw probe payload evidence.
- Design specifies host-derived paths, descriptor-relative no-follow access, same-descriptor hashing, bounded counts/sizes, quarantine on uncertainty, crash-safe cleanup, retention, and independent offline re-verification.
- No filesystem collector, storage backend, database, credentials, report signer, network, VM, provider, or untrusted execution was implemented or used.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Latest authoritative snapshot — PR #82 merged (2026-11-24)

- Current main HEAD: `d7ef7ed4266ea2606acd76f6e36fb4822af7d179` (PR #82 squash merge).
- PR #82 final head `d91ea3da44fc133e94621df4cae3dfd7dee174bf` passed:
  - Task Orchestrator Tests run `45390283412`
  - Non-production PR Validation run `45390283324`
  - Project Memory Audit run `45390283473`
- Added `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md`, defining the future trusted host-side acceptance report signing boundary and schema-v3 requirements.
- Critical security clarification: `AuthenticatedObserverResult` is a constructible Python dataclass, not a trust root. The signer must independently revalidate exact raw envelope bytes and Ed25519 signatures and match every record to a trusted replay acceptance receipt from the committed ledger transaction.
- Schema v3 should bind `observer_envelope_manifest_sha256`; schema v1/v2 remain unchanged. The design specifies immutable attempt snapshots, fencing/ledger revision, fail-closed behavior, independent post-sign verification, and adversarial tests.
- PR #82 is documentation only. No signer, private key, key generation, production signing service, replay DB, filesystem collector, network, VM, provider, probe execution, or untrusted code was added or used.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Main baseline and project-memory enforcement candidate — 2026-11-24

- Verified `main` baseline: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e` (PR #84 merge).
- PR #84 final head `1588aa5ddcc0c6b68ccf96ac5cd251e87f975085` passed Task Orchestrator Tests `45391947042` (358 tests), Non-production PR Validation `45391947037`, and Project Memory Audit `45391947062`.
- PR #84 introduced immutable replay acceptance receipts and exact readback checks, including ledger revision and fencing epoch. Production persistence remains absent.
- Candidate branch `feat/enforce-project-memory-pr-gate-20261124` adds `tools/project_memory/verify_change_memory.py`, unit tests, and a required Project Memory Audit step that checks whether implementation-sensitive PRs update the relevant durable project-memory documents.
- The candidate gate distinguishes ordinary app changes from orchestrator/memory/workflow changes and requires progressively relevant memory files. It checks PR diff membership, not prose correctness.
- The semantic/resolved/critical-path indexes are generated CI outputs retained for 30 days; only tracked docs provide durable project memory.
- Candidate branch is not merged; exact final-head CI and PR status must be recorded after validation.


## Task context memory expansion — candidate (2026-11-24)

- The task orchestrator's mandatory pinned project context now includes `docs/DECISIONS.md` and `docs/KNOWN_ISSUES.md`, in addition to the existing six core documents.
- Context packages continue to read tracked files from the exact pinned Git revision and include per-document hashes plus a canonical package hash. No mutable working-tree text is substituted.
- The combined context limit remains 512 KiB; adding these two memory documents reduces the remaining source-context budget. The builder fails closed rather than silently truncating.
- This change is part of the project-memory enforcement candidate PR #89 and requires exact-head Task Orchestrator and Project Memory Audit validation.


## Versioned agent context contract — candidate PR #89 (2026-11-24)

- The first attempt to add `docs/DECISIONS.md` and `docs/KNOWN_ISSUES.md` only to the orchestrator's required context failed CI because the provider-neutral envelope builder/validator and handoff fixtures still required the old six-document manifest.
- Corrected the design by introducing contract v1.2 with one canonical eight-document manifest in `agent_contract.py`, shared by the orchestrator and envelope builder.
- The validator remains backward-compatible with legacy v1.1 envelopes and results. New v1.2 envelopes require the exact eight-document path list in canonical order; result version must match its envelope.
- Updated context-builder, orchestrator, envelope-builder, patch-guard, and GitHub handoff tests/fixtures. The combined context ceiling remains 512 KiB.
- Exact-head CI after the v1.2 changes is pending; prior PR #89 CI failure remains recorded as a real finding, not a passing result.
