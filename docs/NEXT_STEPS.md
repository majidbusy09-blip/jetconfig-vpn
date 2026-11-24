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
