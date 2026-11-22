# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `tests/live-verification-resume-20261122`  
> Inspected source-change commit: `6679e4b69e2d26338b1245536dec889b67374462`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `a2483f2bb90e528a70440978ac62b9f58264c778` (9,016 lines / 352,934 UTF-8 bytes / 336,842 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Durable project memory, the generated lexical code index, and the read-only memory-audit workflow are now present on `main`.
- No tracked `android/` or `pubspec.lock` in the inspected application-source snapshot. `main` still has no application test suite; review branches add `test/recovery_policy_test.dart` and `test/live_connection_policy_test.dart`.
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
- PR #13 (current branch): extracts the asynchronous live-ping sequence behind an injectable verifier and adds deterministic async tests; based on PR #12, pending CI/review.

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
