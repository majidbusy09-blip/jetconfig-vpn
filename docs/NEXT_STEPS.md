# JET VPN — Prioritized Next Steps

## Current authoritative roadmap — 2026-11-24

### Baseline and operating constraints

- Live `main` at the start of this checkpoint: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e` (PR #84 merge). Re-fetch the live ref before every session; this SHA is a historical checkpoint, not a permanent pointer.
- PR #89 is Draft/open/unmerged. Its v1.2 eight-document context contract and enforced project-memory change gate are candidate-branch features until a human-approved merge.
- PR #91 is Draft/open/unmerged and records the successful ChatGPT documentation-only GitHub-connector pilot. Its lease is released and its exact-head checks passed.
- The approved model interaction route is only the user's ChatGPT and Grok chat sessions through their existing GitHub connections. No model API key, paid model API, external source-upload adapter, or autonomous background polling.
- GitHub is the shared task inbox, lease authority, source of truth, PR history, and durable project memory. One implementation agent per task; the other may review read-only.
- The sandbox track remains separate. No arbitrary untrusted-code execution, provider provisioning, external spend, merge, release, or deployment is authorized by this roadmap.

### P0 — Independent Grok read-only review of PR #91 (NEXT ACTION)

**Owner:** user-activated Grok chat. **Lease:** not required; review must be read-only.

- Read PR #91, Issue #90, the exact PR head, changed file, PR envelope, and exact-head check-runs directly through Grok's existing GitHub integration.
- Review whether the ChatGPT pilot genuinely satisfies the lease, pinned-base, allowlist, branch/commit/PR metadata, scope-guard, and release requirements. Separate verified evidence from assumptions.
- Return findings with severity, exact file/line or API evidence, and an explicit pass/fail recommendation. Do not write comments, commits, branches, or PR changes.

**Acceptance:** an independent review report grounded in PR #91's exact head and check-run IDs, with no repository mutations.

### P1 — Verify Grok's GitHub write path independently

- After the read-only review, create a new low-risk documentation-only Issue assigned to `grok`, with a narrow allowlist and fixed Python-tooling verification profile.
- Activate the Grok chat; claim a new lease; independently verify the lock ref, owner, claim ID, expiry, and pinned base SHA.
- Require Grok to create its own remote branch from that exact SHA, commit one in-scope Markdown artifact, and open a Draft PR with the exact final-body `jet-agent-pr:v1` envelope.
- Run and inspect the trusted scope guard and all required checks on the exact final PR head; release and verify the lease.

**Acceptance:** a Grok-owned Draft PR with a single allowed file, exact-base provenance, green exact-head checks, and a verified released lease. If a connector operation is unavailable, record it as unavailable and let the user perform only that discrete action; do not claim it succeeded.

### P2 — Complete one real coding task end to end

- Select one small, evidence-backed, non-sensitive source-code task with a clear regression test and a narrow allowlist. Do not choose a sandbox/provider task or a production/payment/credential change.
- Use one implementation chat and one active lease. Read the pinned project memory and only the selected in-scope source; create a remote branch from the pinned base SHA; implement and test; open a Draft PR.
- Have the other chat perform a read-only review against the exact PR head. Resolve findings under the same task/lease protocol; do not let both agents write concurrently.
- Update durable memory in the same PR and verify all required exact-head checks.

**Acceptance:** an actual application/tooling code change (not only documentation) implemented through the chat connector, regression tests passing, independent review completed, scope guard passing, lease released, and complete audit trail.

### P3 — Stabilize memory enforcement and session continuity

- Independently review PR #89's memory-diff gate, v1.2 eight-document contract, legacy v1.1 compatibility, exact-base pinning, size cap, and documentation accuracy.
- Obtain the user's explicit merge decision; do not merge PR #89 automatically. Until merged, do not describe its gate or v1.2 contract as a main-branch capability.
- At every session start, fetch live main/PR/Issue/lease/check state. At every pause, update CURRENT_STATUS, NEXT_STEPS, DEVELOPMENT_LOG, and DECISIONS. Follow the mandatory anti-drift procedure in AGENTS.md.
- After an approved merge, verify the ruleset's required memory check against the actual main branch and run a safe negative test proving incomplete memory updates are blocked.

**Acceptance:** one current authoritative roadmap, no contradictory active priorities, exact GitHub state at every checkpoint, and a reproducible resume path after interruption.

### P4 — Triage the legacy open-PR backlog

- GitHub showed 18 open PRs at the audit checkpoint. PRs #89 and #91 are on the current connector/memory path; PRs #86–#88 are a separate sandbox stack. Older PRs must be reviewed for dependency, relevance, supersession, and risk before any work resumes.
- Do not merge, close, rebase, or rewrite legacy PRs in bulk. Create a disposition list and handle each only after checking its current exact head and dependencies.

**Acceptance:** every open PR is classified as active, blocked, superseded, or awaiting human decision; no stale branch is mistaken for the current task.

### Separate, deferred track — sandbox and untrusted execution

PRs #86–#88 continue the synthetic schema-v3 report pipeline. They are not prerequisites for chat-based repository work. Real filesystem staging, durable replay storage, mTLS/workload identity, KMS/HSM, VM/provider, production signer, external spend, and any arbitrary untrusted execution remain blocked pending separate security review and explicit approval. Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.

## Historical roadmap and milestones (superseded)

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


## Project-memory reliability follow-up — 2026-11-24

1. Validate the implementation-sensitive PR memory gate on its exact candidate head: unit tests, Project Memory Audit, and required-check status.
2. Verify that PR #88's same-PR memory refresh satisfies the new gate once the workflow is available; do not mistake the prior pre-gate success for proof.
3. After any approved merge, verify the ruleset requires the Project Memory Audit check and test a deliberately incomplete implementation PR in a safe test branch to prove the gate blocks it.
4. Keep reviewing factual accuracy manually: this gate only requires relevant docs to change; it cannot determine whether a summary is truthful or complete.
5. Resume the schema-v3 production gates only after independent review and platform decisions: mTLS/workload identity, KMS/HSM key custody, isolated signer, and durable anti-replay ledger.

Do not merge PRs, alter branch protection, provision infrastructure, or authorize execution without explicit approval.


## Agent context completeness follow-up — 2026-11-24

- Confirm the expanded mandatory context (decisions and known issues) passes context-builder and orchestrator integration tests and remains within the 512 KiB cap.
- Review whether the full development log should eventually be replaced in routine task context by a compact, commit-pinned summary plus task-relevant log excerpts. Do not reduce history or omit decisions without a tested retrieval design.
- Keep source selection explicit and bounded; semantic suggestions remain advisory and never expand task scope automatically.


## Versioned agent memory contract follow-up — 2026-11-24

1. Run exact-head Task Orchestrator Tests, Non-production PR Validation, and Project Memory Audit after contract v1.2 changes.
2. Confirm legacy v1.1 envelopes/results remain accepted as a matched pair and new v1.2 envelopes/results require the exact eight-document manifest.
3. Confirm the GitHub task-handoff fixture includes decisions and known issues at the pinned base and emits an eight-document context package.
4. If context exceeds the existing 512 KiB cap, fail closed and select a smaller explicit source context; do not silently truncate project memory.
5. After CI succeeds, update this status with the exact head SHA and check run IDs. Do not merge either draft PR without explicit approval.


## After exact-head validation of PR #89 — superseded operating plan (2026-11-24)

PR #89 remains Draft/open/unmerged pending human review. The v1.2 eight-document context contract and project-memory change gate are candidate-branch capabilities until an explicit merge. Verify its exact-head checks and the ruleset before any approved merge.

The earlier instruction to build a paid/read-only provider adapter, configure model credentials, transfer source to an external API, and wait for isolated provider execution is superseded by the user's accepted architecture: ChatGPT and Grok chat sessions use their existing GitHub connections, with no model API key or paid model API. The connector-based route is user-activated and does not wake chats or poll in the background.

Immediate work is to complete and validate the GitHub connector runbook, verify each connector's actual write capabilities, and perform a harmless documentation-only pilot with one active lease, a remote branch pinned to the exact base SHA, PR scope guard, exact-head Actions checks, and read-only review by the other agent. The production sandbox remains a separate track and is not a prerequisite for this workflow.

Do not merge PRs, alter branch protection, provision infrastructure, create API keys, use paid model APIs, upload private source to external APIs, or authorize untrusted execution without separate explicit approval.


## Updated connector pilot status — 2026-11-24

- ChatGPT's documentation-only GitHub connector pilot is complete and verified on PR #91. The exact final head passed the trusted PR scope guard, Non-production PR Validation, and Project Memory Audit. The lease was released. Do not repeat the ChatGPT pilot unless the connector behavior changes.
- Next independent validation is Grok: have the Grok chat read PR #91 in read-only mode and return a source-grounded review of the pilot protocol, PR metadata, scope, and CI evidence. This review does not need an implementation lease and must not modify the branch.
- Then verify Grok's actual GitHub operations separately. If a Grok write pilot is needed, create a new low-risk docs-only Issue assigned to grok, claim its own lease, use a separate remote branch from the pinned base, open a Draft PR, and release the lease after exact-head checks pass.
- Keep PR #89 Draft/open until human review; it carries the candidate v1.2 memory contract and enforced memory gate. The current main branch does not yet contain those candidate features.
- No model API key, paid model API, external source upload, provider account, arbitrary untrusted execution, merge, release, or deployment is authorized.
