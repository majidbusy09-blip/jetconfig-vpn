# JET VPN — Current Status

## Latest verified snapshot — 2026-11-24

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `f360d50b13064c7136eb7ce4a3b38e3413e5b333` (PR #47 squash merge).
- PR #20, PRs #38–#44, PR #46, and PR #47 are merged.
- PR #46 corrected the authoritative memory and superseded the outdated E2B-first pilot recommendation.
- PR #47 added a synthetic-only sandbox lifecycle contract and fake-provider tests. It does not provision a sandbox, connect a real provider, upload source, or execute model-generated code.
- PR #47 head `846b4cf15ba176178c811f45e51384bc25ae3c28`: Task Orchestrator Tests #45314331567 passed 247 Python tests, including all 13 new sandbox tests; Project Memory Audit #45314331612 passed; `validate-agent-pr` passed. Non-production PR Validation #45314331545 was still running at this snapshot.
- `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59`; source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.
- `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`; app version remains `2.4.5+284`.
- Active `main-protection` ruleset requires PR + `Verify generated code index and memory freshness`, blocks deletion/force pushes, allows Squash only, and has no bypass actors.

## Current collaborator capabilities

- Durable project memory includes mandatory agent instructions, source navigation, analyzer-resolved Dart indexes, curated critical paths, freshness auditing, and task-scoped context packages pinned to a Git commit.
- Local orchestrator supports task lifecycle, context/impact analysis, fixed verification profiles, scope checks, and human-reviewed handoff.
- Shared GitHub Issue intake and lease workflows support provider-neutral task assignment and claim/renew/release. No automatic model wake-up or live provider dispatch exists.
- Provider-neutral task/result contracts validate scope, context fingerprints, structured results, and opaque content-addressed patch references.
- Fixture-only dispatch, local result ingestion, SHA-256 patch storage, and fail-closed live review authorization are implemented and integration-tested. Patches are not automatically applied.
- The sandbox lifecycle contract supports only a fixed synthetic acceptance payload. It requires a Linux VM declaration, pinned image/policy digests, deny-all network request, explicit resource limits, provider-reported runtime checks, bounded SHA-256 artifact, and confirmed termination/destruction. Provider metadata is not independent attestation.
- All successful sandbox test records explicitly set `eligible_for_untrusted_execution: false` and `patch_applied: false`.

## Security and execution boundaries

- No live model provider is connected. The OpenAI planner remains opt-in and metadata-only; no live request has been made.
- The hosted GitHub runner is not approved for untrusted code execution: the observed runner lacked delegated cgroup controls and visible Seccomp filtering and exposed a Docker socket path.
- Neither E2B nor Daytona is approved for a pilot under current constraints. E2B requires prior written consent before testing and a payment method for EU workspace verification; Daytona's strict sandbox-level egress policy is tier-gated with a documented $500 Tier 3 top-up.
- No vendor account, API key, payment method, sandbox, private-source transfer, or provider spend has been created or authorized.
- No production release, deployment, version bump, signing change, app behavior, bot, payment, backend, or server change is included in PRs #46 or #47.
- CI/build success is not proof of physical-device VPN runtime behavior.

## Next engineering objective

Build a trusted runtime-acceptance harness that independently tests a real candidate VM's egress denial, DNS/QUIC behavior, resource limits, process-tree termination, credential/socket isolation, artifact bounds, and destruction. Until an actual runtime and independent evidence exist, keep the sandbox synthetic-only and do not run untrusted code.

## Historical detail

Older snapshots and superseded planning are preserved in `docs/archive/`. Do not treat older SHAs, PR states, or vendor selections as current.
