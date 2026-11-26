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


## Latest verified main baseline — PR #84 merged (2026-11-24)

- Current `main` HEAD at the start of PR #88: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e` (PR #84 merge).
- PR #83 refreshed project memory after PR #82; PR #84 added immutable replay acceptance receipts and exact readback validation.
- PR #84 final head `1588aa5ddcc0c6b68ccf96ac5cd251e87f975085` passed Task Orchestrator Tests `45391947042` (358 tests), Non-production PR Validation `45391947037`, and Project Memory Audit `45391947062`.
- The replay verifier now requires a committed immutable receipt and exact equality of observer/attempt/runtime/policy/probe, registry/key, nonce/envelope digest, sequence, challenge expiry, acceptance timestamp, ledger revision, and fencing epoch before returning authenticated observer evidence. The store remains a protocol plus in-memory test fake; no durable store or production fencing exists.

## Active candidate implementation — PR #88 (not merged; 2026-11-24)

- PR: [#88 — non-circular verified report signing and schema-v3 pipeline](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/88).
- Base `main` SHA: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e`.
- Implementation checkpoint: `566fbb58c4e039ef88abee64a987995b029ba534`; branch `feat/host-csprng-challenge-issuer-20261124`. This checkpoint identifies the code tested by the listed CI runs; later documentation-only commits require fresh exact-head CI.
- Added deterministic schema-v3 report construction from exact probe evidence, raw observer envelopes, pinned observer registry, and matching committed replay receipts. Observer signatures and bindings are independently rechecked; the exact raw-envelope manifest digest is bound into the report.
- Added independent schema-v3 pre-sign content verification and post-sign signature verification. The verifier reconstructs the exact report and manifest from raw inputs; it does not trust caller-created authenticated-result objects.
- Added a verifier-signed, short-lived signing authorization attestation (maximum 120 seconds) binding verifier identity/key, signer audience, report SHA-256, envelope-manifest SHA-256, unique CSPRNG verification ID, issue/expiry times, and Ed25519 algorithm. Verifier-attestation and report-signing keys must be distinct.
- Added a fail-closed Trusted Report Signer gate that checks strict canonical schema-v3 content and the verifier attestation, atomically consumes the one-time authorization ID through an injected store, then calls an injected signing backend. No private key or production KMS/HSM implementation is included.
- Added an integrated non-executing acceptance pipeline and expanded Host challenge generation to OS CSPRNG with identity/audience/attempt/runtime/policy/probe binding; observer key rotation overlap and revocation behavior are covered by tests.
- Exact checkpoint CI: Task Orchestrator Tests run `45428730520` succeeded (401 tests); Non-production PR Validation run `45428731306` succeeded (tooling-only scope; Flutter/APK build skipped); Project Memory Audit run `45428731849` succeeded. The audit ran app regression tests, semantic AST/resolved-index/critical-path tests, deterministic index generation, a real-source task-intelligence smoke test, and lexical index freshness checks.
- Project Memory Audit uploaded semantic/resolved/critical-path and lexical index artifacts with 30-day retention. The detailed semantic artifacts are generated in CI and are not committed source files.
- PR #88 remains Draft/open/unmerged. No production mTLS transport, KMS/HSM keys, isolated signer deployment, durable Replay Store, production trust control plane, live probes, VM/provider, source transfer, or untrusted execution was performed. Independent external security review remains outstanding.
- Preserve `execution_authorized: false`, `eligible_for_untrusted_execution: false`, and `patch_applied: false`. No app, bot, payment, VPN runtime, version, release, or deployment change is included.


## Multi-project JET AI baseline — 2026-11-25

- PR #97 merged into `main` as `914445b758d049ad5b97d670a66635f4cf8aba7b`.
- Added `docs/MULTI_PROJECT_ARCHITECTURE.md`, `docs/PROJECT_MANIFEST_SCHEMA.json`, and `docs/PROJECT_ONBOARDING.md`.
- PR #97 exact-head checks passed: Project Memory Audit run `45483195909`, Non-production PR Validation run `45483195875`, and Agent PR Lease and Scope Guard run `45483192332`. A subsequent ready-for-review event re-ran the lease guard after the task lease had been released and failed closed because no active lease remained; the earlier exact-head guard pass was successful.
- The post-merge Project Memory Audit run `45484504394` for merge commit `914445b758d049ad5b97d670a66635f4cf8aba7b` completed successfully.
- JET VPN compatibility fixture: GitHub repository ID `1349356614`, canonical name `majidbusy09-blip/jetconfig-vpn`, default branch `main`. Candidate project ID `jet-vpn-android` is not registered/active.
- Issue #98 / Phase 2A implements a pure project manifest validator and adversarial tests. Base SHA: `914445b758d049ad5b97d670a66635f4cf8aba7b`; working branch: `agent/project-registry-validation-20261125`; task ID: `project-registry-validation-20261125`.
- Current Phase 2A changes: `tools/task_orchestrator/project_registry.py` and `tools/task_orchestrator/tests/test_project_registry.py`. No persistence, network, task-envelope integration, app changes, external repository changes, or project activation.
- The registry validator supports only the explicitly implemented subset of the checked-in JSON Schema; it rejects unsupported keywords and remote references. It is not claimed to be a general-purpose JSON Schema implementation.
- «حسابگر من» is not registered; its exact repository URL is still required.


## Phase 2A validator — first exact-head verification (2026-11-25)

- Source/test checkpoint: `835708e582513d73a7ec94ff632ffbdf93b77844`.
- Task Orchestrator Tests run `45486062484` passed: 414 tests, including the new project registry tests.
- Non-production PR Validation run `45486062444` passed.
- Agent PR Lease and Scope Guard run `45486062154` passed while the task lease was active.
- Project Memory Audit run `45486062165` was still running when this checkpoint was recorded; it must be checked on the final PR head after the memory-only follow-up commit.
- The first test attempt on earlier checkpoint `18ec9ae311e2057c50b75a4538a912b3d36dc3c7` exposed that the manifest schema also uses `date-time` format. The validator was corrected to support the schema's URI and RFC3339 date-time formats, and the later 414-test run passed.


## Phase 2B — explicit task project identity (2026-11-25; in progress)

- PR #99 merged successfully by Squash as `9b54a7158a1fbba7405f04ad503bcb8126c457bc`; Issue #98 closed as completed.
- Issue #100 is active under a verified ChatGPT lease. Current claim ID: `202611250550de39`; pinned base SHA: `9b54a7158a1fbba7405f04ad503bcb8126c457bc`. The lease is time-limited and must be renewed before expiry if work continues.
- PR #101 is Draft/open/unmerged: `https://github.com/majidbusy09-blip/jetconfig-vpn/pull/101`; branch `agent/project-identity-intake-v2-20261125`.
- Implemented on the branch: v2 task payload identity schema; explicit v1-only JET VPN compatibility identity; checked-in JET VPN manifest with lifecycle `registered`; manifest/live-repository validation in intake and lease/handoff paths; handoff schema v3; local task-record persistence of project identity plus pinned base SHA; base/head repository identity checks in PR guard; issue revalidation and patch-review gate identity checks.
- Scope intentionally excludes registry persistence, activation, context/envelope changes, lease namespace changes, workspace/cache/artifact namespacing, application source, external repositories, and production execution.
- First CI pass on an earlier PR #101 head found unconverted legacy consumers in patch review and test fixture mismatches. The PR guard passed. The affected patch-review gate/command and tests were updated. The final exact-head run on implementation commit `33357ea746d3e2a5147416a8da9385ee1002b340` subsequently passed all four required workflows; see the verification record below.
- The current JET VPN manifest remains `registered`; no project is activated. «حسابگر من» remains unregistered pending its exact GitHub repository URL.
- No merge, release, deployment, paid API, new provider spend, credentials, source transfer, or untrusted-code execution has been performed for Phase 2B.


### PR identity downgrade guard — Phase 2B extension

A review of the first v2 PR guard test exposed a downgrade gap: a project-bound v2 Issue could otherwise be edited to a legacy v1 body while an existing PR envelope and active lease remained. PR #101 now adds a separate PR authorization envelope v2 binding the exact Issue-body SHA-256, project identity tuple, and lease-pinned base SHA. V2 tasks require this envelope; legacy v1 tasks require PR envelope v1. The agent context/input envelope remains unchanged. Exact-head CI must be re-run after this addition.


### Exact-head verification record — 2026-11-25

Implementation head: `33357ea746d3e2a5147416a8da9385ee1002b340` (base `9b54a7158a1fbba7405f04ad503bcb8126c457bc`).

- Task Orchestrator Tests: **426 tests passed** — run `45534458358`.
- Non-production PR Validation: success — run `45534458288`.
- Agent PR Lease and Scope Guard: success — run `45534455835`.
- Project Memory Audit: success — run `45534458336`.

PR #101 remains Draft/open/unmerged and has no review submissions or review threads. GitHub reports it mergeable, but it is deliberately awaiting human review and separate merge approval. Latest verified lease claim is `202611250555cafe`, pinned to the main base SHA above, expiring at `2026-11-25T04:34:16Z`.


## Authoritative multi-project status — 2026-11-25

- Phase 2B PR #101 is merged as `a0046fd5d17c32293bef3f904adc2bda89cd48c5`. The final PR head `028e5aea501abde1ceb2ff3d84d91aae9423d162` passed 426 Task Orchestrator tests plus Non-production PR Validation, Project Memory Audit, and Agent PR Lease and Scope Guard.
- Issue #100 is completed and closed. Its task lease was released after merge.
- Phase 2C Issue #102 is active on branch `agent/project-memory-manifest-context-20261125`, base `a0046fd5d17c32293bef3f904adc2bda89cd48c5`. It removes the fixed six-document assumption for v2 project-aware context while preserving the explicit six-document JET VPN v1 compatibility path.
- حسابگر من repository has been independently identified read-only: `majidbusy09-blip/hesabgar_man`, immutable GitHub repository ID `1423683236`, default branch `main`, primary language Dart. Current `pubspec.yaml` reports version `1.0.9+10`. Its tracked tree contains Flutter application source, tests, assets, and a build workflow, but no project-memory documents were present at repository root in the inspected tree. It remains unregistered and inactive.
- No external repository was modified. No app source, registry persistence, project activation, release, deployment, provider spend, API key, credential, or untrusted-code execution was performed.


## Phase 2D-1 — project lease/workspace namespaces

Phase 2C is merged. Phase 2D-1 is active on branch `agent/project-scoped-lease-workspace-namespace-20261125`, claim `202611250335d2d1`, pinned to main `c145412206f62be0f08349d1530646dfb5a776da`. The implementation adds deterministic namespace derivation, lease schema v2 with project identity, project-specific lock refs/record paths, handoff verification/acceptance against the same namespace, and project-bound workspace IDs. Exact-head CI is pending. Local task-record/artifact/cache/source-index namespacing is deferred to Issue #106. حسابگر من remains unchanged and inactive.


## Phase 2D-1 update — PR guard included

The project-scoped lease resolver is now also wired into the trusted PR guard and patch-review authorization. V2 PR validation reads the project-specific lock ref and lease record and rejects a lease record whose full project binding differs from the current trusted Issue binding. Legacy v1 PR validation continues to read the original lock branch and file. Exact-head CI is pending on the latest branch revision.


## Current multi-project status — 2026-11-25

- PR #103 merged: manifest-selected project memory and v2 context/envelope binding.
- PR #107 merged: project-scoped lease refs/records and workspace IDs. Main SHA after merge: `dcf754ac5b22691687ebe0d9ec0f88623e4265b5`.
- PR #109 is Draft/open for Issue #106 (Phase 2D-2A). It introduces project-scoped local task records, context/handoff/agent-input metadata paths, project-aware metadata filtering/fingerprinting, ambiguity rejection, and project-specific local task branches. Legacy v1 JET VPN paths are preserved.
- The final verified PR #109 head is `7acce911e1fe5e61077bc77749d401cad9492f2d`. Exact-head checks passed: 448 Task Orchestrator tests (run `45551100959`), Non-production PR Validation (`45551100865`), Project Memory Audit (`45551100829`), and Agent PR Lease and Scope Guard (`45551097893`). PR #109 remains Draft/open for review and has not been merged.
- Issue #108 (Phase 2D-2B) remains queued until #106 is reviewed and merged.
- حسابگر من repository ID `1423683236` remains unregistered/inactive; no target-repository writes have been made.
- The workflow artifact-upload wildcard remains a known issue because `.github/workflows/**` is protected from this task; a separate reviewed task is required.


### Scandir iterator cleanup — PR #109

The project/repository task namespace scan now owns both `os.scandir` iterators through context managers. This closes directory handles even when symlink validation raises early. The 450-test run on the prior exact head passed but emitted ResourceWarning for these iterators; the cleanup follow-up requires a fresh exact-head CI run.


## Verified merges — 2026-11-25

- Phase 2D-2A PR #109 is merged as `30a665c29fe658b37139c8e232b2411f6e59305a`. Project-aware local task records, handoff/context/input paths, metadata filtering, and local task branches are now on `main`; v1 JET VPN paths remain preserved.
- حسابگر من target PR #2 is merged as `177eb1a1f0ae8ae5a77a2c1c136804dff042d5db`. Its dedicated Flutter 3.27.4 / Dart 3.6.2 workflow passed static analysis and 74 tests on the exact PR head. App version remains `1.0.9+10`.
- Central onboarding PR #111 was based on the pre-#109 main and became non-mergeable after #109 landed. Its onboarding changes are being rebased into a fresh PR; do not merge the stale branch.
- The resolved `pubspec.lock` was reviewed from CI artifact `14998203164` (101 packages, 23,577 bytes) but is not tracked on target `main`; reproducible dependency resolution remains open.
- حسابگر من remains `registered`, not active. Generic Dart source-index adapter is still required before source indexing can be enabled.
- Issue #108 is now unblocked by merged #109 and is the next implementation phase. Issue #110 remains separately gated on explicit approval for its protected workflow policy change.


## Phase 2D-2B — project artifact namespace implementation (2026-11-25)

- Issue #108 is claimed under the current lease and PR #113 contains the first implementation slice.
- Added a pure project artifact namespace helper bound to project ID, immutable repository ID, manifest digest, and pinned source revision. It preserves legacy v1 names and output paths.
- Patch artifact storage, provider-result ingestion, and patch-review authorization now accept/verify the same project namespace. Cross-project and stale-revision store reuse fails closed.
- Dart resolved-index and critical-path tooling now accept a trusted project manifest and exact source revision, validate the canonical manifest digest and checked-out GitHub origin, and write project/revision-scoped outputs.
- Workflow artifact-name helper and cache/audit path helpers are implemented. Actual workflow YAML wiring remains deferred because all workflow files are protected by the task protocol.
- PR #113 implements this phase; exact-head Python, Dart semantic tooling, validation, memory-audit, and lease/scope checks are required before merge. No patch is applied, no provider is called, and no untrusted code is executed.

- The fixture-only dispatch audit writer now stores v2 audit output under the project/manifest/source namespace and rejects unscoped output overrides; legacy v1 output behavior remains intact.


## Post-merge state — 2026-11-25

- Phase 2D-2B PR #113 is merged as `1a6911431c27523631c9b707a2ff74be06baf571`; exact-head Python, validation, semantic-index, critical-path, deterministic-generation, task-intelligence, lexical-index, and lease/scope checks passed.
- Issue #108 is closed as completed and its lease is verified released. Issue #114 tracks only the deferred workflow artifact upload-name wiring; it is deliberately unclaimed and has no `agent-task` label pending explicit protected-path approval.
- Phase 2D-2A PR #109, حسابگر من target PR #2, and central onboarding PR #112 are also merged. Stale PR #111 was closed without merging.
- حسابگر من remains `registered`, not active. Target memory/CI is on target `main`; `pubspec.lock` remains an uncommitted CI artifact and generic indexing has not yet been smoke-tested against the target checkout. App version remains `1.0.9+10`.


## Narrow workflow-path authorization — policy phase

- Repository owner approved a single future workflow path: `.github/workflows/project-memory-audit.yml`, bound to task ID `project-memory-artifact-workflow-v1`.
- The task intake and agent contract validators are being updated so only that exact task ID can authorize that exact path. All other `.github/workflows/**` paths remain protected, including `agent-lease-commands.yml`, build, release, and deployment workflows.
- This policy-only phase does not modify any workflow YAML. The actual project-memory audit workflow integration is a separate follow-up after this policy is merged and independently validated.


## Project-bound workflow artifact naming — implementation in progress

- The exact-path policy exception was merged in PR #116 as `53eaa1d989c1bc7227cc4f6d66602a4ed5d380dc`; it is bound only to task ID `project-memory-artifact-workflow-v1` and `.github/workflows/project-memory-audit.yml`.
- The workflow integration now resolves artifact names through a trusted manifest matcher and the exact checked-out `GITHUB_SHA`. If no manifest matches the live immutable repository identity, it retains the legacy names `jet-vpn-semantic-ast-index` and `jet-vpn-code-index`. A matching but invalid/ambiguous manifest or SHA drift fails closed.
- The integration changes only the approved project-memory audit workflow. Lease-command, build, release, and deployment workflows remain untouched.


## Workflow artifact integration — merged 2026-11-25

- Exact-path policy PR #116 merged as `53eaa1d989c1bc7227cc4f6d66602a4ed5d380dc`; the path exception is bound to task ID `project-memory-artifact-workflow-v1` and `.github/workflows/project-memory-audit.yml` only.
- Workflow integration PR #118 merged as `a79d556643ce4aad1dfa0ababb225258be4ac4c1`.
- Main-branch Project Memory Audit run `45589911286` passed. It resolved the trusted JET VPN manifest and generated v2 artifact names bound to repository ID `1349356614`, manifest SHA-256 `6fadf7b2cfe00303787285ab6b38db4de513642d3b9bf5f8d13c35403754aedc`, and source revision `a79d556643ce4aad1dfa0ababb225258be4ac4c1`.
- Main-branch artifact IDs: semantic AST `15010357716`; code index `15009809182`.
- The lease-command workflow and all build/release/deploy workflows remain unchanged.


## Hesabgar live onboarding reconciliation — 2026-11-26

- Central PR #147 fixed released-lease re-pinning under strict fail-closed rules and was squash-merged as `edc483089d6f124ae68ae7ac33a9a25f6c258f0d`. All four exact-head checks passed.
- Issue #105 now has a fresh verified lease pinned to that main SHA: claim `edc483089d6f124a`, lock commit `69e517244c2f4c6edf81d27efb907f21f0917912`. The handoff and local agent-input artifacts were prepared successfully; the workflow did not invoke a model or upload source.
- Live Hesabgar main is `11d44f24ad0cf2ba5ab9a278adeb532a35c677a6`, repository ID `1423683236`. All five required memory documents and `pubspec.lock` are tracked on that exact revision.
- Target validation run `45748004622` passed with Flutter 3.27.4 / Dart 3.6.2, static analysis, and 74 tests. Project-bound source-index generation and Task Intelligence smoke tests passed inside CI.
- Current readiness is `NEEDS_REVIEW`, with no hard blockers and one material runtime gate: central handoff still does not automatically provision/retrieve the exact project/revision-bound source index. Keep Hesabgar lifecycle `registered`, `source_index.strategy=none`, app version `1.0.9+10`; no app source was changed.
