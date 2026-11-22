# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `tests/async-live-verifier-20261122`  
> Inspected source-change commit: `f09b972f3a6ee2f466bcf9553f9f43672483c983`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59` (9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Durable project memory, the generated lexical code index, and the read-only memory-audit workflow are now present on `main`.
- No tracked `android/` or `pubspec.lock` in the inspected application-source snapshot. `main` still has no application test suite; review branches add `test/recovery_policy_test.dart`, `test/live_connection_policy_test.dart`, and `test/live_connection_verifier_test.dart`.
- Backend, bot, web admin, worker and TV sources are outside this repository.
- The `main` branch application source remains unchanged since source baseline `47949178016a6ef3e855a215550b06f4eae8378d`; this review branch contains the isolated recovery-policy change documented below. App version remains `2.4.5+284`.

## Pull requests observed

- PR #1: initial project-memory documentation; open, draft, unmerged; overlaps with merged PR #3 and should not be merged blindly.
- PR #2: isolated PR-validation workflow; open, ready for review, unmerged; adds only `.github/workflows/pr-validation.yml`.
- PR #3: durable agent memory and operating rules; merged into main at `477ff12fb5a82ba2b2bb3f68a268d27f679c40ab`.
- PR #4: automated code index and memory freshness audit; **merged** into main at `66b1b0127b0fc2ae58602c5cf2a69be6536466b7`.
- PR #5: manual release confirmation gate; merged at `f396f57459c9863a325f27e7d438e9456d560e92`.
- PR #6: project-memory documentation snapshot refresh; merged at current `main` `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- PR #7: disposable stale-index negative test; closed unmerged after the audit correctly rejected the stale fingerprint.
- PR #8: Dart AST tooling; open, unmerged; CI Run #40 succeeded.
- PR #9: analyzer-resolved Element graph; open, draft, unmerged; dependent on PR #8; CI Run #57 succeeded.
- PR #10: multi-file Dart resolution and critical-path report; open, draft, unmerged; dependent on PR #9 and PR #8; CI Run #58 succeeded; workflow-trigger refresh Run #65 is being revalidated.
- PR #11: recovery admission policy and first application regression tests; open, draft, unmerged; targets PR #10 branch; full CI Run [#45008026404](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008026404) succeeded, including app `flutter test`, semantic tooling tests/generation, and lexical freshness audit.
- PR #12: fresh live-connection verification on restore/resume; open, draft, unmerged, based on PR #11; full CI Run [#45008634023](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008634023) and final audit Run [#45008853860](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008853860) succeeded.
- PR #13 (current branch): extracts the asynchronous live-ping sequence behind an injectable verifier; full audit CI Run [#45011976765](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45011976765) succeeded on head `e11598dfb3978e44e01aa52a3e3afa95f87307b1`, including 15 app tests, all semantic tooling tests/generation, deterministic regeneration, lexical freshness, and both artifact uploads. Open/draft/unmerged; review pending.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; manual `workflow_dispatch` only; requires `confirm_release=true` and selected ref `main`; Java 17 / Flutter 3.27.4; signs APKs and publishes a GitHub Release.
- PR #2 validation workflow previously succeeded in run #10 (ID `44983819542`) and produced a debug APK artifact. At that time no application `test/` directory existed; PR #11 adds the first app-owned unit suite.
- PR #4's final strict project-memory audit passed in run [#44999570281](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/44999570281) on head `5508b99d1666f24bc602363f32b1eb770065518a`; all five main steps succeeded. Artifact `jet-vpn-code-index`, ID `14744947755`, retained until 2026-12-22.
- PR #10's project-memory tool suite has 10 distinct tests (3 AST, 5 resolved-indexer, 2 critical-path tests); all passed in CI Run #58. These are tooling tests, not application regression tests.
- No app build or runtime/device test was run for PRs #8–#10. PR #11's full `flutter test` and memory audit passed in Run #45008026404. The current branch's four live-connection policy tests passed in Run #45008634023; full read-only audit and both artifact uploads also passed. A passing unit test or memory audit does not prove live VPN connectivity, payment, update, or Android lifecycle behavior.

## Known high-priority risks

