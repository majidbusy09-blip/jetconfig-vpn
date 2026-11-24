# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `53e00ac2ad5e260a4d214772da4ba9bccd3499f4` (PR #48 squash merge).
- PR #20, PRs #38–#44, and PRs #46–#48 are merged.
- PR #47 introduced the synthetic-only sandbox lifecycle contract.
- PR #48 refreshed project memory after PR #47. Its Task Orchestrator Tests, Project Memory Audit, and Non-production PR Validation workflows all completed successfully.
- App source/version remain unchanged: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; version `2.4.5+284`.
- Source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.
- The latest sandbox work is on branch `feat/trusted-sandbox-evidence-gate-20261124`; it adds an independent signed-evidence verifier and adversarial tests. It does not provision or execute a real sandbox.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, context/impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. No automatic model wake-up or live provider dispatch exists.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch, local result ingestion, SHA-256 patch storage, and fail-closed live review authorization are implemented and integration-tested. Patches are not automatically applied.
- `sandbox_contract.py` supports only a fixed synthetic acceptance payload and fake-provider lifecycle tests.
- `sandbox_acceptance.py` verifies a strict signed report from a separate trusted runtime suite: pinned provider/region/task/attempt/image/policy, freshness, canonical JSON, signature, and an exact 20-probe inventory. The signing verifier is injected; a production pinned-key Ed25519 implementation and actual probe runner are not yet installed.
- Even a passing evidence report explicitly remains `execution_authorized: false` and `eligible_for_untrusted_execution: false`.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner remains opt-in and metadata-only; no live request has been made.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path.
- Neither E2B nor Daytona is approved for a pilot under current constraints. E2B requires prior written consent before testing and a payment method for EU workspace verification; Daytona's strict sandbox-level egress policy is tier-gated with a documented $500 Tier 3 top-up.
- No vendor account, API key, payment method, sandbox, private-source transfer, provider signing key, or provider spend has been created or authorized.
- No production release, deployment, version bump, signing change, app behavior, bot, payment, backend, or server change is in scope.
- CI/build success is not proof of physical-device VPN runtime behavior or sandbox isolation.

## Next engineering objective

Implement the fixed external probe suite and a separately controlled signing/verifier trust root, then validate against a real candidate VM only after separate account, consent, data-governance, and cost approval. Until actual signed evidence passes all 20 probes, keep the runtime synthetic-only and do not run untrusted code.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.
