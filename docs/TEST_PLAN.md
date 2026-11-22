# JET VPN — Test Plan

> This is a planned test matrix, not a claim that tests already exist or have passed.

## Current test baseline

- The verified `main` tree at `47949178016a6ef3e855a215550b06f4eae8378d` has no `test/` directory.
- A prior PR validation workflow may build/analyze in CI, but absence of tests means no app regression suite is executed.
- No runtime/device tests were run during the documentation stage.

## Priority regression suites

### A. Connection and lifecycle (highest priority)

1. Cold launch with persisted want-connected=false: VPN stays disconnected.
2. Cold launch with want-connected=true and native disconnected: recovery starts only when network is available.
3. Resume with native CONNECTED but data path unavailable: UI must not mark verified until live verification succeeds.
4. Notification disconnect: user intent becomes false; automatic recovery does not reconnect.
5. Internal stop during recovery/server switch: must not be interpreted as explicit user disconnect.
6. Android VPN permission revoke: state reconciles without false connected UI or unintended reconnect.
7. Connect timeout: smart recovery scheduler accepts the intended reason and runs within rate limits.
8. Recovery attempt cap: maximum four attempts per 15-minute window; cooldown/slow health watch behaves as designed.
9. User presses disconnect during ping/start/recovery: generation checks prevent late reconnect.
10. Network down/up: no wasteful repeated recovery while offline; resume recovery after network returns.

### B. Profiles and local storage

1. Create, update, delete, and switch profiles.
2. Active profile switch clears previous account/server cache.
3. Cache owner marker prevents showing one account's server list under another account.
4. Legacy single-account preferences migrate into profile list.
5. Pending payment token remains bound to its originating account across profile switches.
6. Credential migration to encrypted storage preserves login and profile behavior.

### C. Purchase, renewal, and free test

1. Invoice creation for new plan and renewal action types.
2. Payment pending → approved, expired, cancelled, rejected, and network failure.
3. Repeated status polling is idempotent from the client's perspective.
4. Account switch while invoice pending does not query token using wrong account.
5. Additional service approval creates/selects the intended profile.
6. Free-test list, offer selection, already-used offer, and additional-service response.
7. Server rejects cross-account token and duplicate invoice application (requires backend test).

### D. API and credential handling

1. Form-encoded POST request encoding and timeout behavior.
2. Invalid JSON, non-2xx status, empty body, and server error handling.
3. Password migration from GET query to POST body coordinated with backend.
4. No secrets/tokens/passwords appear in logs or telemetry.

### E. Update and release

1. Metadata validation and version comparison.
2. Download interrupted/resumed, size mismatch, hash mismatch, and install permission denied.
3. APK signature/package/version compatibility.
4. CI branch PR validation does not publish Release.
5. Production release workflow requires an explicit controlled trigger after redesign.

## Test evidence format

For each run record: date, device/Android version, branch and commit SHA, exact test case, steps, expected/actual result, logs (redacted), pass/fail, and follow-up issue. Do not record credentials or payment tokens.
