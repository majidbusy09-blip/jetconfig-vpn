# JET VPN — Architecture

> Application-source baseline: `main` commit `47949178016a6ef3e855a215550b06f4eae8378d`; `lib/main.dart` blob `df2914b2954d723869e4196d96f96b050618985a`. The current main commit is `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`; the only change since the application-source baseline is the release-workflow safety gate in `.github/workflows/build.yml`.

## 1. Runtime composition

1. `main()` at `lib/main.dart:16` initializes Flutter and runs `JetConfigApp`.
2. `JetUiTheme` at lines 38–112 defines classic/jet theme data.
3. Custom painters at lines 114–347 render connection/orbit visuals.
4. `ServerModel` at lines 348–374 represents server metadata/configuration.
5. `JetConfigApp` at lines 376–392 is the root app widget.
6. `MainVpnScreen` and `_MainVpnScreenState` begin at lines 394–401. The state class is the dominant application service/controller and UI owner.

## 2. Functional areas inside the monolithic state class

| Area | Main symbols / approximate source ranges |
|---|---|
| VPN core/config | `_initCore` 666; `_ensureLocalHttpInbound` 675; `_prepareConfigForCore` 760; domain direct rules 802 |
| Smart routing / bypass | package family expansion 1232–1245; bypass cache/map/refresh 1256–1377 |
| Connection intent/native stop | stop/status helpers 1378–1599; `_verifyLiveConnection` 1606 |
| IP display and SOS | 1712–2073 |
| Subscription status/dialogs | 2074–2407 |
| Profiles and preferences | 2450–2840 |
| Support tickets | 3276–3706 |
| Account/service sync | 3707–3799 |
| Payment token and lifecycle restore | 3800–3987 |
| Payment status/free test | 3988–4235 |
| Renew and purchase plans/invoice | 4236–4593 |
| Account/server fetch and ping | 4594–4920 |
| Health monitoring and recovery | 4921–5367 |
| User connect/disconnect | `_toggleConnect` 5368–5601 |
| Dashboard and settings UI | 5602–6870 and 7715–8974 |
| APK update/download/install | 6983–7619 |

This map is a navigation aid, not a complete dependency graph. Before modifying a method, inspect its callers, shared fields, callbacks, and downstream effects.

## 3. Connection and recovery architecture

- Flutter owns user intent and UI flags, including `_userWantsConnected`, `_connectionVerified`, `isConnecting`, `_isRecovering`, and generation counters.
- `flutter_v2ray_client` starts/stops the V2Ray/Xray engine and reports native state.
- `_verifyLiveConnection` performs live verification; do not equate a native CONNECTED state with end-to-end internet verification.
- Smart health monitoring is implemented by `_startHealthWatch`, `_healthTick`, and recovery scheduling/execution methods.
- Recovery is guarded by a rolling window limit (four attempts per 15 minutes in the current source), minimum spacing, network availability, generation checks, and user-intent checks.
- Notification-originated user disconnect is distinguished in the native patch using `USER_INITIATED_DISCONNECT`, a SharedPreferences flag, and a marker file. Internal service stops are intentionally not treated as user disconnects.
- Resume restoration currently sets `_connectionVerified = true` when native status says connected without calling the same live-verification method; see `KNOWN_ISSUES.md`.

## 4. Native patch integration

The repository stores patched Java source under `tools/v2ray_notif_patch/`. The workflow runs `bash tools/v2ray_notif_patch/apply_patch.sh` after dependency installation, applying modifications to the fetched dependency in the build workspace. The patch script and all three Java files are source inputs and must be inspected together before changing notification, VPN service, or core behavior.

## 5. External services

- Main API: `https://majid6064.ir/api.php`
- SOS endpoint: `https://majid6064.ir/sos_api.php`
- Update metadata: `https://majid6064.ir/app_version.json`
- Tunnel bypass metadata: `https://majid6064.ir/tunnel_bypass.json`
- Public IP checks include external services; treat them as diagnostics, not authoritative backend APIs.

## 6. Build/release boundary

Current `.github/workflows/build.yml` at main commit `f396f57459c9863a325f27e7d438e9456d560e92` is manual-only:
- Trigger: `workflow_dispatch`; no `push: main` release trigger.
- Required input: Boolean `confirm_release`, default `false`.
- Release job runs only when the selected ref is exactly `main` and `inputs.confirm_release == true`.
- `contents: write` is scoped to the release job.
- Signed APK build and GitHub Release publication steps are preserved.

Therefore, ordinary pushes and PR merges do not publish releases. A manually dispatched run on main with explicit confirmation can publish a public GitHub Release. Do not run it without explicit user approval.

## 7. Known unknowns

- Full backend behavior and server-side authorization/payment validation.
- Full response schemas and error semantics for every API action.
- Complete native dependency behavior outside repository-maintained patches.
- Real device behavior across Android versions and VPN permission/revoke scenarios.
