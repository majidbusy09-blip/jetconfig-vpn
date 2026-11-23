# JET VPN — Current Status

## Latest verified snapshot — 2026-11-23

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `a09cdb0be35e3072be29973f7ae8df66ab44d07f` (PR #18 documentation refresh squash-merged after PR #19).
- PR #16 merged at `c4f7f4743b3c6ffc64d34a0efb0c19f41b236f1e`; PR #17 merged at `eae477a89816a5cfd475c596e166d5cb2575884a`; PR #19 merged at `abdff3a59b89419e869c98d7dbb4ac91512fe950`; PR #18 documentation refresh merged at `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- PR #19 aligns the non-production validation Android scaffold with production SDK/package-visibility settings using `tools/validation/align_validation_android.py` and its tests. It changes validation tooling and CI only; no Dart app, native tunnel, routing, app version, signing, bot, payment, backend, server, or production-release behavior was changed.
- PR #19 head before squash: `3d47359c1ebaf6dcd6adfb19e886b9f148bbf030`; merge method: Squash.
- PR #19 CI on its final head: Project Memory Audit run [#45065541236](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541236) and Non-production PR Validation run [#45065541255](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541255) completed successfully before merge.
- PR #18 refreshed authoritative project memory only; its post-merge Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) completed successfully on the new main commit.
- App version remains `2.4.5+284`; `pubspec.yaml` blob `adc3b22a4538db4738bec789e3c3badf26e4f710`.
- `lib/main.dart` blob remains `3d28693b7be8bfe309a850923599830e1a65ab59` (9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points); PR #19 did not change app source.
- Active `main-protection` ruleset requires PRs and the project-memory status check, blocks deletion/force pushes, allows Squash only, and has no bypass actors.
- User-reported physical-device recovery scenarios passed on the tested environment: cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device/build/log details were not supplied; do not generalize beyond that report.
- No production release, deployment, version bump, or change to bot/payment/backend/server occurred in PR #19.

## Current engineering boundaries

- Primary objective: build a reliable, independent programming collaborator with durable project memory and safe execution.
- PR #20 (`design/task-execution-orchestrator-20261123`) remains Draft/open/unmerged, based on main SHA `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- Latest fully CI-verified pre-validator head `a2e04ebe203e79896ad6e13420b4bc4d1fc2f746`: Project Memory Audit [#45106590264](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45106590264) and Non-production PR Validation [#45106590252](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45106590252) both succeeded. The latter included the orchestrator integration suite, Flutter analysis/tests, debug APK smoke build, and ARM64 validation APK build.
- Added provider-neutral design contract `docs/CODING_AGENT_ADAPTER_CONTRACT.md` and schema validator `tools/task_orchestrator/agent_contract.py` with adversarial fixture tests `tools/task_orchestrator/tests/test_agent_contract.py`. Validator implementation and test commits are newer than the verified head; fresh CI is pending and must pass before this validator phase is marked verified.
- No model provider is connected; no agent-generated patch is fetched or applied. No Dart/Java/Kotlin application source, app version, signing, production release workflow, bot, payment, backend, or server behavior changed.
- Work on isolated branches; inspect complete diffs; run relevant checks; open PRs; never merge, release, deploy, or dispatch the production release workflow without explicit user approval.
- Telegram bot, payment, backend and server work are deferred unless a concrete issue appears or the user changes priority.
- JET VPN TV and حسابگر من are separate repositories; do not infer their implementation from this repository.

## Historical detail preservation

The pre-refresh status and planning snapshots are preserved in `docs/archive/CURRENT_STATUS_pre_memory_refresh_20261122.md` and `docs/archive/NEXT_STEPS_pre_memory_refresh_20261122.md`. They are historical evidence only; older PR states and SHAs must not be treated as current.

## Exact source identity

- Main commit: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- `lib/main.dart`: `3d28693b7be8bfe309a850923599830e1a65ab59`.
- `pubspec.yaml`: `adc3b22a4538db4738bec789e3c3badf26e4f710`.
- App version: `2.4.5+284`.
- PR #19 validation tool: `tools/validation/align_validation_android.py`; tests: `tools/validation/test_align_validation_android.py`.
