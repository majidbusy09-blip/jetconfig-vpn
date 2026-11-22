# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `main`  
> Inspected commit: `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `df2914b2954d723869e4196d96f96b050618985a` (9,001 lines / 352,404 UTF-8 bytes / 336,257 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Durable project memory, the generated lexical code index, and the read-only memory-audit workflow are present on `main`.
- No tracked `android/`, `test/`, or `pubspec.lock` exists on this `main` snapshot.
- Backend, bot, web admin, worker, and JET VPN TV sources are outside this repository.
- Application source and app version have not changed since source baseline `47949178016a6ef3e855a215550b06f4eae8378d`; subsequent main commits add release safety and project-memory tooling/documentation only.

## Pull requests observed

- PR #1: initial project-memory documentation; open, draft, unmerged; overlaps with merged PR #3 and should not be merged alongside it.
- PR #2: isolated PR-validation workflow; open, ready for review, unmerged. Latest run #11 (ID `44983827682`) succeeded on its branch.
- PR #3: durable agent memory and operating rules; merged at `477ff12fb5a82ba2b2bb3f68a268d27f679c40ab`.
- PR #4: automated lexical code index and memory freshness audit; merged at `66b1b0127b0fc2ae58602c5cf2a69be6536466b7`.
- PR #5: manual release confirmation gate; merged at `f396f57459c9863a325f27e7d438e9456d560e92`.
- PR #6: post-merge status and file-map refresh; merged at current `main` `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- PR #7: disposable stale-index negative test; closed unmerged after the audit rejected the deliberately stale fingerprint.
- PR #8: AST-based Dart source index; open, unmerged; CI run #40 succeeded.
- PR #9: analyzer-resolved Element graph; open, draft, unmerged; depends on PR #8; CI run #57 succeeded.
- PR #10: multi-file resolution and static critical-path reports; open, draft, unmerged; depends on PR #9; CI run #63 succeeded.
- PR #11: recovery admission policy and first app regression tests; open, draft, unmerged; depends on PR #10; CI run #66 succeeded.
- PR #12: fresh live-connection verification on restore/resume; open, draft, unmerged; depends on PR #11; CI run #45008634023 succeeded.
- PR #13: injectable asynchronous live verifier; open, draft, unmerged; depends on PR #12; source CI run #45011976765 and final audit run #45012221316 succeeded.
- PR #14: client-side pending-payment token owner binding; open, draft, unmerged; depends on PR #13; source CI run #45013721394 and documentation audit run #45014029283 succeeded. **Further payment work is parked at the user's direction; do not extend this scope unless the user re-prioritizes it.**

PRs #8–#14 are review branches, not part of `main`. Their changes must not be described as deployed or merged. Preserve their dependency order and obtain explicit approval before merging any PR.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; manual `workflow_dispatch` only; requires `confirm_release=true` and selected ref `main`; Java 17 / Flutter 3.27.4; signs APKs and publishes a GitHub Release.
- PR #2 validation run #11 (`44983827682`) succeeded: Flutter static analysis and debug APK build passed; the test step was skipped because that revision had no `test/` directory. Debug APK artifact ID `14739381273`, retained until 2026-11-29.
- PRs #11–#14 introduce app-owned unit tests only on their unmerged review branches. They are not present on `main`.
- PR #14's final memory-audit run #45014029283 succeeded on its review branch; it is not a build or runtime/device test.
- No Android emulator/device test or real tunnel-traffic test has been performed for the reviewed changes.
- A passing build, unit test, or memory audit does not prove live VPN connectivity, payment processing, update behavior, or Android lifecycle behavior.

## Known high-priority risks

See `KNOWN_ISSUES.md`. The findings remain applicable to `main` until a reviewed fix is merged and verified. Candidate changes exist in unmerged PRs #11–#14; do not mark those issues fixed on `main` based on branch-only evidence.

The previous critical risk that an ordinary push/merge to main automatically publishes a release is **resolved by PR #5**. Manual production release still requires explicit dispatch and confirmation.

## Memory freshness

This document is authoritative for `main` commit `1f2519923cdd9f85ab280a3a4359d7ed5aed3949` and the source blob SHAs listed above. PR #6 changed documentation only; the application source and app version remain unchanged. The lexical index is a navigation aid, not a semantic call graph or proof of runtime reachability.
