# JET VPN — Current Status

## Latest verified snapshot — 2026-11-22 (supersedes older status entries below)

- PR #16 current head: `8f8da63cb4cd687ee1e35a452d6d695a2043084d`; branch `integration/memory-and-recovery-20261122`; base `main` at `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- Application source SHA remains `8571a10a8676bf114ca6eda07657da026e550085`; commits after that source snapshot are documentation-only.
- PR #16 is open, Draft, unmerged, and GitHub reports it mergeable. Diff: 38 files, 3,528 additions, 453 deletions.
- Project-memory audit run [#45026323360](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323360) **succeeded** on the exact current head. Application regression tests, AST indexer tests, resolved-element indexer tests, critical-path tests, deterministic semantic generation, lexical index freshness, and both artifact uploads passed.
- Non-production PR validation run [#45026323476](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323476) **succeeded** on the exact current head. Validation-preparation tests, Flutter analysis, app tests, debug smoke build, split ARM64 release-mode build, package/label/signature/ABI checks, and artifact uploads passed.
- Latest ARM64 test artifact: `JET-VPN-TEST-arm64-validation-69`, artifact ID `14756425339`, ZIP size 27,040,234 bytes, expires 2026-11-29. It is an isolated test APK, not production-signed and not for distribution or updating production.
- Latest semantic artifacts: `jet-vpn-code-index` ID `14755568224` and `jet-vpn-semantic-ast-index` ID `14755153930`, both retained until 2026-12-22.
- User-reported device tests passed for all four scenarios: cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device model/build and diagnostic logs were not supplied; do not generalize beyond the tested environment.
- PR review submissions: none. Inline review threads: none.
- Final scoped diff review found no source-level blocker in the inspected VPN verifier/recovery integration, validation workflow, or project-memory workflow. CI does not prove all Android/device/network conditions.
- Production source on `main`, app version `2.4.5+284`, payment, bot, backend, server configuration, and production release workflow remain outside this PR's changes. No merge, release, or deployment has occurred.
- Next action: present the merge recommendation and wait for explicit user approval. Do not merge, mark ready, release, deploy, or dispatch the production workflow without that approval.

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Current inspected branch: `integration/memory-and-recovery-20261122`  
> Current inspected application/validation source commit: `8571a10a8676bf114ca6eda07657da026e550085` (subsequent commits in this stage are documentation-only)  
> Base main: `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59` (9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`

## Current verified integration snapshot

- PR #16 is open, draft, unmerged, and reported mergeable at inspected head `895124409f2c6a302e2ede3c73ccd3af54c747a0`.
- PR validation [Run #45021900956](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900956) passed: Flutter analysis, app tests, debug APK build, ARM64 split Release-mode comparison APK build, and artifact uploads.
- Project-memory audit [Run #45021900965](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900965) passed: app regression tests, AST and resolved-element tooling tests, deterministic generation, critical-path report, lexical freshness, and artifact uploads.
- Latest debug artifact: `JET-VPN-debug-25`, 153,067,024 bytes; artifact ID `14754525304`; expires 2026-11-29. It is a CI smoke-test build, not a suitable install candidate.
- Latest ARM64 comparison artifact: `JET-VPN-arm64-release-mode-25`, artifact ID `14754511282`; ZIP size 27,063,719 bytes; expires 2026-11-29. Its contained APK is 27,773,007 bytes (about 26.48 MiB) and contains native libraries only under `lib/arm64-v8a/`.
- Production package ID is derived from the production workflow's Android scaffold command: `flutter create . --platforms=android --project-name=jetconfig_vpn --org com.jetconfig.vpn`, which generates `com.jetconfig.vpn.jetconfig_vpn`. CI reported the same generated ID. This is workflow-derived evidence, not a package dump from the user's installed device.
- The comparison APK is signed with the Android Debug certificate. The production release workflow decodes the configured release keystore and signs production builds. The signing fingerprints have **not** been compared; the comparison APK must not be installed as an update over the production app.
- No production release, deployment, or merge has occurred. Main app source and version remain unchanged by the CI size investigation.

## Immediate safety boundary

- The 26.48 MiB APK proves the split-per-ABI build output is lean and ARM64-only; it does not prove production signing, installation compatibility, or live VPN behavior.
- Do not install this comparison APK over the installed JET VPN.
- The next useful device-validation path is a separately identified validation package (distinct application ID), signed with a test key, so it can coexist with the production app. It must be clearly labeled as a test build and must not publish or update production.

## Historical source snapshot — pre-integration (superseded by the current snapshot above)

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Durable project memory, the generated lexical code index, and the read-only memory-audit workflow are now present on `main`.
- No tracked `android/` or `pubspec.lock` in the inspected application-source snapshot. `main` still has no application test suite; review branches add `test/recovery_policy_test.dart`, `test/live_connection_policy_test.dart`, and `test/live_connection_verifier_test.dart`.
- Backend, bot, web admin, worker and TV sources are outside this repository.
- The `main` branch application source remains unchanged since source baseline `47949178016a6ef3e855a215550b06f4eae8378d`; this review branch contains the isolated recovery-policy change documented below. App version remains `2.4.5+284`.

## Historical pull-request snapshot — superseded by current PR state above

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

## Historical build and test baseline

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


## Isolated device-validation APK — 2026-11-22 (latest verified)

- **Source head:** `8571a10a8676bf114ca6eda07657da026e550085`; PR #16 remains open, draft, and unmerged.
- **PR validation:** [Run #45023210674](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210674) succeeded end-to-end: validation-tool unit tests, Flutter analysis, app tests, debug smoke build, ARM64 split Release-mode APK build, package/label/signature/ABI verification, and artifact upload.
- **Project-memory audit:** [Run #45023210902](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210902) succeeded on the validation-build change set.
- **Artifact:** `JET-VPN-TEST-arm64-validation-42`, artifact ID `14754751347`, ZIP size 27,040,223 bytes, expires 2026-11-29 12:43:53 UTC. Contains `app-arm64-v8a-release.apk` (27,748,544 bytes; about 26.46 MiB).
- **Verified APK identity:** package `com.jetconfig.vpn.jetconfig_vpn.validation`; label `JET VPN TEST`; versionName `2.4.5`; versionCode `2284`; native ABI set exactly `arm64-v8a`.
- **Signature:** Android APK Signature Scheme v1 and v2 verification passed; one signer, `CN=Android Debug`; certificate SHA-256 `524cfda67adac575c959bdeaf99484cd5f0f1a260a87a275cd84f2f6d833fdf9`. This is a test certificate, not the production release key.
- **Isolation safeguards:** validation-only build preparation changes the generated package ID and label and injects a compile-time updater guard in the ephemeral CI workspace. The tracked production `lib/main.dart`, production package configuration, and `.github/workflows/build.yml` are not modified by this validation-only preparation step. The validation app's update check is disabled.
- **Local archive inspection:** ZIP contains exactly one APK; APK contains native libraries only in `lib/arm64-v8a/`.
- **Device/runtime status:** not yet installed or exercised on a physical device. This artifact is suitable only for side-by-side validation, not production distribution or upgrading the production app. Do not test purchases/payments in this build.
- **Next:** use `docs/DEVICE_VALIDATION.md` to install alongside production and record cold start/restore, background resume, disconnect during verification, and profile-switch during verification. Record device model and Android version. Do not merge or release before device evidence and explicit user approval.


## Physical-device validation — user-reported success (2026-11-22)

- **Result:** user reports that all four scenarios in `docs/DEVICE_VALIDATION.md` were tested and everything worked: cold start/restore, background resume, explicit disconnect during verification, and profile switch during verification.
- **Evidence type:** user-reported manual test result; no device logs or screen recording were supplied. Device model, Android build, network type, and test profile are not yet recorded. Do not infer these from the ChatGPT client metadata.
- **Interpretation:** this is positive physical-device evidence for the tested environment, in addition to successful CI and APK identity/signature/ABI checks. It is not a broad compatibility claim across Android versions/devices or proof of every native tunnel edge case.
- **PR #16:** open, draft, unmerged, and reported mergeable at the latest inspection. Application/validation source SHA remains `8571a10a8676bf114ca6eda07657da026e550085`; later commits in this stage are documentation-only. The PR contains 38 changed files and 3,479 additions / 453 deletions at the reviewed snapshot.
- **Latest completed CI:** PR validation [Run #45024183497](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45024183497) and project-memory audit [Run #45024183512](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45024183512) both succeeded on the documentation snapshot at `eefde6baa1556e56c11ce4c872ca4cdd9cee3722`. Project-memory audit [Run #45026094298](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026094298) subsequently passed on this documentation head. The non-production validation run [#45026094310](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026094310) was created but remained queued at the time of this snapshot; the application/validation source is unchanged from the already successful validation run #45024183497.
- **PR review state:** no submitted PR reviews or inline review threads were returned at the latest review-list check.
- **Next:** finish final source/diff review, then verify CI on the latest documentation head and present a merge recommendation for explicit approval. Do not merge, release, or deploy automatically.