See `KNOWN_ISSUES.md`. Highest priorities:
1. `connect_timeout` is admitted by PR #11; full CI passed, while runtime/device recovery behavior remains unverified.
2. PR #12 removes native-state-only verification on restore/resume; unit tests and full CI passed, but device reproduction remains required.
3. Pending payment token is stored globally without an owner identity.
4. Account passwords are stored in SharedPreferences profile JSON/plain keys.
5. Login/password-change credentials are sent in GET query strings.
6. `main` still has no app regression suite; PR #11 and PR #12 introduce initial unit suites on dependent review branches.
7. Backend authorization/payment semantics remain unverified.

The previous critical risk that an ordinary push/merge to main automatically publishes a release is **resolved by PR #5**. Manual production release still requires explicit dispatch and confirmation.

## Memory freshness

This document preserves the authoritative `main` snapshot and separately records the review-branch source fingerprint above. `main` has one tracked Dart file under `lib/`; the PR #11 review branch has two (`lib/main.dart` and `lib/recovery_policy.dart`), and PR #12 adds `lib/live_connection_policy.dart`; the current PR #13 branch adds `lib/live_connection_verifier.dart` and its async test suite. The lexical index remains a navigation aid; PR #10 semantic tooling resolves every tracked Dart file and emits static critical-path reports. These outputs do not establish runtime behavior.


## Integration review snapshot — PR #16 (2026-11-22)

This section supersedes the earlier PR #13 branch snapshot above for the integrated review branch; the earlier snapshot is retained as historical evidence.

- **Branch:** `integration/memory-and-recovery-20261122`.
- **Reviewed source head before documentation refresh:** `287448bfae73d6b38e95e4944b6c23afa0ea80f4`.
- **Base main:** `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- **App version:** `2.4.5+284`; unchanged.
- **Application source:** `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`.
- **Integration diff:** 32 files; 2,762 additions / 432 deletions. It consolidates PRs #8–#13: AST and analyzer-resolved indexing, critical-path tooling, recovery policy, live-connection UI policy, asynchronous verifier, app integration, tests, and docs.
- **Latest CI on the reviewed source head:** [Run #91 / 45018162238](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45018162238) succeeded. Application tests, semantic tooling tests/generation, deterministic AST regeneration, lexical freshness, and both artifacts passed.
- **Artifacts:** code index ID `14753040563`; semantic AST/index bundle ID `14752731739`; expire 2026-12-22.
- **Source review:** no source-level blocker found in the focused review. See `docs/INTEGRATION_REVIEW.md` for the scope, verified behavior, and exact limitations.
- **Not verified:** APK build, Android emulator/device behavior, Android lifecycle integration, native V2Ray behavior, or real tunnel traffic.
- **PR state:** open, draft, unmerged. GitHub reported mergeable/clean at reviewed head. Do not merge or release without explicit user approval.
- **Deferred:** bot, payment, backend, and server changes remain out of current priority per user direction.


## APK comparison validation — 2026-11-22

- Latest integration head: `613d465774e8093d4ba38f7959406ca4c3bf2d8f` (CI workflow-only change; app version and app source unchanged).
- Non-production PR validation [Run #45021183386](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021183386) completed successfully: Flutter analysis, application tests, debug APK build, ARM64 split Release APK build, and both artifact uploads.
- Project-memory audit [Run #45021183398](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021183398) completed successfully on the same head.
- Debug artifact: `JET-VPN-debug-21`, 153,067,021 bytes; expires 2026-11-29. This is a CI smoke-test build, not a production package.
- ARM64 Release artifact: `JET-VPN-arm64-release-mode-21`, artifact ID `14753468185`, ZIP size 27,063,707 bytes; expires 2026-11-29. The contained APK `app-arm64-v8a-release.apk` is exactly 27,773,007 bytes (about 26.48 MiB).
- Downloaded and inspected the APK archive: it contains native libraries only under `lib/arm64-v8a/`; no `armeabi-v7a`, `x86`, or `x86_64` ABI libraries were present. This confirms the split-per-ABI fix worked.
- **Package identity limitation:** CI generated a temporary Android scaffold. Its reported application ID/namespace is `com.jetconfig.vpn.jetconfig_vpn`; this has not been confirmed as the production app ID. Signing compatibility is also unverified. Do not install this APK over the production JET VPN app or distribute it.
- This is a valid ARM64 size comparison build, but not yet proof of production installability or runtime VPN behavior. Next: compare the exact APK size with the installed production package and verify the production application ID/signature from the authoritative Android project/build configuration before any installation.
