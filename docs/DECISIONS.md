# JET VPN — Technical Decisions

This log records decisions that govern future work. New entries should include date, status, rationale, and consequences. Do not erase superseded decisions.

## D-001 — GitHub source is authoritative for Android client

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Use the current GitHub repository/branch/commit as source of truth for client code; old ZIP archives and chat snippets are historical context only.
- **Rationale:** The user may have newer local changes than old uploaded archives.
- **Consequence:** Fetch latest source and record SHA before each task.

## D-002 — Branch + diff + PR approval workflow

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Work on isolated branches, inspect diff and verification evidence, and request explicit approval before merge/release.
- **Rationale:** Real code changes are allowed but production actions must remain under user control.
- **Consequence:** Never merge or release autonomously.

## D-003 — Project memory is part of the deliverable

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Update source-grounded project documents whenever implementation changes affect architecture, APIs, data, payment, issues, tests, or workflow.
- **Rationale:** A future agent must be able to resume without depending on conversational memory.
- **Consequence:** Every material code PR should include appropriate memory updates.

## D-004 — Release workflow is a protected boundary

- **Date:** 2026-11-22
- **Status:** Accepted; remediation implemented in PR #5
- **Decision:** Production release is manual-only and fail-closed: `workflow_dispatch`, selected ref exactly `main`, and explicit `confirm_release=true`. The release job alone receives `contents: write`.
- **Rationale:** Prevent ordinary pushes and PR merges from unintentionally publishing signed production APKs.
- **Consequence:** Never dispatch a production release without explicit user approval. Current implementation is in `.github/workflows/build.yml` at main commit `f396f57459c9863a325f27e7d438e9456d560e92`.

## D-005 — API docs distinguish client observation from server truth

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Document request fields and response usage from Flutter source as client-observed only until backend source is reviewed.
- **Rationale:** Client behavior cannot prove authorization, validation, idempotency, or payment correctness on the server.
- **Consequence:** Use explicit server-unverified markers and do not make security claims about backend.

## D-006 — Every task must pass the collaborator-priority test

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Before prioritizing work, ask: «آیا این کار ما را به داشتن یک همکار برنامه‌نویس مستقل، دقیق و دارای حافظه پروژه نزدیک‌تر می‌کند؟» A negative answer means the work is not a priority unless explicitly requested.
- **Rationale:** Keep engineering effort focused on durable project understanding, implementation ability, verification, memory, and safe maintenance rather than unrelated activity.
- **Consequence:** Record the capability improved by each prioritized task; defer unrelated product features, marketing, visual changes, and refactors.


## D-007 — AST call-site map must not overclaim semantic resolution

- **Date:** 2026-11-22
- **Status:** Accepted; tooling merged in PR #16
- **Decision:** Introduce Dart Analyzer AST parsing in an isolated developer-tool package, but label the first call graph as syntactic and candidate-based until analyzer element resolution is implemented.
- **Rationale:** AST structure is more reliable than regex for declaration and invocation locations, but matching identifier names alone cannot prove which declaration a call binds to.
- **Consequence:** Keep ambiguous and unresolved calls explicit; never describe this first graph as a verified semantic call graph or runtime reachability map.


## D-008 — Multi-file analyzer index and curated critical-path report

- **Date:** 2026-11-22
- **Status:** Accepted; tooling merged in PR #16
- **Decision:** Resolve all tracked Dart source files under `lib/` as one application source set, fingerprint each file, and build cross-file edges from analyzer Elements. Define critical workflows through a source-path/owner/kind/name manifest and report static transitive reachability from those curated anchors.
- **Rationale:** A single-file graph cannot show cross-file impact once the app is split; explicit entrypoint anchors make impact analysis useful while remaining auditable.
- **Consequence:** Missing or ambiguous anchors fail closed and are reported. Static reachability is not runtime execution; callbacks, state-field dependencies, dynamic calls, and native Java behavior remain separate evidence boundaries.

## D-009 — Native VPN state is not live connection verification

