# JET VPN — Prioritized Next Steps

## Verified baseline — 2026-11-24

- Current `main`: `3e613a8c03a39e4440c3702ac3505acb7b2eae27` (PR #53 merged).
- PR #20, PRs #38–#44, and PRs #46–#53 are merged.
- PR #49 Task Orchestrator Tests #45320041554 passed 259 tests, Project Memory Audit #45320041561 passed, and Agent PR Lease and Scope Guard #45320038880 passed.
- PR #50 validation completed successfully. PR #51 all four checks passed: Task Orchestrator Tests #45325193322, Project Memory Audit #45325193253, Agent PR Lease and Scope Guard #45325195790, and Non-production PR Validation #45325193266.
- App source/version remain unchanged: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; version `2.4.5+284`.
- Validated handoff remains: task envelope → fixture dispatch → local result ingestion → content-addressed patch → live Issue/lease review gate → `ready_for_human_review`, `applied: false`.

## P0 — Build the actual independent runtime probe suite

The signed-evidence verifier was introduced in PR #49 and hardened in PR #51. It validates canonical signed reports, exact 20-probe inventory, and raw evidence bytes by recomputing SHA-256; it still does not execute probes, provision a VM, establish a production trust root, or authorize code.

1. Implement a fixed guest-side probe runner and an independent external canary controller. Provider SDK status and provider-generated JSON must never count as independent test evidence.
2. Make probe outputs bounded and deterministic; PR #51 now requires exact raw evidence bytes, recomputes each digest, and rejects missing, extra, empty, altered, and oversized evidence.
3. Cover VM/kernel separation, non-root/capabilities, Seccomp negative tests, enforced cgroup CPU/memory/PID limits, disk quota, read-only source/scratch, secret/socket/device/metadata absence, IPv4/IPv6, DNS, QUIC, external canary, timeout, process-tree kill, artifact integrity, cleanup on success/failure/timeout, and cross-attempt residue.
4. Define the trust-root lifecycle before selecting crypto packaging: out-of-band public-key pinning, key IDs, activation/expiry, rotation, revocation, rollback protection, signer access policy, audit trail, and disaster recovery. Then add an audited Ed25519 implementation using an explicitly approved dependency; never create or commit a private key, and never place signing material in the provider or guest.
5. Run the suite against the exact provider, region, VM image, and policy intended for a pilot; preserve signed report and raw evidence.
6. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false` until a real independent suite, external signer, pinned trust root, candidate runtime validation, and separate owner-approved policy gate exist.

## P0a — Complete protected trust-root integration

PR #53 implements policy validation, not production cryptography. Next safe work:

1. Inspect existing Python/tooling dependency policy and workflow pinning. Compare maintained Ed25519 libraries, security history, reproducible installation, and transitive risk; do not add a dependency before review.
2. Design a protected control plane supplying trust-store bytes, an independently pinned SHA-256 digest, and a monotonic minimum version. Specify atomic update, rollback prevention, revocation, audit, and recovery. Never persist the version floor in the guest/provider.
3. After dependency approval, implement a narrow Ed25519 adapter with known-answer, tamper, and invalid-signature tests. No private key is created or committed.
4. Keep execution authorization false; trust-store validation alone is not runtime acceptance.

## P0b — Independent runtime acceptance suite

1. Specify the 20 probes as host-observable assertions with bounded evidence and explicit failure semantics.
2. Implement a fixed guest probe runner plus an independent host controller/canary. Provider status and guest-generated claims alone are not independent evidence.
3. Cover VM/kernel boundary, privilege/capabilities, Seccomp, enforced CPU/memory/PID/disk limits, read-only mounts, secrets/sockets/devices/metadata, IPv4/IPv6, DNS/QUIC/egress, timeout/process-tree kill, artifact integrity, cleanup, and cross-attempt residue.
4. Test against deterministic fake runtimes first; real VM validation requires separate account, consent, data-governance, and cost approval.
5. Bind exact raw evidence to the signed report and trusted key identity. Do not authorize execution from provider assertions or unit tests alone.

## P1 — Provider and data-governance decision

- E2B remains blocked by prior-written-consent requirement before testing and EU workspace payment-method verification.
- Daytona's strict sandbox-level `networkBlockAll` is tier-gated; documented Tier 3 requires a $500 top-up.
- Do not create accounts, add payment methods, provision sandboxes, upload source, or spend without separate approval.
- Evaluate alternatives against VM boundary, network controls, limits, lifecycle, region, retention, DPA, signature trust, and audit requirements.

## P2 — Complete multi-agent implementation integration

- Connect a sandbox broker to task leases and the existing dispatcher only after the external suite, signature trust root, and actual runtime pass acceptance.
- Keep model API credentials in the provider control plane, never in the code-execution guest.
- Keep patch application separate, human-reviewed, and disabled until its own scope/rollback/recovery gates are implemented.
- Add task status reporting that distinguishes planning, dispatch, execution, ingestion, validation, review, and rejection.

## P3 — Cross-repository project memory

- Perform read-only architecture/workflow inventories of `jetconfig-vpn-tv` and `hesabgar_man`.
- Add repository-specific instructions and a shared project map only after verifying each repository's current source.

## Deferred

- Live model calls, API keys, paid services, vendor accounts, sandbox provisioning, private-source transfer, signing keys, and provider spend: separate approval required.
- Production release, deployment, signing, app version changes, bot/payment/backend/server changes: separate explicit approval required.

## Verified baseline update — PR #55 merged (2026-11-24)

This update supersedes the PR #53 baseline above.

- Main includes PR #55 squash merge `3cc2e200dd02416d7b2fba02725b6734dffede39`.
- PR #55 final head `56e48fac7e5cfdf25c07492daef9ed3cdd3c0805` passed Task Orchestrator Tests (`45354914545`), Project Memory Audit (`45354914553`), and Non-production PR Validation (`45354914620`).
- A real PyCA Ed25519 public-key verification backend now exists and is integrated with the pinned trust-store verifier. It does not provide trust-root deployment or execution authorization.
- Dependency pins are exact versions but not hash-locked. Review wheel hashes/provenance and supply-chain reproducibility before treating installation as fully reproducible.

## Reprioritized next work

1. **Protected trust-configuration control plane:** define how trust-store bytes, independently pinned digest, and monotonic minimum version are delivered from protected out-of-band configuration; implement atomic updates, persistent rollback prevention, revocation/rotation, audit, and recovery. Keep this outside the guest/provider.
2. **Independent 20-probe runtime acceptance suite:** implement a fixed guest probe runner plus independent host controller and external canary. Validate the exact VM/kernel, Seccomp, cgroup CPU/memory/PID, disk, read-only source, secrets/sockets/devices/metadata, IPv4/IPv6, DNS/QUIC/egress, timeout/kill, artifact integrity, cleanup, and cross-attempt residue requirements.
3. **Dependency supply-chain hardening:** review PyPI wheel hashes/provenance and add a reproducible hash-locked dependency set where supported; document any transitive package for which provenance cannot be verified.
4. **Only after independent evidence and separate approval:** assess a real VM/provider pilot. No account, payment method, provider, private-source transfer, API key, VM provisioning, or spend without separate approval.

Do not connect live model providers or execute untrusted code at this stage. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`. GitHub-hosted runners and the benign Bubblewrap self-test are not an accepted untrusted-code sandbox.

## Current authoritative baseline — PR #56 merged (2026-11-24)

- PR #55 implementation merge: `3cc2e200dd02416d7b2fba02725b6734dffede39`.
- PR #56 project-memory refresh merge: `5354ba7c38d1b27ff75ace2ed288feb50551d701`.
- PR #56 final head `e07b35b4ccde0b78c50bf3bada16b1ad1ca9bf3f` passed Project Memory Audit run `45356110882` and Non-production PR Validation run `45356110761`; both concluded success.
- PR #55's PyCA Ed25519 backend is present. Its version pins remain not hash-locked.
- This document's older baseline entries above are historical; use this section and the current main commit as the latest state.

## Next engineering sequence

1. **Provider-neutral protected trust-config acceptance module:** implement strict signed-envelope validation, exact audience/expiry/digest checks, and a monotonic-state-store protocol. Unit tests may use deterministic fake root verification and an in-memory compare-and-swap store only. The module must expose no fake production persistence and must fail closed when the store is unavailable.
2. **Independent 20-probe runtime suite:** implement the fixed probe runner and host controller as separate trust domains. The existing `sandbox_acceptance.py` is only a report verifier; it is not the runner or runtime evidence.
3. **Supply-chain hardening:** investigate reproducible wheel hashes/provenance for the PyCA dependency set.
4. **Operational design review:** choose a KMS/HSM, workload identity, transactional monotonic store, audit/recovery and region only after a separately approved vendor/cost/data-governance decision.
5. **Real runtime pilot:** only after separate owner approval for account, consent, VM provisioning, data transfer, provider and spend, and after independent acceptance of the exact runtime.

The detailed trust configuration contract is `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`. No provider, KMS/HSM, signing key, API key, VM, private-source transfer, spend, or untrusted execution is authorized. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.




## Current authoritative baseline — PR #57 merged (2026-11-24)

- PR #57 final head `d60cf18554f37b0387bc6c5738edefdd2f04f602` passed Task Orchestrator Tests `45358099449`, Project Memory Audit `45358099476`, and Non-production PR Validation `45358099550`; all three runs concluded success.
- PR #57 squash merge commit: `e28e16ba9b4021d3974085639df4c461774e8eaf`.
- The protected trust-control-plane contract is now documented in `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md` and decision D-013. It is not an implementation and creates no production trust root or durable anti-rollback store.

## Next implementation sequence

1. **Provider-neutral trust-config acceptance module:** strict canonical signed-envelope parsing; duplicate-key rejection; schema/audience/time/epoch/version/digest validation; injected root-signature verifier; `PinnedTrustStoreVerifier` integration; abstract monotonic store with atomic CAS; append-only audit contract; return accepted config only after durable commit. Fail closed on invalid signatures, rollback, conflicts, unavailable/corrupt store, CAS races, or audit failure.
2. **Tests only with explicit fakes:** deterministic fake root verifier and in-memory CAS store for unit tests. Label them test-only; never call them production persistence or anti-rollback. Cover idempotency, same-epoch conflict, concurrency, malformed/canonical JSON, expiry, audience, digest, rollback, rotation/revocation, store/audit failures, and no provider/guest access.
3. **Independent 20-probe runtime acceptance suite:** fixed guest runner plus independent host controller and external canary. Do not run untrusted code on GitHub-hosted runners or treat Bubblewrap self-test as proof.
4. **Supply-chain hardening:** review PyCA wheel hashes/provenance and reproducibility.
5. **Separate approval gates:** KMS/HSM, workload identity, transactional store, VM/provider, private-source transfer, API keys, external spend and any untrusted execution require explicit separate approval.

Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Next steps after PR #59 — trust acceptance and sandbox evidence

1. **Refresh project memory after PR #59** (this PR): synchronize the authoritative snapshot and explicitly preserve the non-production boundary.
2. **Independent runtime acceptance suite:** design and test a harmless 20-probe host/guest evidence collection architecture. Keep the runner and host controller independently controlled; include an external egress canary. Do not execute untrusted source.
3. **Runtime probe coverage:** VM/kernel boundary; Seccomp; cgroup CPU/memory/PID caps; disk quotas; read-only source; secrets/socket/device isolation; cloud metadata blocking; IPv4/IPv6; DNS/QUIC/egress; timeout and process-tree kill; artifact integrity; cleanup and cross-attempt residue.
4. **Supply-chain hardening:** add hash-locked wheel requirements and provenance verification for `cryptography`, `cffi`, and `pycparser`; verify binary-wheel installation reproducibility and document any provenance gaps.
5. **Production trust control plane remains blocked:** separately design/provision an offline root trust ceremony, audited root verifier, durable transactional monotonic CAS plus append-only audit, key rotation/revocation, recovery, and independent security review.
6. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`. No paid provider, VM, KMS/HSM, API key, private-source transfer, or untrusted execution without separate explicit approval.


## Current next steps after PR #68 (supersedes older sequencing above)

1. **Host-controller lifecycle contract, fake-only:** define immutable run context, fixed allowlisted probe IDs, bounded observer adapter interfaces, monotonic deadline handling, cancellation/cleanup states, and deterministic failure transitions. Do not accept task-supplied shell commands or dynamic probe code.
2. **Evidence authenticity design:** specify out-of-band observer identity provisioning/rotation and authenticated host-to-canary evidence transport. The current collector validates IDs against caller-supplied allowlists but does not authenticate them.
3. **Evidence/report integration tests:** connect assembled raw evidence to the existing signed-report verifier using fake signature backends only; preserve attempt/runtime/policy binding and ensure the result never changes execution flags.
4. **Artifact collector contract:** design path allowlisting, symlink/device rejection, size limits, host-side digest recomputation, and bounded retention; tests use in-memory fixtures only.
5. **Independent threat-model review:** examine host/guest/canary separation, provider metadata, IPv4/IPv6/DNS/QUIC egress, resource enforcement, timeout/kill, cleanup, and cross-attempt residue.
6. **Supply-chain:** preserve SHA-256 hash-locked binary-wheel installation; review provenance and reproducibility for all pinned dependencies.
7. **Operational pilot remains gated:** a real VM/provider, account, API key, private-source transfer, KMS/HSM, paid service, or spend requires separate explicit approval and independent security review.

The host evidence collector is not a runner and no runtime probes have been executed. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #70 (2026-11-24)

1. **Host adapter interface design:** define fixed typed operations for creating a runtime, starting observations, requesting termination, confirming process-tree exit, and confirming resource cleanup. Keep all implementations fake-only; no dynamic commands.
2. **External observer authenticity:** specify out-of-band identity provisioning/rotation and authenticated host-to-canary evidence transport; the evidence collector currently checks IDs against caller-supplied allowlists only.
3. **Artifact collector contract:** define path allowlisting, symlink/device rejection, size ceilings, host-side digest recomputation, bounded retention, and evidence binding.
4. **Signed report integration:** connect assembled evidence to the existing report verifier with fake signature backends only; preserve false execution flags.
5. **Threat-model review:** cancellation races, host-monotonic timeout enforcement, kill escalation, cleanup retry/crash recovery, canary separation, IPv4/IPv6/DNS/QUIC egress and resource caps.
6. **Operational gates:** real VM/provider, API keys, private-source transfer, KMS/HSM, paid services and spend require separate explicit approval and independent security review.

PR #70 is a state-machine contract only; it does not implement any of the host adapter operations. No runtime probes have been executed. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #72 (2026-11-24)

1. **External observer authenticity:** design out-of-band host/guest/canary identity provisioning and rotation, authenticated transport, anti-replay, and trust-root binding. The existing evidence collector only checks IDs against caller-supplied allowlists.
2. **Signed report integration:** define a strict manifest/evidence/report relationship. Decide how artifact manifest digest and artifact bytes are cryptographically bound into a signed acceptance report; use fake signature backends and deterministic fixtures only.
3. **Host adapter interface:** specify fixed typed operations for runtime preparation, observation start, termination request, process-tree exit confirmation, and cleanup confirmation. Keep adapters fake-only; no dynamic shell commands or live runtime.
4. **Trusted filesystem collector design:** translate the pure artifact candidate contract into a separately reviewed host implementation using descriptor-relative no-follow traversal, `fstat`, same-descriptor read/hash, TOCTOU defenses, file identity checks, quotas, retention, and crash-safe cleanup. Do not implement actual filesystem collection until its host trust boundary is independently reviewed.
5. **Threat-model review:** cancellation races, monotonic deadline enforcement, kill escalation, cleanup retry/crash recovery, external-canary separation, IPv4/IPv6/DNS/QUIC egress, resource caps, and cross-attempt residue.
6. **Supply-chain hardening:** review provenance and reproducibility for pinned cryptography/cffi/pycparser wheels; add hash-locks where supported without introducing unapproved dependencies.
7. **Operational gates remain closed:** any VM/provider, account, API key, private-source transfer, KMS/HSM, paid service, or spend requires separate explicit approval and independent security review.

PR #72 completes only the in-memory artifact validation contract. It does not collect filesystem objects, verify report signatures, enforce retention, run probes, or prove sandbox isolation. No runtime probes have been executed. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #74 (2026-11-24)

1. **Signed acceptance-report integration:** extend the signed report schema to bind the exact observer-envelope digests, observer registry digest/version, key IDs, sequence numbers, nonce digests, and assembled evidence digest. Verify the relationship using fake signature backends only; do not let a caller-supplied `AuthenticatedObserverResult` become a trust root.
2. **Replay-store design:** specify a durable transactional implementation that atomically consumes nonces, advances per-observer sequences, stores envelope digests, and survives restart/failover/backup restore without rollback. Keep implementation fake-only until a separately reviewed trust boundary and service are approved.
3. **Host challenge and transport design:** specify CSPRNG nonce generation, challenge issuance/expiry, authenticated host-to-observer transport, mutual TLS/workload identity, canary separation, and retry behavior after crash or lost response. No live network code yet.
4. **Out-of-band identity lifecycle:** define registry signing/pinning through the protected trust control plane, key rotation overlap, emergency revocation, cache TTL, audit, and recovery.
5. **Trusted filesystem collector:** design descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, file identity checks, quotas, retention, and crash-safe cleanup. Current artifact collector remains an in-memory validator only.
6. **Threat-model review:** cancellation races, monotonic deadline enforcement, kill escalation, cleanup retry/crash recovery, external-canary independence, IPv4/IPv6/DNS/QUIC egress, resource caps, and cross-attempt residue.
7. **Operational gates remain closed:** any VM/provider, account, API key, private-source transfer, KMS/HSM, paid service, or spend requires separate explicit approval and independent security review.

PR #74 authenticates candidate observer envelopes only when supplied with externally pinned registry data, a trusted signature verifier, and an atomic replay-store implementation. Only fake verifier/replay-store implementations are tested. It does not issue challenges, authenticate network transport, persist replay state, execute probes, or bind provenance into the final signed report. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #76 (2026-11-24)

1. **Durable replay-store design:** define the atomic transaction for nonce consumption, sequence advancement, envelope digest persistence, and crash/failover recovery. Include backup restore anti-rollback, concurrent observers, idempotency, audit, retention, and corruption fail-closed behavior. Keep implementation fake-only until a trusted persistence boundary is approved.
2. **Raw observer-envelope retention:** define protected storage and manifest binding for exact signed envelope bytes referenced by v2 digests; include bounded paths/sizes, access controls, retention, and independent re-verification.
3. **Report signer contract:** specify how a trusted acceptance-suite signer consumes only verified `AuthenticatedObserverResult` values and emits schema v2. No private signing key or signing service until separately approved.
4. **Host challenge and transport design:** specify CSPRNG nonce generation, challenge issuance/expiry, authenticated host-to-observer transport, mutual TLS/workload identity, canary separation, and retry behavior after crash/lost response. No live network code yet.
5. **Protected identity lifecycle:** define registry signing/pinning, key rotation overlap, emergency revocation, cache TTL, audit, and recovery through the protected trust control plane.
6. **Trusted filesystem collector:** design descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, file identity checks, quotas, retention, and crash-safe cleanup. Current artifact collector remains an in-memory validator only.
7. **Threat-model review and operational gates:** cancellation races, deadlines, kill escalation, cleanup recovery, external-canary independence, IPv4/IPv6/DNS/QUIC egress, resource caps, and cross-attempt residue. VM/provider, API key, private-source transfer, KMS/HSM, paid service, or spend still require separate explicit approval.

PR #76 verifies a signed schema-v2 report and cross-binds observer provenance to raw probe evidence, but does not sign reports, persist replay state, retain raw envelopes, or execute probes. V1 remains unchanged and must not be treated as observer-authenticated. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #78 (2026-11-24)

1. **Protected raw observer-envelope retention:** define exact-byte storage for signed envelopes referenced by v2 digests; bind artifact paths, size limits, registry version, attempt/runtime/policy, access controls, retention, and independent re-verification.
2. **Trusted report-signer contract:** specify how the acceptance-suite signer consumes only successful `AuthenticatedObserverResult` values and emits schema v2. No private signing key or signing service until separately approved.
3. **Host challenge and transport design:** specify CSPRNG nonce generation, challenge issuance/expiry, authenticated host-to-observer transport, mutual TLS/workload identity, canary separation, and retry behavior after crash/lost response. No live network code yet.
4. **Protected identity lifecycle:** define registry signing/pinning, key rotation overlap, emergency revocation, cache TTL, audit, and recovery through the protected trust control plane.
5. **Durable replay-store implementation readiness:** design is documented in `SANDBOX_REPLAY_STORE_DESIGN.md`; actual DB/service remains gated on separate trust-boundary review, anti-rollback checkpoint design, credentials, and explicit approval.
6. **Trusted filesystem collector:** design descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, file identity checks, quotas, retention, and crash-safe cleanup. Current artifact collector remains an in-memory validator only.
7. **Threat-model review and operational gates:** cancellation races, deadlines, kill escalation, cleanup recovery, external-canary independence, IPv4/IPv6/DNS/QUIC egress, resource caps, and cross-attempt residue. VM/provider, API key, private-source transfer, KMS/HSM, paid service, or spend still require separate explicit approval.

PR #78 completes the replay-store transaction design and expands the protocol/test fake; it does not create durable storage. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #80 (2026-11-24)

1. **Trusted report-signer contract:** specify how the acceptance-suite signer consumes only successful `AuthenticatedObserverResult` values plus the exact retained envelope bytes and staging manifest, verifies all digest bindings, and emits the next report schema with `observer_envelope_manifest_sha256`. No private key or signing service until separately approved.
2. **Host challenge and transport design:** specify CSPRNG nonce generation, challenge issuance/expiry, authenticated host-to-observer transport, mutual TLS/workload identity, canary separation, and retry behavior after crash/lost response. No live network code yet.
3. **Protected identity lifecycle:** define registry signing/pinning, key rotation overlap, emergency revocation, cache TTL, audit, and recovery through the protected trust control plane.
4. **Trusted filesystem staging/collector:** implement only after a separate host trust-boundary review; use descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, exclusive create, quotas, retention, quarantine, and crash-safe cleanup.
5. **Durable replay-store implementation readiness:** design is documented in `SANDBOX_REPLAY_STORE_DESIGN.md`; actual DB/service remains gated on separate trust-boundary review, anti-rollback checkpoint design, credentials, and explicit approval.
6. **Threat-model review and operational gates:** cancellation races, deadlines, kill escalation, cleanup recovery, external-canary independence, IPv4/IPv6/DNS/QUIC egress, resource caps, and cross-attempt residue. VM/provider, API key, private-source transfer, KMS/HSM, paid service, or spend still require separate explicit approval.

PR #80 is design-only. Schema v2 does not bind a staging-manifest digest; no raw envelope storage exists. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current next steps after PR #82 (2026-11-24)

1. **Replay acceptance receipt read contract:** add a read-only receipt lookup to the observer replay-store protocol and strengthen the in-memory fake. A receipt must expose the committed observer/attempt/runtime/policy/probe, registry/key, nonce/envelope digest, sequence, challenge expiry, acceptance timestamp and ledger revision/fencing epoch. Production storage remains gated.
2. **Pure schema-v3 report builder:** assemble deterministic report bytes from the exact evidence, raw envelope bytes, pinned registry, successful observer results and matching replay receipts. Re-verify envelope signatures and every binding; do not treat the dataclass as proof.
3. **Injected report signer and verifier:** add a narrow `sign(key_id, canonical_bytes)` protocol plus deterministic fake implementation. No private key, real signing service, key generation or network.
4. **Strict schema-v3 report verifier:** bind the pre-acceptance observer-envelope manifest digest and retain v1/v2 verifiers unchanged. Verify generated fake reports end-to-end.
5. **Host challenge/transport design:** CSPRNG nonce generation, challenge issuance/expiry, authenticated host-to-observer transport, mutual TLS/workload identity, canary separation and crash/retry behavior.
6. **Protected identity lifecycle:** registry signing/pinning, rotation overlap, emergency revocation, cache TTL, audit and recovery through the protected trust control plane.
7. **Trusted filesystem staging and production gates:** actual no-follow host storage, durable replay database, KMS/HSM, VM/provider, API keys, private-source transfer, paid services and spend require separate trust-boundary review and explicit approval.

PR #82 is a design contract only. It does not sign reports, create keys, persist replay state, store files, execute probes, or authorize untrusted code. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Current baseline after PR #82 (2026-11-24)

- PR #82 merged as `d7ef7ed4266ea2606acd76f6e36fb4822af7d179`; final-head checks all passed.
- The signer contract is documented but not implemented. `AuthenticatedObserverResult` must not be trusted by type alone; the future signer must independently validate raw envelopes and match read-only trusted replay receipts.
- Immediate implementation sequence:
  1. Add replay acceptance receipt read protocol and immutable in-memory fake, retaining all fields and ledger revision/fencing epoch.
  2. Add pure schema-v3 report builder that validates exact probe/domain inventory, raw envelope bytes, Ed25519 signatures, receipt context, evidence bytes and staging manifest.
  3. Add injected report-signing and verification protocols with deterministic fake implementations only.
  4. Add strict schema-v3 verifier binding the pre-acceptance observer-envelope manifest digest; leave v1/v2 unchanged.
  5. Add end-to-end adversarial tests for signer output and independent verification.
  6. Continue with host challenge/transport and protected identity lifecycle design.
- Do not create keys, a real signer, durable replay storage, filesystem staging, network, VM/provider, or execute probes without separate review/approval. Keep both execution flags false.


## Current next steps after PR #88 implementation checkpoint (2026-11-24)

1. **Make project-memory freshness enforceable:** extend the required audit so implementation-sensitive PRs must update the authoritative status, next steps, development log, and relevant decisions/context. Current Project Memory Audit verifies source/index freshness and generates semantic artifacts, but it did not detect that project-level status/next-step documents lagged the merged PR #84 baseline. Add focused unit tests and a required CI gate; do not claim the semantic index is durable when it is a 30-day workflow artifact.
2. **Independent security review of schema-v3 signing flow:** review the pre-sign verifier, attestation issuer, one-time authorization consumption, signer trust pins, and post-sign verifier as one threat model. The in-repository tests are not an external review.
3. **Production trust-boundary decisions:** select the workload identity/mTLS provider, trust-root and certificate lifecycle owner, KMS/HSM provider and policy owner, signer deployment isolation, and durable ledger/database platform. Record explicit decisions before adapter implementation; do not guess vendors or deploy resources.
4. **Durable Replay Store readiness:** only after independent review, platform selection, and explicit approval, implement atomic nonce/digest/sequence consumption, fencing, external anti-rollback checkpoint, immutable receipts, and atomic audit with restore/failover/fault-injection tests.
5. **Authenticated Host–Observer transport:** implement only after workload identity, CA/trust roots, service discovery, network policy, and operational ownership are approved. Preserve message-level Ed25519 envelope verification in addition to TLS.
6. **Protected signer/verifier deployment:** separate verifier and report-signer workloads and keys; protect keys in KMS/HSM; pin verifier identity/key/audience out-of-band; prove authorization-store durability and one-time semantics.
7. **Operational acceptance and execution gate:** run the independently controlled 20-probe suite only in an approved isolated environment; verify cleanup, retention, egress, and post-sign evidence. Until every gate is independently satisfied, keep all execution flags false and do not transfer private source or incur spend.

PR #88 is a tested non-production implementation contract, not a production signing system. The in-memory test stores and fake cryptographic backends are not trust anchors. Do not merge or deploy it as production-ready based only on green CI.


## Reprioritized next steps — multi-project JET AI (2026-11-25)

1. Complete Phase 2A Issue #98: pure fail-closed project manifest/schema validation, immutable GitHub identity binding, registry uniqueness, lifecycle gating, implemented-runner gating, canonical manifest digest, and adversarial tests. Keep the change standard-library-only and side-effect-free.
2. Review the Phase 2A Draft PR and all exact-head checks. Do not merge without a separate approval for that PR.
3. Phase 2B: propagate explicit `project_id`, immutable repository ID, canonical repository name, default branch, manifest version/digest, and pinned base SHA through task intake and task records. Preserve a versioned migration path for legacy JET VPN envelopes; reject missing/mismatched identities for new projects.
4. Phase 2C: make project memory manifests configurable and remove the fixed six-document assumption from context building/envelope validation without weakening hash, size, path, and tracked-file checks.
5. Phase 2D: namespace lease refs, branches, workspaces, context packages, source indexes, caches, artifacts, and audit records by project identity; add cross-project isolation tests.
6. Phase 2E: implement read-only dry-run onboarding and a registry persistence/activation workflow only after the pure validator and isolation gates are reviewed. JET VPN is first fixture; keep it unregistered/inactive until all prerequisites pass.
7. Onboard «حسابگر من» only after its exact GitHub repository URL is provided and its repository ID, default branch, source layout, memory, protected paths, and verification capabilities are independently inspected.

Do not activate Python profiles until their fixed runners exist. Do not run Flutter checks for Python-only projects. Do not use task text to infer a project. No paid API, new provider spend, credentials, production change, release/deploy, or untrusted-code execution is authorized.


## Phase 2B execution plan — explicit project identity (2026-11-25)

1. Finish the v2 project-binding contract and ensure every consequential path validates it against the trusted manifest and live repository metadata: issue intake, lease request, handoff construction/acceptance, Issue revalidation, PR base/head guard, and patch-review authorization.
2. Keep v1 compatibility bounded to the exact JET VPN repository identity; add negative tests proving v1 cannot be accepted for another repository and v2 cannot silently fall back to v1.
3. Ensure schema-v3 handoffs persist the project identity tuple and pinned `base_sha` in local task records. A repository rename or manifest digest change must fail closed and require explicit migration.
4. Exact-head CI has passed on implementation head `33357ea746d3e2a5147416a8da9385ee1002b340`: 426 orchestrator tests, non-production PR validation, project-memory audit, and lease/scope guard. Re-run the checks after this status-only documentation update.
5. Review the complete diff and tests. Checks are green; keep PR #101 Draft until human review is complete and the user separately approves any merge decision.
6. After Phase 2B is reviewed and merged, proceed to Phase 2C (project-specific memory/context selection) and then Phase 2D (lease/workspace/cache/artifact namespaces). Registry persistence and activation remain later, separately gated phases.
7. Do not activate the JET VPN manifest or register «حسابگر من» in this phase. Obtain and verify the exact حسابگر من repository URL before any onboarding task.

The current task lease is time-limited. Renew it before expiry; do not run two agents on the same task/branch. No paid API, credentials, provider spend, release/deploy, production change, or untrusted-code execution.


### Additional Phase 2B control-plane check

- Verify PR authorization envelope v2 is mandatory for v2 tasks and binds the current Issue-body SHA-256, project-binding tuple, and lease-pinned base SHA. Verify legacy v1 tasks require the v1 PR envelope. Test downgrade, body-hash drift, project-binding drift, and base-SHA drift. Keep the agent context/input envelope unchanged.
