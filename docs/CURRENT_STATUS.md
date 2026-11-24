# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `f682c56331bfb7c07bc4c5be26fddc33a3043969` (PR #44 squash merge).
- PR #20 merged at `15fea59e4f83704e0a9955363e0f0b237aac09ac`; the local task orchestrator MVP, coding-agent contract validator, context/impact tooling, and fixture-only read-only adapter are now part of main.
- PR #38 merged at `75f6601a8b516d3bec0cd641e57292d0615a4aed`: local content-addressed patch artifact store and integrity checks.
- PR #39 merged at `834a627d1d9df81f11a462c760ce17acb08c788f`: fail-closed live Patch review authorization gate.
- PR #40 merged at `e50a8c871f0105cb185fdf70ae72967cb63a6d9a`: read-only live Patch review command.
- PR #41 merged at `27d9bcf8a71585ed9dcc3d1997f33c1f468ec7ea`: local provider-result ingestion with digest, scope, and overwrite checks.
- PR #42 merged at `f603d4f7190459be0f4bd56db67851f12e01c3c9`: fixture dispatch-to-ingestion integration test.
- PR #43 merged at `fa5915d746ad339840f181aee5e9b26b93f8002b`: live review command integration test with mocked GitHub/lease observations.
- PR #44 merged at `f682c56331bfb7c07bc4c5be26fddc33a3043969`: ingestion-to-live-review integration test; the exact content-addressed patch reaches `ready_for_human_review` and remains unapplied.
- PR #44 head `af5fc704f61fd8a656966b35ddbe9450630d8c1f` passed three workflows: Task Orchestrator Tests [#45307323849], Non-production PR Validation [#45307323773], and Project Memory Audit [#45307323780].
- `lib/main.dart` blob remains `3d28693b7be8bfe309a850923599830e1a65ab59`; `pubspec.yaml` blob remains `adc3b22a4538db4738bec789e3c3badf26e4f710`; app version remains `2.4.5+284`.
- `lib/main.dart` source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points (verified by the memory audit).
- Active `main-protection` ruleset requires PRs and the `Verify generated code index and memory freshness` status check, blocks deletion/force pushes, allows Squash only, and has no bypass actors.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, explicit source context selection, impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. The local orchestrator does not itself wake a model provider.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch and local result ingestion are tested. The live review command reads GitHub Issue/lease state and validates the exact patch artifact before declaring it ready for human review.
- Success states are review-only: `ready_for_human_review`, `applied: false`. No patch is automatically applied, committed, pushed, merged, or deployed.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner is opt-in, metadata-only, requires separately configured credentials, and has not been invoked.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path. Do not bypass these restrictions.
- No E2B/Daytona account, API key, sandbox, payment method, or paid infrastructure has been created. E2B's prior-written-consent requirement and EU workspace payment-method requirement block the current pilot; Daytona's strict sandbox-level egress policy requires a higher tier with a substantial top-up. See `docs/MANAGED_SANDBOX_CANDIDATE_EVALUATION.md`.
- No private repository source has been transferred to an external provider. No model API usage or provider spend has been authorized.
- No production release, deployment, version bump, signing change, or change to app behavior, bot, payment, backend, or server occurred in PRs #20 and #38–#44.
- CI/build success is not proof of physical-device VPN runtime behavior.

## Next engineering objective

Design and test a provider-neutral, fail-closed sandbox lifecycle contract with a fake adapter and no external execution. Only after its state machine and failure cases are tested should we revisit a real sandbox provider. The provider must demonstrate a dedicated VM boundary, deny-all egress, enforced resource/time limits, process-tree termination, bounded artifact return, and verified destruction before any untrusted code is considered.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.