- **Date:** 2026-11-22
- **Status:** Accepted; implementation merged in PR #16
- **Decision:** The UI may expose a connected state only when the native core reports CONNECTED, a live tunnel verification has succeeded, and no explicit UI-disconnect override is active. Cold restore and app resume must clear stale verification and require a fresh ping check before showing connected.
- **Rationale:** The native core can report CONNECTED before the data path is usable; retaining a stale verification flag or setting it from native state alone can produce a false-positive connected UI.
- **Consequence:** Failed silent verification must not stop the core or preserve a green/connected state. In smart mode, it falls back to the slow health watcher; device-level lifecycle and network tests remain necessary.


## D-010 — Sandbox signature trust is pinned outside the runtime trust domain

- **Date:** 2026-11-24
- **Status:** Accepted; policy adapter merged in PR #53.
- **Decision:** Trust-store bytes must be canonical and match a SHA-256 digest supplied by protected out-of-band configuration. A protected caller-supplied minimum version must be enforced monotonically. Only unique, active, in-window Ed25519 public keys are eligible; revoked, retired, unknown, expired, not-yet-valid, malformed, or algorithm-mismatched keys fail closed.
- **Rationale:** A provider or guest must not be able to nominate its own verification key or roll back to an older trust policy.
- **Consequence:** `sandbox_trust.py` validates the store and delegates Ed25519 verification to an injected audited backend. It does not persist rollback state, provision keys, or authorize execution. Production integration requires protected deployment of the pinned digest/version floor and an approved cryptographic backend.


## D-011 — Untrusted execution remains disabled until independent runtime acceptance

- **Date:** 2026-11-24
- **Status:** Accepted
- **Decision:** Passing trust-store parsing, signature verification, CI, or synthetic tests is not sufficient to authorize untrusted code execution. Execution remains disabled until an independently controlled host/guest probe suite, protected trust configuration, audited cryptographic backend, real candidate VM validation, and separate owner-approved policy gate all pass.
- **Rationale:** A signed report can still be false, incomplete, replayed, or generated by the same compromised runtime it purports to validate unless evidence is independently observed and trust roots are protected.
- **Consequence:** Keep execution_authorized and eligible_for_untrusted_execution false; no provider, VM, source transfer, key, spend, or untrusted execution without separate approval.

## D-012 — Use a narrow PyCA Ed25519 verification backend

- **Date:** 2026-11-24
- **Status:** Accepted for signature verification; supply-chain hardening remains open.
- **Decision:** Implement Ed25519 public-key verification through PyCA `cryptography` in `tools/task_orchestrator/ed25519_backend.py`; expose verification only and pin dependency versions in a dedicated requirements file.
- **Rationale:** The trust-store policy adapter previously delegated signature mathematics to an injected backend. A maintained cryptographic implementation is required to verify real signatures rather than relying on a test double.
- **Consequences:** RFC 8032 known-answer and integration tests are required. Current pins (`cryptography==50.0.2`, `cffi==2.1.1`, `pycparser==3.12`) are exact but not hash-locked; wheel hashes/provenance review remains outstanding. The adapter does not load private keys, sign, generate keys, establish the trust root, persist rollback state, or authorize untrusted execution. Keep `execution_authorized` and `eligible_for_untrusted_execution` false.

## D-013 — Trust configuration must be accepted through a protected host control plane

- **Date:** 2026-11-24
- **Status:** Design accepted; implementation and operational provider remain outstanding.
- **Decision:** Deliver trust-store bytes, their independent digest, a monotonic version floor, and a monotonic configuration epoch through a root-authenticated host control plane outside the provider and guest. Persist epoch/version with atomic compare-and-swap and an append-only audit record. Reject rollback, same-epoch content conflicts, audience mismatch, expired configuration, transaction failure, and unavailable/corrupt monotonic state.
- **Rationale:** `PinnedTrustStoreVerifier` validates supplied bytes and a caller-supplied floor, but it does not deliver the trust root or persist anti-rollback state. A local file, CI cache, guest variable, provider response, or repository artifact is not an independent durable trust anchor.
- **Consequences:** The contract is specified in `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`. A provider-neutral validator may be implemented and tested with fake interfaces, but it must not be labelled production anti-rollback until a real transactional store, root-key custody, workload identity, audit, recovery, and independent review are in place. No KMS/HSM account, key, provider, VM, spend, or untrusted execution is authorized.



