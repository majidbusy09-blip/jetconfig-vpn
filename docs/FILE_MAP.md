# JET VPN — Repository File Map

Snapshot: GitHub `main`, inspected 2026-11-21.

| Path | Verified purpose / contents |
|---|---|
| `README.md` | Project overview and links. Important: it describes a wider JetConfig system (bot, web admin, PHP and MySQL), but those components are not present in the current root tree inspected for this snapshot. Treat its wider-system description as documentation, not proof that those sources are in this repository. |
| `pubspec.yaml` | Flutter package metadata, app version/build, SDK constraint, dependencies. |
| `lib/main.dart` | Main Flutter application source; large monolithic file containing app entry, themes, app routing package lists, server model, main VPN screen and connection logic. |
| `.github/workflows/build.yml` | Android build and release workflow. Runs on pushes to `main` and manual dispatch. |
| `tools/v2ray_notif_patch/apply_patch.sh` | Shell script invoked by CI to patch the VPN notification integration. |
| `tools/v2ray_notif_patch/V2rayCoreManager.java` | Native Java source involved in the V2Ray core integration patch. |
| `tools/v2ray_notif_patch/V2rayProxyOnlyService.java` | Native Java source involved in the proxy-only service patch. |
| `tools/v2ray_notif_patch/V2rayVPNService.java` | Native Java source involved in the VPN service patch. |

## Current source identity

- `pubspec.yaml`: `version: 2.4.5+284`
- `lib/main.dart`: `appVersion = 'v2.4.5'`, `appVersionCode = 284`
- The two version declarations agree in this snapshot.

## Repository scope warning

Do not add assumed paths such as `bot.php`, `webadmin/`, `worker/`, or a TV app to this map unless they are confirmed in the current repository tree or a separately identified source repository. Older ZIP archives may describe a broader or older project snapshot.
