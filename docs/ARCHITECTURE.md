# JET VPN — Verified Architecture Notes

> Prepared from the GitHub `main` snapshot inspected on 2026-11-21. This is a source-grounded initial map, not a complete reverse-engineered specification.

## Runtime and framework

- Flutter / Dart application.
- Package name: `jet_vpn`.
- Dart SDK constraint: `>=3.1.0 <4.0.0`.
- Flutter CI version: `3.27.4` (see `.github/workflows/build.yml`).
- Main application entry point: `lib/main.dart`.
- Android VPN engine dependency: `flutter_v2ray_client: 3.5.0`.

## Main runtime composition

The inspected `lib/main.dart` begins with:

1. Flutter binding initialization and `runApp(const JetConfigApp())`.
2. Global app metadata/constants, including version, update metadata URL, bypass metadata URL, logo URL, Telegram bot/channel URLs, and SOS API URL.
3. `JetUiTheme`, with `classic` and `jet` themes.
4. Custom painters for neon connection/orbit visuals.
5. Package lists for default domestic/direct-routing apps and selectable VPN apps.
6. `ServerModel` for server metadata.
7. `JetConfigApp` and `MainVpnScreen`.
8. A `V2ray` instance with an `onStatusChanged` callback inside the main screen state.

The main file is large (approximately 336 KB in the inspected snapshot) and currently concentrates substantial UI, connection-state, routing, and service logic. Do not assume a modular feature-folder architecture.

## External packages declared in pubspec

- `flutter_v2ray_client: 3.5.0`
- `http: ^1.2.0`
- `shared_preferences: ^2.2.2`
- `url_launcher: ^6.2.5`
- `percent_indicator: ^4.2.3`
- `path_provider: ^2.1.2`
- `open_filex: ^4.4.0`
- `installed_apps: ^2.2.1`
- Flutter test and Flutter lints in dev dependencies.

## Native notification patch

The repository includes:

- `tools/v2ray_notif_patch/V2rayCoreManager.java`
- `tools/v2ray_notif_patch/V2rayProxyOnlyService.java`
- `tools/v2ray_notif_patch/V2rayVPNService.java`
- `tools/v2ray_notif_patch/apply_patch.sh`

The workflow invokes the patch script in the build pipeline under the step named “Patch VPN notification (disconnect + ping)”. Inspect the script and exact patch targets before changing this integration.

## CI/build pipeline (verified at a high level)

Workflow file: `.github/workflows/build.yml`.

- Triggers: push to `main`, and manual `workflow_dispatch`.
- Declares `contents: write`.
- Uses Ubuntu, Java 17, Flutter 3.27.4.
- Installs Android platform/build tools 35.
- Generates Android project files if the `android` directory is absent.
- Sets app label and icon from the configured remote logo.
- Applies FileProvider/install-permission configuration.
- Runs `flutter pub get` and the native notification patch.
- Reads signing material from GitHub Actions secrets; never copy or expose those values in docs/logs.
- Builds release APK variants and prepares release artifacts.

Because push to `main` triggers this workflow, never commit directly to `main` during ordinary development.

## Important unknowns / follow-up reverse engineering

- Full function/class map and state ownership inside `lib/main.dart`.
- Exact subscription API request/response contracts.
- Full connection/recovery state machine and timing invariants.
- Remote update and bypass metadata schemas.
- Full workflow release/tag behavior after artifact preparation.
- Runtime behavior on physical devices; source inspection alone is not a device test.