## D-013 — Protected trust control plane design accepted (2026-11-24)

- Status: **design accepted; implementation pending**.
- PR #57 was squash-merged as `e28e16ba9b4021d3974085639df4c461774e8eaf` from final head `d60cf18554f37b0387bc6c5738edefdd2f04f602`.
- Final-head Task Orchestrator Tests `45358099449`, Project Memory Audit `45358099476`, and Non-production PR Validation `45358099550` all passed.
- The detailed contract is `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`: offline/out-of-band root trust; signed envelope with audience, schema, expiry, digest and monotonic epoch/version; atomic transactional compare-and-swap; fail-closed behavior; key rotation/revocation; append-only audit and recovery.
- This decision approves the architecture direction, not provisioning or operation. No root key, KMS/HSM, control-plane service, durable monotonic database, provider, VM, or untrusted execution is authorized.
- Implementation may begin with a provider-neutral validator and abstract monotonic-store interface. Fake signature verification and in-memory CAS are test fixtures only and must never be represented as production security.


## D-014 — Trust configuration acceptance remains reference-only (2026-11-24)

**Status:** Accepted; implementation boundary.

PR #59 adds a provider-neutral trust configuration acceptance module with strict envelope validation, injected root-signature verification, trust-store digest binding, and a monotonic-store Protocol. The Protocol contract requires durable atomic CAS and append-only audit in the same transaction.

This module is not production-ready and must not be described as an operational protected trust control plane. No production root key/verifier, durable monotonic persistence, transactional audit implementation, KMS/HSM, or service is provisioned. In-memory CAS and fake verifiers/backends exist only in tests.

**Consequences**
- The acceptance API may be used for deterministic reference behavior and tests only until real root trust and durable storage are separately implemented, reviewed, and provisioned.
- Any production adapter must prove atomic CAS plus append-only audit, crash consistency, rollback resistance, key lifecycle, and recovery behavior.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory. Passing module tests cannot enable untrusted execution.


## D-015 — Host evidence assembly is a non-production contract (2026-11-24)

**Status:** Accepted for deterministic evidence validation only; operational runtime implementation pending.

PR #68 adds `tools/task_orchestrator/sandbox_host_evidence.py` and its tests. The collector binds each observation to a pinned attempt, runtime ID and policy digest; requires the observer domains declared by the 20-probe manifest; validates caller-configured observer IDs, UTC freshness, monotonic offsets and payload bounds; rejects missing/duplicate/untrusted observations; and produces deterministic evidence bytes with host-recomputed payload digests.

**Limits and consequences**
- The collector does not execute probes, start processes, provision or inspect VMs, perform network requests, collect guest files, authenticate observer identities cryptographically, sign reports, or authorize code execution.
- Observer identity configuration must eventually be provisioned and rotated through a protected out-of-band trust mechanism. Test identities are fixtures only.
- A successful unit test or assembled evidence bundle is not proof of isolation and cannot authorize untrusted execution.
- Next work may implement a fixed host-controller adapter/lifecycle contract with fake observers only, plus a separately designed external-canary trust boundary. Real runtime/provider provisioning and spend require separate approval.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-016 — Host lifecycle state machine remains a pure contract (2026-11-24)

**Status:** Accepted as deterministic event-order validation only.

PR #70 adds `tools/task_orchestrator/sandbox_host_lifecycle.py`. The state machine binds events to a pinned attempt/runtime/policy tuple and monotonic start/deadline, enforces allowlisted transitions, and requires explicit termination and cleanup confirmation after both passing and rejected evidence outcomes. Cancellation, timeout, adapter failure, and cleanup failure are represented as distinct bounded failure states.

It does not invoke a runtime adapter or independently observe host state. It cannot prove process termination, resource cleanup, timeout enforcement, or VM isolation. Those remain responsibilities of a future independently reviewed host implementation.

**Consequences**
- Tests may exercise the transition contract with deterministic events only.
- No task-supplied commands, dynamic probe code, process execution, VM/provider integration, or external service is authorized.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-017 — Artifact collection starts as a pure in-memory validator (2026-11-24)

