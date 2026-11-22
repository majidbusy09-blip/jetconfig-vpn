# JET VPN — Current Status

> Snapshot date: 2026-11-22  
> Repository: `majidbusy09-blip/jetconfig-vpn`  
> Inspected branch: `main`  
> Inspected commit: `47949178016a6ef3e855a215550b06f4eae8378d`  
> App version: `2.4.5+284`  
> `lib/main.dart` blob: `df2914b2954d723869e4196d96f96b050618985a` (9,002 lines / 336,260 characters)

## Verified repository state

- Flutter Android client; recursive tree contained 13 entries (8 files and 5 directories) at this snapshot.
- Main app source is concentrated in `lib/main.dart`.
- Dependency: `flutter_v2ray_client: 3.5.0`.
- Native patch files exist under `tools/v2ray_notif_patch/`.
- No tracked `android/`, `test/`, or `pubspec.lock` in `main`.
- Backend, bot, web admin, worker and TV sources are outside this repository snapshot.

## Pull requests observed before this memory PR

- PR #1 `Add JET VPN project memory and development documentation`: open, draft, unmerged; branch `docs/jet-project-memory-20261121`; 5 docs files.
- PR #2 `Add isolated JET VPN PR validation workflow`: open, unmerged; branch `ci/jet-vpn-pr-validation-20261122`; only `.github/workflows/pr-validation.yml`.
- Neither PR is part of `main`. Their proposed changes must not be assumed present in the default branch.

## Build and test baseline

- Production workflow: `.github/workflows/build.yml`; push to `main` and manual dispatch; Java 17 / Flutter 3.27.4; signs APKs and publishes GitHub Release.
- PR #2 validation workflow succeeded in a previous run as recorded in conversation context; it built a debug APK. It did not execute an actual test suite because the repository has no `test/` directory. Verify the live run again before relying on that result.
- No runtime/device test was run for this documentation task.
- The existence of a passing debug build does not prove VPN connection, payment, update, or Android lifecycle behavior.

## Known high-priority risks

See `KNOWN_ISSUES.md`. Highest priorities are:
1. `connect_timeout` recovery reason is not in the scheduler allowlist.
2. Resume restore can mark connection verified from native state alone.
3. Pending payment token is stored globally without an owner identity.
4. Account passwords are stored in SharedPreferences profile JSON/plain keys.
5. Login/password-change credentials are sent in GET query strings.
6. Merging to `main` can trigger automatic production release.

## Memory freshness

This document is authoritative only for the exact `main` SHA above. After any source merge, refresh the commit SHA, version, tree, file blob SHAs, and affected line ranges before using this status as current.
