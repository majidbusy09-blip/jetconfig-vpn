# JET VPN — Known Issues and Risks

> Application findings were inspected against `main` commit `47949178016a6ef3e855a215550b06f4eae8378d`; `lib/main.dart` blob remains unchanged at current main `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`. A source-level finding is not automatically a reproduced runtime bug.

## JET-001 — connect_timeout recovery reason is rejected

- **Severity:** High
- **Status:** Source-level mismatch corrected in PR #11 branch `tests/recovery-regression-20261122`; focused unit tests authored and initial `flutter test` step passed in Run #66. A stricter allowlist assertion has since been added; latest full CI and runtime/device reproduction remain pending.
- **Original evidence:** `_toggleConnect` schedules `_scheduleSmartRecovery('connect_timeout')` after an 8-second unverified connection timeout; the prior scheduler allowlist omitted this reason. On the test branch, `lib/main.dart` delegates admission to `lib/recovery_policy.dart`, whose allowed reasons include `connect_timeout`.
- **Impact:** Smart-mode connection timeout does not enter the intended recovery flow through this path.
- **Verification:** `test/recovery_policy_test.dart` covers all allowed reasons, unknown reasons, connection-intent gates, and cooldown values. The test has not yet been executed in CI at this snapshot.

## JET-002 — Resume restore trusts native CONNECTED status as verified

- **Severity:** High
- **Status:** Confirmed source-level inconsistency; real-world impact needs device reproduction.
- **Evidence:** `_restoreWantConnectedAfterLoad` sets `_connectionVerified = true` when `_statusMeansConnected(v2rayStatus.state)` is true (`lib/main.dart:3843–3868`). It does not call `_verifyLiveConnection` in that branch, while the ordinary verification method exists at line 1606.
- **Impact:** UI/state may report verified connectivity before a live data-path check.
- **Next:** Define one authoritative verification invariant and add lifecycle/resume tests on a device/emulator.

## JET-003 — Pending payment token is not bound to its owner in local storage

- **Severity:** High
- **Status:** Confirmed client storage/context gap; backend exploitability unknown.
- **Evidence:** `_restorePendingPayToken` and `_savePendingPayToken` use one `pending_pay_token` key (`lib/main.dart:3800–3822`). `_watchPaymentStatus` combines it with current `savedUser/savedPass` (`3988–4015`). `_activateProfile` changes active credentials but does not visibly clear/rebind the token (`2566–2604`).
- **Impact:** An invoice created under one profile may be checked using another profile's credentials after switching accounts.
- **Next:** Store token owner and creation metadata; verify server rejects owner mismatch before implementation.

## JET-004 — Account passwords are stored as plaintext preference values

- **Severity:** High
- **Status:** Confirmed source-level storage behavior.
- **Evidence:** Profile JSON stores `username/password/label` (`lib/main.dart:2450–2495`); active password is stored under `saved_password` (`2478–2479`, `2576–2578`, `2605–2609`).
- **Impact:** Credentials are not protected by an app-level encrypted storage layer visible in this source. Device compromise/root/backup exposure may increase risk.
- **Next:** Design a Keystore-backed migration with legacy compatibility and recovery tests. Do not change storage without an explicit implementation task.

## JET-005 — Passwords are transmitted in GET query strings

- **Severity:** High
- **Status:** Confirmed client transport behavior; server logs/configuration not inspected.
- **Evidence:** `_fetchUserData` includes username/password in GET URL (`lib/main.dart:4594–4613`). `_changeAppPassword` includes current and new password in GET URL (`7620–7697`).
- **Impact:** URLs may be recorded by web-server, proxy, or observability logs even over HTTPS.
- **Next:** Coordinate a POST-body API change with backend owner; maintain backward compatibility only during a planned migration.

## JET-006 — Native VPN revoke path lacks explicit user-stop marker

- **Severity:** Medium
- **Status:** Confirmed absence in inspected native method; runtime consequences unknown.
- **Evidence:** `V2rayVPNService.onRevoke()` at approximately line 338 calls `stopCore()`; the explicit `USER_INITIATED_DISCONNECT` handling is in the STOP_SERVICE branch at lines 109–133.
- **Impact:** Flutter may not receive the same intentional-stop signal for Android VPN permission revocation as for notification disconnect.
- **Next:** Trace complete `onRevoke` implementation and Flutter status reconciliation; reproduce permission revoke on supported Android versions.

## JET-007 — Main branch push triggers production release

- **Severity:** Critical operational risk
- **Status:** **Resolved** by merged PR #5.
- **Historical evidence:** Before PR #5, `.github/workflows/build.yml` triggered on push to `main` and published signed APKs/GitHub Releases.
- **Resolution evidence:** Current workflow at main commit `f396f57459c9863a325f27e7d438e9456d560e92` uses only `workflow_dispatch`; requires `confirm_release=true` and `github.ref == 'refs/heads/main'`; `contents: write` is scoped to the release job.
- **Residual risk:** A manually dispatched, explicitly confirmed run can still publish a public Release. Do not dispatch without user approval.

## JET-008 — No repository-owned automated test suite in main snapshot

- **Severity:** High quality/process gap
- **Status:** Confirmed tree observation.
- **Evidence:** Recursive `main` tree at application-source baseline `47949178016a6ef3e855a215550b06f4eae8378d` contains no `test/` directory; application source remains unchanged at current main.
- **Impact:** CI can build/analyze but cannot provide regression coverage for connection, payment, profile, or lifecycle behavior.
- **Next:** Establish test seams and add focused unit tests before high-risk code changes. Do not confuse a CI build with tests.
