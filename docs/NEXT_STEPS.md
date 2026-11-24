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