**Status:** Accepted for deterministic candidate validation only.

PR #72 adds `tools/task_orchestrator/sandbox_artifacts.py`. It validates caller-supplied candidate bytes and metadata, restricts logical paths to normalized relative `artifacts/` and `reports/` roots, rejects unsafe path forms and declared non-regular/symlink/hard-link candidates, bounds inventory count and bytes, recomputes SHA-256, binds a deterministic manifest to attempt/runtime/policy/evidence/report digests, and records bounded retention metadata.

**Limits and consequences**
- Candidate `kind`, `symlink_target`, and `link_count` values are caller assertions; the module does not open or inspect filesystem objects and cannot prove those claims.
- Report digest binding is not signature verification. The signed-report verifier and protected trust configuration remain separate.
- Retention is metadata only; there is no storage backend, deletion, quota enforcement, or crash recovery.
- A future trusted host collector must use descriptor-relative no-follow traversal, `fstat`, same-descriptor reads/hashing, TOCTOU defenses, and independently verified acceptance-report/evidence bindings.
- Artifacts remain quarantined and non-executable; this contract does not apply patches or change execution authorization.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-018 — Authenticate observer envelopes before evidence assembly (2026-11-24)

**Status:** Accepted as a verification contract only; protected provisioning, transport, durable replay state, and report integration remain pending.

PR #74 adds `tools/task_orchestrator/sandbox_observer_auth.py`. It validates a canonical signed observer envelope against an externally pinned observer registry, maps observer ID to exactly one trust domain and key ID, binds the envelope to a short-lived host challenge (audience, observer, attempt, runtime, policy digest, and acceptance-suite probe), verifies payload digest and Ed25519 signature through an injected verifier, and asks an injected replay store to atomically consume the nonce and advance the per-observer sequence.

Successful verification returns `AuthenticatedObserverResult` with a `ProbeObservation` and audit bindings (registry digest/version, key ID, sequence, nonce digest, envelope digest).

**Limits and consequences**
- The registry digest/version/audience must be delivered by the protected root-signed trust configuration process; this module only checks the supplied pin.
- Production must use the existing pinned Ed25519 trust-store verifier with aligned trusted time. Fake verifiers are test fixtures.
- The replay-store interface requires durable atomic nonce/sequence state, but only an in-memory fake exists. No production replay persistence or recovery is implemented.
- No host challenge generator, authenticated transport, identity provisioning/rotation service, probe execution, or VM adapter is implemented.
- The current evidence bundle does not carry the authenticated envelope provenance. Signed-report integration must bind it explicitly with the assembled evidence digest.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-019 — Bind observer provenance in a separate signed acceptance schema v2 (2026-11-24)

**Status:** Accepted as a verification contract; report signing, raw-envelope retention, durable replay, and transport remain pending.

PR #76 adds `sandbox_acceptance_provenance.py` with a schema-v2 verifier while leaving the v1 verifier unchanged. V2 pins runtime ID and observer registry digest/version, signs a sorted observer provenance inventory, recomputes provenance and raw probe evidence digests, derives required observer domains from the probe manifest, and cross-checks each record against observer ID/domain and exact payload SHA-256 in the raw evidence.

**Trust model**
- The acceptance-suite signing key is the authority attesting that the host verifier already authenticated observer envelopes.
- The v2 verifier does not independently verify each observer signature; it binds the exact envelope digest and metadata in the signed report. Preserve raw signed envelope bytes in a separately protected artifact set if later re-verification is required.
- V1 remains valid for legacy evidence but is not observer-authenticated. Consumers that require observer authenticity must explicitly require schema v2 and must not silently downgrade.
- The v2 verifier does not sign reports, create private keys, run probes, authorize patch application, or enable untrusted execution.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## D-020 — Durable observer replay storage requires atomic audit and anti-rollback (2026-11-24)

**Status:** Design accepted; no production storage implementation.

PR #78 expands the replay-store protocol to receive all security/audit context and adds `docs/SANDBOX_REPLAY_STORE_DESIGN.md`. A production implementation must atomically consume the nonce, advance the per-observer sequence, persist the envelope digest and context, and append the audit event in one serializable transaction.

