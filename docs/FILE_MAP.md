# JET VPN — Verified Repository File Map

> Current source snapshot: `main` at `a09cdb0be35e3072be29973f7ae8df66ab44d07f`, 2026-11-23. PRs #16, #17, #18, and #19 are merged. App version `2.4.5+284`; `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`.

| Path | Verified purpose |
|---|---|
| `AGENTS.md` | Mandatory operating instructions for AI agents/contributors. |
| `docs/TASK_TEMPLATE.md` | Required structured record for non-trivial engineering and maintenance tasks. |
| `docs/TASK_ORCHESTRATOR_DESIGN.md` | Design and safety contract for the local task execution orchestrator. |
| `tools/task_orchestrator/task_orchestrator.py` | Local fail-closed CLI for task records, context/base pinning, scope validation, fixed verification profiles, and handoff; currently under PR #20 review, not yet on main. |
| `tools/task_orchestrator/tests/test_task_orchestrator.py` | Temporary-Git-repository integration tests for lifecycle and safety gates; currently under PR #20 review. |
| `tools/task_orchestrator/README.md` | Local MVP usage, fixed profiles, and explicit non-goals; currently under PR #20 review. |
| `tools/validation/align_validation_android.py` | Aligns the temporary validation Android scaffold with production SDK/package-visibility settings. |
| `tools/validation/test_align_validation_android.py` | Unit tests for validation Android parity and idempotency. |
| `README.md` | Project overview; may describe wider JetConfig ecosystem not included in this repository. |
| `pubspec.yaml` | Flutter package metadata, version, SDK constraint, dependencies. |
| `lib/main.dart` | Main Flutter application; UI, account, payment, server, VPN connection/recovery, settings and update logic. |
| `lib/recovery_policy.dart` | Pure smart-recovery admission and cooldown policy; added on the recovery regression branch for unit-testable decision rules. |
| `lib/live_connection_policy.dart` | Merged pure UI connected-state gate requiring native core connected, successful live verification, and no forced-disconnect override. |
| `lib/live_connection_verifier.dart` | Injectable asynchronous settle/ping/retry sequence used by `_verifyLiveConnection`; UI state and native stop/recovery decisions remain in `main.dart`. |
| `test/live_connection_verifier_test.dart` | Deterministic async tests for silent verification, retry timing, core disconnect, stale result cancellation, and explicit-disconnect cancellation. |
| `test/recovery_policy_test.dart` | First application-owned unit suite; tests smart-recovery reason admission, intent gates, and cooldown selection. |
| `test/live_connection_policy_test.dart` | Tests the verified-connection UI gate; does not simulate asynchronous lifecycle or native VPN behavior. |
| `.github/workflows/build.yml` | Production build and GitHub Release workflow; manual dispatch only, requires main ref and explicit confirmation. |
| `.github/workflows/pr-validation.yml` | Non-production PR validation workflow on `main`; analyzes/tests the app and builds isolated validation APK artifacts. |
| `.github/workflows/project-memory-audit.yml` | Read-only CI audit of generated code index and source freshness; required on every main-targeting PR and on relevant main pushes. |
| `docs/PROJECT_MEMORY_AUTOMATION.md` | Usage, guarantees, and limitations of project-memory audit; merged in PR #4. |
| `docs/generated/jet_vpn_code_index.json` | Generated lexical Dart navigation index; merged in PR #4. |
| `tools/project_memory/index_dart.py` | Standard-library generator/checker for lexical Dart index and source fingerprint; merged in PR #4. |
| `tools/project_memory/semantic/` | Merged developer tooling: Dart AST and analyzer-resolved multi-file indexers, critical-path report generator, and focused tooling tests. Detailed generated output is a CI artifact, not committed. |
| `docs/critical_paths.json` | Curated, source-verified entrypoint anchors for connection/recovery, lifecycle, payment, and profile workflows; includes explicit native Java boundary references. |
| `tools/project_memory/semantic/lib/critical_path_report.dart` | Computes static transitive reachability from curated entrypoints using resolved internal call edges. |
| `tools/project_memory/semantic/bin/critical_paths.dart` | Generates or verifies the machine-readable critical-path report. |
| `tools/project_memory/semantic/test/critical_path_report_test.dart` | Tests transitive traversal, external/unresolved calls, and ambiguous entrypoint handling. |
| `docs/generated/jet_vpn_resolved_index.json` | Generated multi-file analyzer-resolved index; uploaded as a CI artifact, not committed. |
| `docs/generated/jet_vpn_critical_paths.json` | Generated static critical-path report; uploaded as a CI artifact, not committed. |
| `tools/v2ray_notif_patch/apply_patch.sh` | Applies repository-maintained native patch to dependency sources in build workspace. |
| `tools/v2ray_notif_patch/V2rayCoreManager.java` | Patched V2Ray core manager source. |
| `tools/v2ray_notif_patch/V2rayProxyOnlyService.java` | Patched proxy-only service source. |
| `tools/v2ray_notif_patch/V2rayVPNService.java` | Patched VPN service source, including user-initiated notification disconnect marker. |

| `tools/validation/align_validation_android.py` | Aligns the ephemeral validation Android scaffold with production SDK levels, QUERY_ALL_PACKAGES permission and package visibility queries; CI-only. |
| `tools/validation/test_align_validation_android.py` | Unit tests for Gradle Groovy/Kotlin, manifest package visibility, and idempotency of Android parity alignment. |
| `tools/validation/prepare_validation_build.py` | CI-only preparation script that creates a distinct validation package ID/label and disables the updater in the disposable validation workspace; it does not alter tracked production app source. |
| `tools/validation/test_prepare_validation_build.py` | Unit tests for validation package isolation, updater guard, idempotence, and fail-closed behavior. |
| `docs/DEVICE_VALIDATION.md` | Physical-device test protocol for cold restore, background resume, explicit disconnect during verification, and profile switch during verification. |

## Confirmed absences in the application-source snapshot

The current `main` tree contains a tracked `test/` suite and isolated semantic tooling. No backend PHP sources, Telegram bot sources, website/admin source, worker source, or JET VPN TV source are present in this repository. CI may generate Android scaffold files in its temporary workspace; that does not make them tracked application source.

## Source identity

- Current `main`: `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- `lib/main.dart`: blob `3d28693b7be8bfe309a850923599830e1a65ab59`, 9,008 lines, 352,770 UTF-8 bytes, 336,710 Unicode code points.
- `pubspec.yaml`: blob `adc3b22a4538db4738bec789e3c3badf26e4f710`, version `2.4.5+284`.
- `.github/workflows/build.yml`: blob `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`; manual release gate.
- `tools/v2ray_notif_patch/apply_patch.sh`: blob `ef603a667eded4786dd12c2fefd3650667d12ba3`.
- `tools/v2ray_notif_patch/V2rayVPNService.java`: blob `fb081e7a99b076f7bbcda47b736b8571bb12966f`.

Never add paths to this map unless verified from the current tree or a separately identified source repository.

