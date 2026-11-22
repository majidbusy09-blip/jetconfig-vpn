# JET VPN — Test Plan

> This is a planned test matrix, not a claim that tests already exist or have passed.

## Current test baseline

- Current `main` is `abdff3a59b89419e869c98d7dbb4ac91512fe950`; PR #16, #17, and #19 are merged.
- Application regression tests exist under `test/`; the project-memory workflow runs `flutter test` after resolving root Flutter dependencies.
- The isolated semantic tooling package has tests for AST indexing, analyzer-resolved indexing, and critical-path reporting.
- Project-memory audit after PR #19 [#45065541236](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541236) passed; non-production PR validation [#45065541255](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541255) also passed.
- User-reported device tests passed for cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device/build/log details were not supplied.
- Unit tests and CI do not replace Android lifecycle, VPN-engine, network, payment, or backend integration tests.

## Priority regression suites

### A. Connection and lifecycle (highest priority)

1. Cold launch with persisted want-connected=false: VPN stays disconnected.
2. Cold launch with want-connected=true and native disconnected: recovery starts only when network is available.
3. Resume with native CONNECTED but data path unavailable: UI must not mark verified until live verification succeeds. The pure UI-gate test is part of the merged regression suite; lifecycle/device coverage remains limited to the user-reported scenarios above.
4. Notification disconnect: user intent becomes false; automatic recovery does not reconnect.
5. Internal stop during recovery/server switch: must not be interpreted as explicit user disconnect.
6. Android VPN permission revoke: state reconciles without false connected UI or unintended reconnect.
7. **Unit seam added (CI-covered):** `SmartRecoveryPolicy` admits `connect_timeout`, rejects unknown reasons, and preserves connection-intent/cooldown gates. End-to-end scheduler execution and rate-limit behavior still require a later integration/device test.
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


## Validation Android parity (PR #19)

- `tools/validation/align_validation_android.py` aligns the disposable CI Android scaffold with production compileSdk 35, minSdk 24, targetSdk 35, `QUERY_ALL_PACKAGES`, and the production package-visibility query set.
- `tools/validation/test_align_validation_android.py` covers Groovy/Kotlin Gradle configuration, manifest package declarations, and idempotency.
- These tests validate build configuration parity; they do not prove live VPN routing, DNS, or tunnel traffic.
- PR #19 final-head validation and memory-audit runs #45065541255 and #45065541236 both passed.

## Project memory automation

1. After changing `lib/main.dart`, regenerate the navigation index with `python tools/project_memory/index_dart.py --write`.
2. Run `python tools/project_memory/index_dart.py --check --check-status` before opening the PR.
3. The `JET VPN - Project Memory Audit` workflow repeats both checks on relevant PRs and uploads the machine-readable index as a 30-day artifact.
4. A changed source blob or changed byte/line/code-point metrics without matching `CURRENT_STATUS.md` is a stale-memory failure.
5. The index is lexical only: symbol locations and token occurrence counts are not a semantic call graph and do not replace Dart analysis or tests.


## Project-memory tooling regression tests (PR #10 proposal)

- Resolve a call from one Dart file into a declaration in another file and assert the target Element source and repository classification.
- Ensure every tracked `lib/**/*.dart` file is included in the generated source fingerprint list.
- Traverse internal resolved edges from curated workflow anchors; count external and unresolved calls without following them.
- Fail closed when a curated entrypoint is missing or ambiguous.
- Generate the multi-file resolved index and critical-path report twice and compare byte-for-byte in CI.
- Keep native Java patch references visible as cross-language boundaries; do not label them as Dart-analyzed edges.


## Application unit tests — recovery policy branch

- `lib/recovery_policy.dart` isolates deterministic recovery-admission rules from Flutter/plugin state.
- `test/recovery_policy_test.dart` covers documented reason admission (including `connect_timeout`), unknown reasons, smart-mode/user-intent/intentional-stop gates, and cooldown selection.
- The project-memory workflow now runs `flutter test` after root `flutter pub get`. This is a unit-level policy test, not a VPN engine, Android lifecycle, network, or device integration test.

## Application unit tests — live verification branch (PR #12)

- `lib/live_connection_policy.dart` isolates the UI connected-state invariant: native core connected AND live verification succeeded AND no forced-disconnect override.
- `test/live_connection_policy_test.dart` covers native-only connected rejection, verified acceptance, stale verification with disconnected core, and explicit disconnect override.
- PR #12 changes both cold restore and resume to clear verification/ping state and require a fresh silent live check. A failed silent check clears the verified state, leaves the core running, and lets smart mode use the slow health watcher.
- These unit tests do not simulate Flutter lifecycle callbacks, V2Ray plugin behavior, sockets, or actual tunnel traffic. Device/emulator verification is still required.


## Asynchronous live-verification seam — PR #13

- `LiveConnectionVerifier` owns only the settle/ping/retry sequence; Flutter UI state, native core lifecycle, recovery scheduling, and stop decisions remain in `_MainVpnScreenState`.
- Injected wait and ping functions make the asynchronous sequence deterministic in unit tests without starting V2Ray.
- Tests cover silent resume's one-attempt timing, silent ping failure, native-core disconnect during an in-flight check, obsolete-result cancellation, non-silent retry timing, explicit-disconnect cancellation, and compilation of the app entrypoint against the extracted verifier.
- These tests exercise the async verifier used by the app, not the Android lifecycle callback, plugin implementation, sockets, or actual tunnel traffic. Device/emulator tests remain required.
