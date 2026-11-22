# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `tests/recovery-regression-20261122`  
> Inspected source-change commit: `b7101afa870262ca116ebb9fcf7e6ab4b9df00cc`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `dc1d0832d55c412d7a475cc596d6b20bd611cf38` (8,997 lines / 352,351 UTF-8 bytes / 336,225 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Durable project memory, the generated lexical code index, and the read-only memory-audit workflow are now present on `main`.
- No tracked `android/` or `pubspec.lock` in the inspected application-source snapshot. `main` still has no application test suite; this branch adds `test/recovery_policy_test.dart` as the first app-owned unit test.
- Backend, bot, web admin, worker and TV sources are outside this repository.
- Application source and app version have not changed since source baseline `47949178016a6ef3e855a215550b06f4eae8378d`; subsequent main commits add release safety and project-memory tooling/documentation only.

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
- PR #10: multi-file Dart resolution and critical-path report; open, draft, unmerged; dependent on PR #9 and PR #8; CI Run #58 succeeded.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; manual `workflow_dispatch` only; requires `confirm_release=true` and selected ref `main`; Java 17 / Flutter 3.27.4; signs APKs and publishes a GitHub Release.
- PR #2 validation workflow previously succeeded in run #10 (ID `44983819542`) and produced a debug APK artifact. It did not execute an app test suite because the repository has no `test/` directory.
- PR #4's final strict project-memory audit passed in run [#44999570281](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/44999570281) on head `5508b99d1666f24bc602363f32b1eb770065518a`; all five main steps succeeded. Artifact `jet-vpn-code-index`, ID `14744947755`, retained until 2026-12-22.
- PR #10's project-memory tool suite has 10 distinct tests (3 AST, 5 resolved-indexer, 2 critical-path tests); all passed in CI Run #58. These are tooling tests, not application regression tests.
- No app build or runtime/device test was run for PRs #8–#10. This branch adds a `flutter test` CI step; its result is pending until the branch workflow runs. A passing unit test or memory audit does not prove live VPN connectivity, payment, update, or Android lifecycle behavior.

## Known high-priority risks

See `KNOWN_ISSUES.md`. Highest priorities:
1. `connect_timeout` recovery reason is not in the scheduler allowlist.
2. Resume restore can mark connection verified from native state alone.
3. Pending payment token is stored globally without an owner identity.
4. Account passwords are stored in SharedPreferences profile JSON/plain keys.
5. Login/password-change credentials are sent in GET query strings.
6. No repository-owned automated regression test suite exists.
7. Backend authorization/payment semantics remain unverified.

The previous critical risk that an ordinary push/merge to main automatically publishes a release is **resolved by PR #5**. Manual production release still requires explicit dispatch and confirmation.

## Memory freshness

This document is authoritative for the exact main SHA and file blob SHAs listed above. The application implementation details in architecture/API/storage/payment documents remain based on the unchanged `lib/main.dart` blob. The lexical index remains a navigation aid for `lib/main.dart`; the proposed semantic tooling in PR #10 resolves every tracked Dart file under `lib/` (currently one file) and emits curated static critical-path reports. These outputs do not establish runtime behavior.