**Required controls**
- Unique nonce digest and envelope digest; unique `(observer_id, sequence)`; compare-and-swap sequence advancement.
- Stable observer ID across key rotation so sequence continuity cannot reset with a new key ID.
- Single-writer fencing token and an external protected high-water checkpoint to reject stale backup restores.
- Nonce tombstone retention through challenge expiry plus allowed skew; sequence high-water state survives key rotation and audit cleanup.
- Fail closed on DB outage, replication lag, split-brain, uncertain commit, corruption, audit failure, or rollback. No in-memory fallback.
- Keep raw signed envelopes in a separate protected artifact store; the replay ledger stores digests and audit context only.
- Current implementation remains an interface plus in-memory test fake. Production database/service requires separate trust-boundary review and explicit approval.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-021 — Retain exact observer envelopes in a two-phase protected artifact chain (2026-11-24)

**Status:** Design accepted; no storage implementation.

PR #80 adds `docs/SANDBOX_OBSERVER_ENVELOPE_RETENTION.md`. Exact original signed envelope bytes must be staged before report signing in a host-only content-addressed store. A deterministic staging manifest records path, size, envelope digest, observer/domain/key, attempt/runtime/policy/probe, registry digest/version, sequence, nonce digest, challenge expiry, and trusted acceptance time.

The next acceptance-report schema should bind the staging-manifest digest. After the report is signed and verified, the final post-acceptance artifact manifest binds retained envelope artifacts to the report digest. This avoids circular dependencies.

**Limits**
- Schema v2 remains unchanged and does not bind a staging-manifest digest or carry raw envelope bytes.
- Raw envelopes must be preserved exactly; do not reserialize before hashing or signature re-verification.
- Storage requires a trusted host implementation with descriptor-relative no-follow traversal, same-descriptor hashing, path derivation, size/count limits, quarantine, retention, and crash-safe cleanup.
- No filesystem collector or storage backend exists. The artifact collector remains a pure in-memory validator.
- `execution_authorized: false` and `eligible_for_untrusted_execution: false` remain mandatory.


## D-022 — Acceptance report signing must revalidate observer evidence and replay receipts (2026-11-24)

**Status:** Design accepted; no signer implementation or key provisioning.

PR #82 adds `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md`. A report signer must not treat a caller-created `AuthenticatedObserverResult` as proof. It must independently verify exact raw envelope bytes and Ed25519 signatures, match every record to a read-only trusted replay-acceptance receipt, cross-bind raw probe evidence and the pre-acceptance envelope staging manifest, and produce deterministic canonical report bytes.

The next schema is v3 because it must bind `observer_envelope_manifest_sha256`. Schema v1/v2 remain unchanged. A successful report must be independently verified after signing before it is accepted.

Tests may use fake signers and in-memory replay receipts only. No private key, signing service, durable replay DB, filesystem collector, network, VM, provider or untrusted execution is authorized. Keep both execution flags false.


## D-022 implementation status update — PR #82 merged (2026-11-24)

- The trusted report signer design is recorded in `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md`.
- Current implementation remains verifier-only for v1/v2. There is no report builder/signer, schema-v3 verifier, private key, signing service, replay receipt reader, or production ledger.
- Next code work is the read-only replay acceptance receipt protocol and in-memory fake, followed by a pure schema-v3 builder and injected fake signer/verifier. Any real signing backend or durable replay store requires separate trust-boundary review and explicit approval.


## D-023 — Break report-signing authorization into pre-sign verification and post-sign verification (2026-11-24)

**Status:** Implemented as a non-production adapter contract in PR #88; production deployment not approved.

A report signer cannot require an authorization attestation that is issued only after the final report signature is verified; that creates a circular dependency. Use two independent verification stages instead:

1. The independent verifier reconstructs and validates the exact unsigned schema-v3 report, probe evidence, raw observer envelopes, pinned observer signatures, replay receipts, and envelope manifest.
2. Only after successful content verification, the verifier issues a short-lived signed attestation binding its pinned identity/key, signer audience, exact report and manifest SHA-256 digests, unique verification ID, issue/expiry, and algorithm.
3. The trusted signer verifies the attestation and exact bytes, atomically consumes the one-time authorization ID, and signs through a separately protected backend.
4. An independent post-sign verifier reconstructs the content again and verifies the final report signature.

