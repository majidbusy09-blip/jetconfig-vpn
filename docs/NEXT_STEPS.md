# JET VPN — Prioritized Next Steps

## Verified baseline — 2026-11-24

- Current `main`: `4dbe01eda4078342c17f16a4111919bebaa616ae` (PR #46 merged).
- PR #20 and PRs #38–#44 are merged; PR #46 corrected the authoritative project memory and sandbox-provider decision.
- PR #46 Project Memory Audit, Task Orchestrator Tests, and `validate-agent-pr` passed. Its unrelated non-production APK build hit Maven Central HTTP 429 on the first attempt; retry was still in progress at this snapshot.
- App source/version remain unchanged: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; version `2.4.5+284`.
- The validated path is task envelope → fixture dispatch → local result ingestion → content-addressed patch → live Issue/lease review gate → `ready_for_human_review`, `applied: false`.

## P0 — Complete synthetic-only sandbox lifecycle contract

Branch `feat/sandbox-lifecycle-contract-20261124-v2` contains the first implementation and requires CI/review:

- Provider-neutral `SandboxProvider` protocol with no arbitrary shell, source upload, or credential injection methods.
- Strict request schema, pinned image/policy SHA-256 digests, explicit CPU/RAM/PID/disk/wall-time limits, and deny-all network policy.
- Linux VM-only capability gate; rejects shared-kernel containers and missing VM, dedicated-kernel, image pinning, egress, resource, process-tree, credential, artifact, or destruction capabilities.
- Provider-reported ready-state checks for blocked egress, ephemeral VM, dedicated kernel, enforced limits, no credentials/host sockets, and process-tree termination. These reports are not independent attestation.
- Explicit lifecycle state machine and mandatory terminate → terminated confirmation → destroy → destroyed confirmation.
- Fixed synthetic acceptance payload only; bounded SHA-256-verified artifact; interruption and failure cleanup.
- Fake-provider tests cover success, missing capabilities, open egress, credentials/host sockets, timeout, invalid/oversized artifact, destroy failure, provider-error sanitization, and interruption cleanup.
- Every success reports `eligible_for_untrusted_execution: false` and `patch_applied: false`. No real provider or sandbox is connected.

## P1 — Build independent runtime acceptance evidence

1. Design a trusted control-plane acceptance harness that tests the actual candidate VM, not just provider declarations or API responses.
2. Verify egress denial from inside the guest and an external canary, including DNS/QUIC bypass attempts.
3. Verify hard CPU, memory, PID, disk, and wall-clock enforcement under harmless synthetic load.
4. Verify timeout/cancellation kills the full process tree and that termination/destruction are independently observable.
5. Verify immutable image digest, dedicated guest kernel, read-only source, isolated scratch, no credentials/sockets/metadata access, bounded artifact export, and cleanup on every failure path.
6. Keep the harness synthetic-only until all tests pass; it must not upload private source or run model-generated code.

## P2 — Reassess managed providers only after acceptance harness exists

- E2B remains blocked by prior-written-consent requirement before testing and EU workspace payment-method verification.
- Daytona's strict sandbox-level `networkBlockAll` is tier-gated; documented Tier 3 requires a $500 top-up.
- Do not create accounts, add payment methods, provision sandboxes, upload source, or spend without separate approval. Evaluate any alternative against the same threat model and data/legal terms.

## P3 — Complete multi-agent implementation integration

- Connect the sandbox broker to task leases and the existing dispatcher only after P1 evidence passes.
- Keep model API credentials in the provider control plane, never in the code-execution guest.
- Keep patch application separate, human-reviewed, and disabled until its own scope/rollback/recovery gates are implemented.
- Add task status reporting that distinguishes planning, dispatch, execution, ingestion, validation, review, and rejection.

## P4 — Cross-repository project memory

- Perform read-only architecture/workflow inventories of `jetconfig-vpn-tv` and `hesabgar_man`.
- Add repository-specific instructions and a shared project map only after verifying each repository's current source.

## Deferred

- Live model calls, API keys, paid services, vendor accounts, sandbox provisioning, private-source transfer, and provider spend: separate approval required.
- Production release, deployment, signing, app version changes, bot/payment/backend/server changes: separate explicit approval required.
