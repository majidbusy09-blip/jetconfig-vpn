# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `main`  
> Inspected commit: `f396f57459c9863a325f27e7d438e9456d560e92`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `df2914b2954d723869e4196d96f96b050618985a` (9,002 lines / 336,260 characters)  
> `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`  
> `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`

## Verified repository state

- Flutter Android client; recursive tree contained 13 entries (8 files and 5 directories) at the inspected application-source snapshot.
- Main app source is concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`.
- Native patch files exist under `tools/v2ray_notif_patch/`.
- No tracked `android/`, `test/`, or `pubspec.lock` in `main`.
- Backend, bot, web admin, worker and TV sources are outside this repository.
- The application source and app version have not changed between the source baseline `47949178016a6ef3e855a215550b06f4eae8378d` and current main `f396f57459c9863a325f27e7d438e9456d560e92`; the latter adds the release safety gate only.

## Pull requests observed

- PR #1 `Add JET VPN project memory and development documentation`: open, draft, unmerged; branch `docs/jet-project-memory-20261121`; initial documentation overlaps with PR #3. Do not merge both blindly.
- PR #2 `Add isolated JET VPN PR validation workflow`: open, ready for review, unmerged; branch `ci/jet-vpn-pr-validation-20261122`; adds only `.github/workflows/pr-validation.yml`.
- PR #3 `Establish durable JET VPN agent memory and operating rules`: this PR; open, draft, unmerged; branch `docs/agent-memory-foundation-20261122`. Its documentation is being refreshed to the current main state.
- PR #4 `Add automated JET VPN code index and memory freshness audit`: open, draft, unmerged; branch `tools/project-memory-index-20261122`; based on PR #3 and must be rechecked/rebased after PR #3 is finalized.
- PR #5 `Require explicit confirmation before publishing JET VPN releases`: merged into main; merge commit `f396f57459c9863a325f27e7d438e9456d560e92`.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; manual `workflow_dispatch` only; requires `confirm_release=true` and selected ref `main`; Java 17 / Flutter 3.27.4; signs APKs and publishes a GitHub Release.
- PR #2 validation workflow previously succeeded in run #10 (ID `44983819542`) and produced a debug APK artifact. It did not execute an app test suite because the repository has no `test/` directory. Recheck the live run before relying on it for a future change.
- No runtime/device test was run for this documentation refresh.
- A passing debug build does not prove VPN connection, payment, update, or Android lifecycle behavior.

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

This document is authoritative for the exact main SHA and file blob SHAs listed above. The application implementation details in the architecture/API/storage/payment documents remain based on the unchanged `lib/main.dart` blob. After any application-source merge, refresh the commit SHA, version, tree, file blob SHAs, and affected line ranges before using this status as current.
