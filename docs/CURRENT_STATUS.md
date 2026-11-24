# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `4dbe01eda4078342c17f16a4111919bebaa616ae` (PR #46 squash merge).
- PR #20 and PRs #38–#44 are merged. PR #46 refreshed the authoritative memory and corrected the stale sandbox-vendor recommendation.
- PR #44 integration test confirms fixture result ingestion → content-addressed artifact → live Issue/lease review gate, with `ready_for_human_review` and `applied: false`.
- PR #46 head `be9a280aa9c1c7f00479b4a01aff0c724f0d51c1`: Project Memory Audit #45313415951, Task Orchestrator Tests #45313415720, and `validate-agent-pr` #45313412813 passed. Non-production app-build attempt 1 failed because Maven Central returned HTTP 429 for dependencies; attempt 2 was in progress at this snapshot. No app source changed in PR #46.
- `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59`; source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.
- `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`; app version remains `2.4.5+284`.
- Active `main-protection` ruleset requires PR + `Verify generated code index and memory freshness`, blocks deletion/force pushes, allows Squash only, and has no bypass actors.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, context/impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. No automatic model wake-up or live provider dispatch exists.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch, local result ingestion, SHA-256 patch storage, and fail-closed live review authorization are implemented and integration-tested. Success remains review-only; patches are never auto-applied.
- Branch `feat/sandbox-lifecycle-contract-20261124-v2` adds a synthetic-only sandbox lifecycle state machine, capability checks, runtime snapshot validation, bounded artifact integrity checks, interruption cleanup, and fake-provider tests. It is not merged or CI-verified yet and does not enable untrusted code execution.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner remains opt-in and metadata-only; no live request has been made.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path.
- Neither E2B nor Daytona is approved for a pilot under current constraints. E2B requires prior written consent before testing and a payment method for EU workspace verification; Daytona's strict sandbox-level egress policy is tier-gated with a documented $500 Tier 3 top-up.
- No vendor account, API key, payment method, sandbox, private-source transfer, or provider spend has been created or authorized.
- No production release, deployment, version bump, signing change, app behavior, bot, payment, backend, or server change is included in PR #46 or the current sandbox branch.
- CI/build success is not proof of physical-device VPN runtime behavior.

## Next engineering objective

Complete CI validation and review of the synthetic-only sandbox lifecycle contract. After it merges, build a separate trusted runtime-acceptance harness that can independently verify a real candidate VM's network denial, resource limits, process-tree termination, artifact bounds, and destruction. Do not connect a live provider or execute untrusted code until all acceptance evidence exists and separate approval is granted.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.
