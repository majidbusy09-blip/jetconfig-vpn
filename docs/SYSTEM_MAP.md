# JET VPN — System Map

 > Source baseline: `main` `eae477a89816a5cfd475c596e166d5cb2575884a`; `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59` (verified 2026-11-22). Historical line references below have not yet been revalidated against this blob; re-fetch source before relying on a line number.

## Component map

```text
Flutter entry point (main)
  └── JetConfigApp
       └── MainVpnScreen
            └── _MainVpnScreenState
                 ├── UI / dashboard / settings
                 ├── account + profile persistence
                 ├── API client calls (HTTP)
                 ├── server list + ping selection
                 ├── connection intent + state verification
                 ├── smart health monitor + recovery
                 └── update download/install
                       │
                       ├── SharedPreferences
                       ├── HTTP API: majid6064.ir
                       └── flutter_v2ray_client
                              └── native V2Ray/Xray service
                                  (patched by tools/v2ray_notif_patch)
```

## Main ownership

| Component | Responsibility | Evidence |
|---|---|---|
| `main()` | Flutter initialization and root app launch | `lib/main.dart:16` |
| `JetConfigApp` | Root Material app/theme | `lib/main.dart:376–392` |
| `ServerModel` | Server name/host/port/protocol/config/ping | `lib/main.dart:348–374` |
| `MainVpnScreen` | Stateful screen and lifecycle observer | `lib/main.dart:394–401` |
| `_MainVpnScreenState` | Main application state and feature orchestration | `lib/main.dart:401 onward` |
| `_initCore` | Initializes V2Ray client callback | `lib/main.dart:666` |
| `_fetchUserData` | Authenticated account/server fetch and cache update | `lib/main.dart:4594–4713` |
| `_verifyLiveConnection` | Live connection verification | `lib/main.dart:1606` |
| `_healthTick` | Smart connection health checks | `lib/main.dart:4980` |
| `_scheduleSmartRecovery` / `_runSmartRecovery` | Recovery admission and recovery sequence | `lib/main.dart:5114–5291` |
| `_toggleConnect` | User connect/disconnect orchestration | `lib/main.dart:5368` |
| Native `V2rayVPNService` patch | Distinguishes user notification disconnect from internal stop | `tools/v2ray_notif_patch/V2rayVPNService.java:109–133` |

## State groups to trace together

- User intent: `_userWantsConnected`, persisted intent key (resolve current constant before editing).
- UI/verification: `isConnecting`, `_connectionVerified`, `_uiForceDisconnected`, `_isVpnConnected`.
- Recovery coordination: `_isRecovering`, `_recoveryGen`, `_connectGen`, `_verifyGen`, recovery timestamps/window counters.
- Native/user stop: `_weInitiatedStop`, `v2ray_user_stop`, `flutter.v2ray_user_stop`, marker file `jet_vpn_user_stop`.
- Lifecycle: `didChangeAppLifecycleState`, `_restoreWantConnectedAfterLoad`, `_reconcileVpnStateOnResume`.

Do not edit one state group in isolation without tracing all reads/writes and callback paths.
