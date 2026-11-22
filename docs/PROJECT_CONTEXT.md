# JET VPN — Project Context

> Current verified repository snapshot: `main` at `eae477a89816a5cfd475c596e166d5cb2575884a` (2026-11-22).  
> PR #16 merged at `c4f7f4743b3c6ffc64d34a0efb0c19f41b236f1e`; PR #17 merged at `eae477a89816a5cfd475c596e166d5cb2575884a`.  
> Main source blob: `lib/main.dart` = `3d28693b7be8bfe309a850923599830e1a65ab59`.  
> App version: `2.4.5+284` (`pubspec.yaml` blob `adc3b22a4538db4738bec789e3c3badf26e4f710`).  
> Project-memory audit run #45029689706 passed on the current main commit.  
> Active `main-protection` ruleset protects only the default branch and requires PR + memory-audit status check.
 
## Product and repository identity

- App: **JET VPN**; related service/brand name: **JetConfig**.
- Telegram bot: [@JetConfig1bot](https://t.me/JetConfig1bot).
- Telegram information channel: [@jetconfig11](https://t.me/jetconfig11).
- In-app purchase is active; the bot remains an alternative purchase and management route. These are user/product context, not proof of backend implementation.
- This repository is the Flutter Android client. The inspected application-source tree contains `.github/workflows/build.yml`, `README.md`, `lib/main.dart`, `pubspec.yaml`, and `tools/v2ray_notif_patch/` with three Java files and one shell script.
- The current main tree contains tracked application tests under `test/` and developer tooling under `tools/project_memory/`. No backend PHP source, Telegram bot source, admin panel, worker, or JET VPN TV source is present in this repository. CI may generate Android scaffold files in its temporary workspace; those generated files are not tracked application source.

## Runtime summary

- Flutter/Dart app; `main()` initializes Flutter and runs `JetConfigApp`.
- `MainVpnScreen` is stateful and owns the bulk of UI, account, subscription, server, connection, recovery, update, and support logic in the large `lib/main.dart`.
- VPN engine dependency: `flutter_v2ray_client: 3.5.0`.
- Repository-maintained native patch sources are applied to the dependency during the build workflow.
- Server APIs observed by the client use `https://majid6064.ir/api.php`, plus `sos_api.php`, `app_version.json`, and `tunnel_bypass.json`.

## Product context versus source truth

Smart routing, direct/domestic app handling, account profiles, purchase/renewal, free tests, server ping, automatic recovery, and APK update are known product areas. Before changing any behavior, verify the implementation in the current source and update the relevant technical documents.

## Collaboration contract

The repository's `AGENTS.md` is the mandatory operating contract. Before prioritizing work, apply the collaborator-priority test stated there. The short version: load project memory first, verify current source, work on isolated branches, show diffs and evidence, open PRs, and do not merge or release without explicit approval.

## Release workflow

The production workflow `.github/workflows/build.yml` is manual-only after merged PR #5: `workflow_dispatch`, selected ref `main`, and explicit `confirm_release=true` are required. Ordinary pushes and PR merges do not publish a Release. A confirmed manual run can publish signed APKs and a public GitHub Release; never trigger it without explicit approval.

## External source dependencies and unknowns

- The authoritative PHP/API implementation is not present in this repository. Request/response details in `API_CONTRACT.md` are client-observed only.
- JET VPN TV is a separate project/repository and is out of scope for this repository's architecture.
- Never assume that README descriptions of a wider JetConfig ecosystem mean those source files are included here.
