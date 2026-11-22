# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `main`  
> Inspected commit: `477ff12fb5a82ba2b2bb3f68a268d27f679c40ab`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `df2914b2954d723869e4196d96f96b050618985a` (9,001 lines / 352,404 UTF-8 bytes / 336,257 Unicode code points)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; application source remains concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`; native patch files exist under `tools/v2ray_notif_patch/`.
- Project memory is tracked in `AGENTS.md` and `docs/`; lexical index and audit tooling are proposed in PR #4.
- No tracked `android/`, `test/`, or `pubspec.lock` in the inspected application-source snapshot.
- Backend, bot, web admin, worker and TV sources are outside this repository.
- Application source and app version have not changed since source baseline `47949178016a6ef3e855a215550b06f4eae8378d`; subsequent main commits add release safety and project-memory documentation only.

## Pull requests observed

- PR #1: initial project-memory documentation; open, draft, unmerged; overlaps with merged PR #3 and should not be merged blindly.
- PR #2: isolated PR-validation workflow; open, ready for review, unmerged; adds only `.github/workflows/pr-validation.yml`.
- PR #3: durable agent memory and operating rules; **merged** into main at `477ff12fb5a82ba2b2bb3f68a268d27f679c40ab`.
- PR #4: automated code index and memory freshness audit; open, ready for review, rebased onto current main. Fresh strict audit run #44999404369 passed on head `37e9d0fa92661ac7cb7c9c9e9d52c8d11dd3f5e9`.
- PR #5: manual release confirmation gate; merged at `f396f57459c9863a325f27e7d438e9456d560e92`.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; manual `workflow_dispatch` only; requires `confirm_release=true` and selected ref `main`; Java 17 / Flutter 3.27.4; signs APKs and publishes a GitHub Release.
- PR #2 validation workflow previously succeeded in run #10 (ID `44983819542`) and produced a debug APK artifact. It did not execute an app test suite because the repository has no `test/` directory.
- PR #4's fresh project-memory audit passed in run [#44999404369](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/44999404369) on the rebased PR head. The lexical index and CURRENT_STATUS source fingerprint/metrics matched; artifact ID `14745610539`, retained until 2026-12-22.
- No runtime/device test was run for this documentation and tooling work. A passing build or memory audit does not prove VPN connection, payment, update, or Android lifecycle behavior.

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

This document is authoritative for the exact main SHA and file blob SHAs listed above. The application implementation details in architecture/API/storage/payment documents remain based on the unchanged `lib/main.dart` blob. The project-memory audit verifies the generated lexical index and source fingerprint/size metrics; it does not establish semantic call relationships or runtime behavior.