The verifier-attestation key and report-signing key must be distinct. The authorization ledger must be durable, atomic, anti-replay, and fail closed in production. Test fakes and injected interfaces do not satisfy those operational requirements. This flow does not authorize execution; preserve all execution flags as false.


## D-024 — Multi-project registry identity must be explicit and immutable (2026-11-25)

**Status:** Accepted architecture; registry implementation in progress.

Every managed project is identified by a stable JET AI `project_id` bound to GitHub's immutable numeric repository ID. Canonical owner/name, HTTPS URL, and configured default branch are checked against trusted live repository metadata before consequential operations. Duplicate project IDs and repository IDs remain reserved even for retired entries; repository renames require an explicit audited migration.

Project manifests are declarative data and cannot weaken global safety policy. A project may be eligible for implementation only when its lifecycle is explicitly `active`. Required verification profiles must both be declared by the project and have an implemented fixed runner. An unknown profile blocks readiness; it is never silently replaced by an unrelated check.

The first implementation phase is a pure validator with no network, filesystem persistence, subprocess, GitHub mutation, model/provider call, or project-code execution. Task/envelope/lease/context/workspace/cache/artifact identity propagation is separate follow-up work. «حسابگر من» is not registered until its exact repository URL and immutable repository identity are independently verified.


## D-025 — Versioned task project binding and bounded legacy migration (2026-11-25)

**Status:** Implemented on Draft PR #101; not yet merged.

New project-aware task payloads use schema v2 and carry exactly six identity fields: stable `project_id`, immutable numeric `repository_id`, canonical `repository_full_name`, configured `default_branch`, `manifest_schema_version`, and canonical `manifest_sha256`. The binding must match a trusted checked-in manifest and live GitHub repository metadata before intake artifacts or handoffs are accepted. PR guards must compare the same repository identity tuple for both base and head repositories.

Legacy v1 is a migration exception for the original JET VPN repository only: repository ID `1349356614`, canonical name `majidbusy09-blip/jetconfig-vpn`, HTTPS URL `https://github.com/majidbusy09-blip/jetconfig-vpn`, and default branch `main`. All v1 acceptance paths must validate trusted repository metadata; a missing identity must fail closed. No project may be inferred from task text, title, branch, or display name.

V2 handoffs use handoff schema 3. The validated project binding is persisted in the local task record together with the lease-pinned `base_sha`. A later repository rename or manifest digest change cannot silently rebind an existing task; the old handoff must be rejected and an explicit migration/new task used.

The JET VPN manifest remains lifecycle `registered`. This phase does not activate it or persist a multi-project registry. V2 implementation intake requires an active manifest and implemented fixed verification profiles; v1 compatibility remains the temporary path for current JET VPN work. Context/envelope schema, lease namespace, workspace/cache/artifact namespacing, and external-project onboarding are explicitly deferred.


### D-025 clarification — separate PR authorization envelope v2

The PR authorization envelope is a distinct control-plane record, not the agent context/input envelope. V2 tasks must use PR envelope v2 with the exact current Issue-body SHA-256, validated project binding, and lease-pinned base SHA. Legacy v1 tasks must use PR envelope v1. The guard rejects version downgrade and any digest/binding/base mismatch. The agent context/input envelope remains unchanged in Phase 2B.


## D-026 — Manifest-selected project context (2026-11-25)

**Status:** Implemented on Phase 2C branch; awaiting exact-head verification and review.

For v2 project-aware tasks, the trusted checked-in project manifest is the only source of the required project-memory document set. The context package and agent envelope must carry the same validated project binding, manifest digest, memory-manifest version, exact ordered required-document list, and pinned base SHA. The verifier rejects drift between the persisted task record, context package, and envelope. Legacy v1 remains an explicit compatibility path for the original JET VPN repository and its exact six-document set only. No task text or repository display name may select a project or memory manifest.
