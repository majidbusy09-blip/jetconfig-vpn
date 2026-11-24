# JET VPN — Prioritized Next Steps

## Verified baseline — 2026-11-24

- Current `main`: `1438d0a047523a22fee26e72ae12cf34cebbb95e` (PR #49 merged).
- PR #20, PRs #38–#44, and PRs #46–#51 are merged.
- PR #49 Task Orchestrator Tests #45320041554 passed 259 tests, Project Memory Audit #45320041561 passed, and Agent PR Lease and Scope Guard #45320038880 passed.
- Non-production PR Validation #45320041553 remained pending; PR #49 changed developer tooling/docs only.
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

## P0a — Trust-root implementation design (safe, no vendor required)

- Specify a versioned public-key trust store with key ID, algorithm, public-key bytes, validity interval, status, and revocation metadata.
- Verify the signature over exact canonical report bytes before trusting report claims; bind suite version and signer identity to the trust entry.
- Reject unknown, expired, revoked, not-yet-valid, duplicate, or algorithm-mismatched keys; fail closed on verifier errors.
- Keep trust-store updates reviewed and auditable; prevent rollback to an older trust-store version.
- Add known-answer, tamper, rotation/revocation, and malformed-key tests. No signing private key or live signing service is created in this phase.

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
