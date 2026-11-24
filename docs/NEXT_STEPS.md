# JET VPN — Prioritized Next Steps

## Verified baseline — 2026-11-24

- Current `main`: `f360d50b13064c7136eb7ce4a3b38e3413e5b333` (PR #47 merged).
- PR #20, PRs #38–#44, PR #46, and PR #47 are merged.
- PR #47 Task Orchestrator Tests #45314331567 passed 247 Python tests, including all 13 sandbox lifecycle tests; Project Memory Audit #45314331612 passed. Non-production PR Validation #45314331545 was still running at this snapshot.
- App source/version remain unchanged: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; version `2.4.5+284`.
- Validated flow: task envelope → fixture dispatch → local result ingestion → content-addressed patch → live Issue/lease review gate → `ready_for_human_review`, `applied: false`.

## P0 — Trusted runtime-acceptance harness

The synthetic-only lifecycle contract is merged. The next task is not to connect a model; it is to build an independent acceptance harness for an actual candidate runtime.

1. Define a trusted probe runner separate from the provider adapter; the provider must not author its own pass/fail evidence.
2. Verify actual guest class and unique kernel, pinned image digest, read-only source, isolated scratch, no credentials, host sockets, devices, or metadata access.
3. Verify deny-all egress from inside the guest and an external canary, including DNS and QUIC/HTTP3 bypass attempts.
4. Apply harmless synthetic load and verify enforced CPU, memory, PID, disk, and wall-clock limits.
5. Verify timeout/cancellation kills the full process tree and that termination/destruction are independently observable.
6. Verify artifact bounds, digest, path allowlist, and cleanup on every success/failure/interruption path.
7. Require evidence to be bound to provider/runtime identity, image/policy digests, attempt ID, timestamps, and test-suite version. Provider-reported metadata alone is never sufficient.
8. Keep the harness synthetic-only; no private source, model-generated code, credentials, or live provider until a separate approval.

## P1 — Provider and data-governance decision

- E2B remains blocked by prior-written-consent requirement before testing and EU workspace payment-method verification.
- Daytona's strict sandbox-level `networkBlockAll` is tier-gated; documented Tier 3 requires a $500 top-up.
- Do not create accounts, add payment methods, provision sandboxes, upload source, or spend without separate approval.
- Evaluate any alternative against the same VM, network, limits, lifecycle, data residency, retention, DPA, and audit requirements.

## P2 — Complete multi-agent implementation integration

- Connect the sandbox broker to task leases and the existing dispatcher only after P0 acceptance evidence passes.
- Keep model API credentials in the provider control plane, never in the code-execution guest.
- Keep patch application separate, human-reviewed, and disabled until its own scope/rollback/recovery gates are implemented.
- Add task status reporting that distinguishes planning, dispatch, execution, ingestion, validation, review, and rejection.

## P3 — Cross-repository project memory

- Perform read-only architecture/workflow inventories of `jetconfig-vpn-tv` and `hesabgar_man`.
- Add repository-specific instructions and a shared project map only after verifying each repository's current source.

## Deferred

- Live model calls, API keys, paid services, vendor accounts, sandbox provisioning, private-source transfer, and provider spend: separate approval required.
- Production release, deployment, signing, app version changes, bot/payment/backend/server changes: separate explicit approval required.
