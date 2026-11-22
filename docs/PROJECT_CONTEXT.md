# JET VPN — Project Context

> Verified source snapshot: `main` at `47949178016a6ef3e855a215550b06f4eae8378d` (2026-11-22).  
> Main source blob: `lib/main.dart` = `df2914b2954d723869e4196d96f96b050618985a`.  
> App version: `2.4.5+284` (`pubspec.yaml` and matching constants in `lib/main.dart`).

## Product and repository identity

- App: **JET VPN**; related service/brand name: **JetConfig**.
- Telegram bot: [@JetConfig1bot](https://t.me/JetConfig1bot).
- Telegram information channel: [@jetconfig11](https://t.me/jetconfig11).
- In-app purchase is active; the bot remains an alternative purchase and management route. These are user/product context, not proof of backend implementation.
- This repository is the Flutter Android client. The verified recursive root tree contains only `.github/workflows/build.yml`, `README.md`, `lib/main.dart`, `pubspec.yaml`, and `tools/v2ray_notif_patch/` with three Java files and one shell script.
- No backend PHP source, Telegram bot source, admin panel, worker, Android project directory, test directory, or lockfile was present in the verified `main` tree.

## Runtime summary

- Flutter/Dart app; `main()` initializes Flutter and runs `JetConfigApp`.
- `MainVpnScreen` is stateful and owns the bulk of UI, account, subscription, server, connection, recovery, update, and support logic in the large `lib/main.dart`.
- VPN engine dependency: `flutter_v2ray_client: 3.5.0`.
- Repository-maintained native patch sources are applied to the dependency during the build workflow.
- Server APIs observed by the client use `https://majid6064.ir/api.php`, plus `sos_api.php`, `app_version.json`, and `tunnel_bypass.json`.

## Product context versus source truth

Smart routing, direct/domestic app handling, account profiles, purchase/renewal, free tests, server ping, automatic recovery, and APK update are known product areas. Before changing any behavior, verify the implementation in the current source and update the relevant technical documents.

## Collaboration contract

The repository's `AGENTS.md` is the mandatory operating contract. The short version: load project memory first, verify current source, work on isolated branches, show diffs and evidence, open PRs, and do not merge or release without explicit approval.

## External source dependencies and unknowns

- The authoritative PHP/API implementation is not present in this repository. Request/response details in `API_CONTRACT.md` are client-observed only.
- JET VPN TV is a separate project/repository and is out of scope for this repository's architecture.
- Never assume that README descriptions of a wider JetConfig ecosystem mean those source files are included here.
