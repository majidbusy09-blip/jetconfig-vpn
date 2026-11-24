# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `3e613a8c03a39e4440c3702ac3505acb7b2eae27` (PR #53 squash merge).
- PR #20, PRs #38–#44, and PRs #46–#53 are merged.
- PR #47 introduced the synthetic-only sandbox lifecycle contract.
- PR #48 refreshed project memory after PR #47.
- PR #49 added the independent signed-evidence verifier and its 12 adversarial tests.
- PR #50 refreshed project memory after PR #49.
- PR #53 adds `sandbox_trust.py`, a strict trust-store policy adapter with canonical parsing, independent SHA-256 pinning, minimum-version enforcement, and active/in-window Ed25519 key selection; signature math remains injected and rollback state is external.
- PR #53 head `b0b5f72c1d8c7f0940b1c1cfb8cb5dacdb1cb11b` passed Task Orchestrator Tests #45334662136 (271 tests), Project Memory Audit #45334662120, Non-production PR Validation #45334662100, and Agent PR Lease and Scope Guard #45334659579; squash-merged as `3e613a8c03a39e4440c3702ac3505acb7b2eae27`.
- PR #51 binds every signed probe digest to the exact supplied raw evidence bytes, recomputes SHA-256, enforces exact evidence inventory, and caps each blob at 128 KiB / aggregate evidence at 2 MiB.
- PR #49 verification: Task Orchestrator Tests #45320041554 passed 259 tests; Project Memory Audit #45320041561 passed; Agent PR Lease and Scope Guard #45320038880 passed.
- PR #50 validation runs #45320512137 and related required checks completed successfully.
- PR #51 head `42c208398ef0b044ba54c17ca183957022eb0288`: Task Orchestrator Tests #45325193322, Project Memory Audit #45325193253, Agent PR Lease and Scope Guard #45325195790, and Non-production PR Validation #45325193266 all completed successfully; PR #51 merged as `1438d0a047523a22fee26e72ae12cf34cebbb95e`.
- Non-production PR Validation #45320041553 remained pending at merge. PR #49 changed only developer tooling and documentation; application source and version were unchanged.
- App source/version: `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; `2.4.5+284`.
- Source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, context/impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. No automatic model wake-up or live provider dispatch exists.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch, local result ingestion, SHA-256 patch storage, and fail-closed live review authorization are implemented and integration-tested. Patches are not automatically applied.
- `sandbox_contract.py` supports only a fixed synthetic acceptance payload and fake-provider lifecycle tests.
- `sandbox_acceptance.py` verifies a strict signed report from a separate trusted runtime suite: pinned provider/region/task/attempt/image/policy, freshness, canonical JSON, signature, exact 20-probe inventory, and independently recomputed SHA-256 over all supplied raw evidence bytes. The signing verifier remains injected. `sandbox_trust.py` now validates an externally pinned trust-store digest, minimum version, key status, validity window, and Ed25519 public-key shape; signature mathematics still requires an audited injected backend, and the independent external probe suite is not installed.
- `runtime_acceptance_probe.py` is only a controlled benign Bubblewrap self-check; `runtime_probe.py` is host inventory/preflight. Neither is the independent 20-probe suite nor evidence of a production sandbox.
- Even a passing evidence report explicitly remains `execution_authorized: false` and `eligible_for_untrusted_execution: false`.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner remains opt-in and metadata-only; no live request has been made.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path.
- Neither E2B nor Daytona is approved for a pilot under current constraints. E2B requires prior written consent before testing and a payment method for EU workspace verification; Daytona's strict sandbox-level egress policy is tier-gated with a documented $500 Tier 3 top-up.
- No vendor account, API key, payment method, sandbox, private-source transfer, provider signing key, or provider spend has been created or authorized.
- No production release, deployment, version bump, signing change, app behavior, bot, payment, backend, or server change is in scope.
- CI/build success is not proof of physical-device VPN runtime behavior or sandbox isolation.

## Next engineering objective

Next implement the independent 20-probe host/guest runtime acceptance suite and protected trust-configuration control plane. Review audited Ed25519 dependency options without adding an unapproved dependency. Real VM/provider validation remains blocked pending separate account, consent, data-governance, and cost approval. Keep the runtime synthetic-only and do not run untrusted code.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.
