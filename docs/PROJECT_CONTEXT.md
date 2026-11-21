# JET VPN — Project Context

> Snapshot date: 2026-11-21  
> Source of truth: GitHub `main` at the time this document was prepared.  
> Verified app version: `2.4.5+284` (`pubspec.yaml`, corroborated by constants in `lib/main.dart`).

## Product identity

- App name: **JET VPN**.
- Related brand/system name: **JetConfig**.
- Telegram bot: [@JetConfig1bot](https://t.me/JetConfig1bot).
- Telegram information channel: [@jetconfig11](https://t.me/jetconfig11).
- In-app purchases are active; the Telegram bot remains an alternative route for purchase and subscription management.

## What this repository currently contains

The current GitHub repository is an Android Flutter application repository. The root tree inspected on 2026-11-21 contains:

- `lib/main.dart`
- `pubspec.yaml`
- `.github/workflows/build.yml`
- `tools/v2ray_notif_patch/` (three Java source files and a shell patch script)
- `README.md`

Do not assume that the bot, web admin, PHP backend, Cloudflare workers, or TV app are present in this repository. They may exist in separate repositories/hosting locations or in older project archives.

## Collaboration requirements

1. Treat the current GitHub source as authoritative for the Android app, not an older ZIP snapshot.
2. Before editing, inspect the current branch head and the relevant source files.
3. Work on a feature/docs branch, never directly on `main`.
4. Review the diff and relevant build/test results before opening or updating a PR.
5. Never merge a PR or push to `main` without the user's explicit approval.
6. Avoid version/build-number changes unless the user requests a release or the change requires it.
7. Do not claim a test passed unless it was actually run and its result inspected.
8. Do not invent missing architecture details. Mark unknowns and ask for source evidence when needed.

## Safety and release warning

The workflow at `.github/workflows/build.yml` runs on pushes to `main` and can publish release artifacts. A merge or push to `main` may therefore trigger a build/release. Keep all development work isolated until approved.

## Known project context from user

- Smart Mode / Smart Routing separates selected domestic apps from tunneled apps.
- The app uses the V2Ray/Xray engine through `flutter_v2ray_client`.
- User-facing capabilities discussed include subscription management, ping checks, reconnect/recovery behavior, app-based routing, and update handling.
- Treat these as product context; confirm exact implementation in the current source before modifying a feature.
