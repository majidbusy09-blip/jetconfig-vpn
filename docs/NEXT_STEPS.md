# JET VPN — Prioritized Next Steps

## Verified baseline — 2026-11-24

- Current `main`: `f682c56331bfb7c07bc4c5be26fddc33a3043969`.
- PR #20 and PRs #38–#44 are merged.
- PR #44's Task Orchestrator Tests, Non-production PR Validation, and Project Memory Audit workflows all succeeded on its head.
- App source and app version are unchanged: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; version `2.4.5+284`.
- The tested path is: task envelope → fixture dispatch/result → local provider-result ingestion → content-addressed patch artifact → live Issue/lease review gate → `ready_for_human_review`, `applied: false`.
- There is still no live provider, safe untrusted-code execution runtime, automatic patch application, or unattended merge.

## P0 — Build the provider-neutral sandbox contract without a vendor

1. Define a narrow adapter contract and explicit capability declaration for create, readiness, bounded execution, artifact export, state inspection, termination, and destruction confirmation.
2. Add a fail-closed lifecycle state machine. Missing or ambiguous capabilities, unknown runtime state, network policy not proven, or cleanup failure must block execution and patch acceptance.
3. Require a dedicated ephemeral Linux VM (not a shared-kernel container), pinned image digest, non-root guest, no credentials/secrets, deny-all egress from creation, hard CPU/RAM/PID/disk/wall-clock limits, and full process-tree termination.
4. Define independent evidence checks: verify actual network denial from inside the guest and from an external canary; verify limits under harmless synthetic load; verify timeout/cancellation kills descendants; verify the sandbox reaches a terminal destroyed state.
5. Keep artifact return narrow: bounded patch + changed-path manifest + bounded diagnostics; verify SHA-256, UTF-8, path allowlist, exclusions, and exact bytes before existing review gates.
6. Implement only a fake/in-memory adapter and failure-injection tests first. No real provider, source upload, model execution, credentials, account, or cost.

## P1 — Complete collaborator integration after the contract is stable

- Connect the provider-neutral sandbox interface to the existing task lifecycle without giving the model GitHub write credentials or host access.
- Keep task ownership/lease checks live and fail closed on stale Issue, expired lease, moved lock ref, changed base, dirty workspace, or unexpected paths.
- Add an explicit human-controlled patch-application stage only after independent verification and review design are complete. Until then, all outputs remain unapplied.
- Add an observable task status/report that distinguishes planning, dispatch, execution, ingestion, validation, human review, and rejection. Never imply a provider is running when only a fixture ran.

## P2 — Reassess external runtime providers only after technical acceptance tests exist

- E2B is not currently available for the intended pilot under the current constraints: vendor documentation requires prior written consent before testing, and its EU workspace verification requires a payment method.
- Daytona's strict sandbox-level `networkBlockAll` controls are tier-gated; the documented Tier 3 path requires a $500 top-up. Do not upgrade or spend without a separate decision.
- Reassess other providers only against the same VM, network-denial, limits, lifecycle, data-residency, retention, DPA, and audit criteria. Do not lower the threat model to fit a vendor.

## P3 — Cross-repository project memory

- Perform read-only architecture/workflow inventories of `jetconfig-vpn-tv` and `hesabgar_man`.
- Establish repository-specific instructions and a shared project map only after verifying each repository's current source.
- Keep the Android JET VPN collaborator as the primary development priority.

## Deferred

- Live model calls, API keys, paid services, vendor accounts, sandbox provisioning, private-source transfer, and any provider spend: separate approval required.
- Production release, deployment, signing, app version changes, bot/payment/backend/server changes: out of scope for this roadmap.
- Do not merge PRs without explicit user approval; do not dispatch the production release workflow without explicit approval.
