# JET VPN — Physical Device Validation Checklist

## Purpose and safety

This checklist validates the recovery/live-connection changes on a real Android device. It does not validate payment, subscription fulfillment, production signing, or release compatibility.

- Install only the separately identified `JET VPN TEST` package: `com.jetconfig.vpn.jetconfig_vpn.validation`.
- Keep the production JET VPN installed. Do not uninstall it, overwrite it, or clear its data.
- The validation APK is signed with an Android Debug certificate and is not a production release.
- The validation build has its updater disabled. Do not use it to test purchases, payment, subscription renewal, or app update flows.
- The current artifact is ARM64-only. Use a compatible 64-bit Android device.

## Before testing

Record:

- Device manufacturer/model:
- Android version/build:
- Production JET VPN version:
- JET VPN TEST version (expected 2.4.5 / versionCode 2284):
- Date/time and network type (Wi-Fi/mobile operator):
- Test server/profile selected:

Confirm the production app still opens before installing the test app. After installing, confirm both app icons are present and launch independently.

## Scenarios

For each scenario, record **PASS / FAIL / BLOCKED**, exact steps, observed result, and whether real internet traffic passed through the VPN.

### 1. Cold start / restore

1. Connect JET VPN TEST and verify a real destination loads through the tunnel.
2. Force-stop the test app from Android Settings (do not clear storage).
3. Reopen it.
4. Observe whether the app restores the intended connection and performs a fresh live verification rather than showing a stale connected state.
5. Confirm traffic actually passes; do not rely only on the UI badge.

Expected: UI must not claim connected until native core state and fresh live verification agree. If verification fails, the UI should not retain a stale verified state.

### 2. Background resume

1. Connect and verify real tunneled traffic.
2. Send the app to the background for at least 30 seconds.
3. Return to the app. If practical, briefly change network state while backgrounded (for example Wi-Fi to mobile data), then return.
4. Observe fresh verification and traffic.

Expected: resume must not reuse stale ping/verification state. Record any disconnect, reconnect, delay, or false-connected display.

### 3. Explicit disconnect during in-flight verification

1. Start a connection or trigger a reconnect/verification attempt.
2. As soon as verification is underway, press Disconnect.
3. Wait at least 20 seconds.
4. Confirm the app remains disconnected and does not silently reconnect because an old async verification result arrived late.

Expected: explicit user disconnect wins; stale asynchronous work must not restore the connected UI or restart the tunnel.

### 4. Profile switch during verification

1. Start a connection/verification on profile A.
2. While verification is in progress, switch to profile B.
3. Wait for the operation to settle.
4. Confirm the final state belongs to profile B and no late result from profile A marks the app connected or overwrites the selected profile state.
5. Verify real traffic if profile B connects successfully.

Expected: stale verification from profile A is cancelled/ignored; final UI and tunnel state must correspond to the selected profile.

## Result record

| Scenario | Result | Actual behavior / evidence |
|---|---|---|
| Cold start / restore | PASS / FAIL / BLOCKED | |
| Background resume | PASS / FAIL / BLOCKED | |
| Disconnect during verification | PASS / FAIL / BLOCKED | |
| Profile switch during verification | PASS / FAIL / BLOCKED | |

## Failure evidence

If a scenario fails, capture:

- Exact timestamp and step where it failed.
- Screen recording or screenshots, if available.
- App logs around the event (redact account identifiers, tokens, and personal data).
- Whether Android reported the VPN as active.
- Whether a real destination was reachable and whether traffic was tunneled.
- Whether the production app remained unaffected.

Do not repeatedly retry a failing sequence without recording the first failure. Return the evidence before any code changes are proposed.

## Exit criteria

A scenario passes only when both UI state and real network behavior match the expected result. A green CI run, successful APK install, or connected icon alone is insufficient. Even if all four scenarios pass, this validates only the tested device/Android/network combination; broader rollout requires additional devices and review of PR #16.
