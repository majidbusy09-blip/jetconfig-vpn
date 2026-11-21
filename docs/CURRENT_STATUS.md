# JET VPN — Current Status

Snapshot date: 2026-11-21  
Inspected branch: `main`  
Repository: `majidbusy09-blip/jetconfig-vpn`

## Verified

- The repository is currently a Flutter Android app source repository.
- App version in `pubspec.yaml`: `2.4.5+284`.
- Matching constants in `lib/main.dart`: `v2.4.5` and code `284`.
- Main application source is `lib/main.dart` (about 336 KB in the inspected snapshot).
- VPN engine package: `flutter_v2ray_client: 3.5.0`.
- Build workflow: `.github/workflows/build.yml`.
- Workflow triggers on push to `main` and manual dispatch.
- CI uses Java 17 and Flutter 3.27.4 and configures Android SDK/build tools 35.
- Native notification patch files exist under `tools/v2ray_notif_patch/`.

## Not verified in this inspection

- No runtime build or device test was run as part of preparing this document.
- No full function-by-function audit of `main.dart` has been completed.
- Backend, Telegram bot, web admin, Cloudflare workers, and JET VPN TV sources were not present in the inspected repository root/tree.
- README references a broader PHP/MySQL system; those files were not present in this repository tree snapshot.

## Development branch created

`docs/jet-project-memory-20261121`

This branch was created from `main` after GitHub App write access was enabled. The initial project-memory documentation is being added here only. No change has been made to `main`, and no release was triggered by creating the branch.

## Next recommended work

1. Complete a structured map of classes, methods, state variables, API endpoints, and persistence keys in `lib/main.dart`.
2. Inspect the entire native patch script and Java diffs to document exact patch behavior.
3. Review the remaining build workflow, especially release naming/tagging and artifact upload behavior.
4. Establish a test/build baseline on this branch before making functional code changes.
5. Identify and link the current authoritative backend repository or hosting source separately, if backend work is in scope.
