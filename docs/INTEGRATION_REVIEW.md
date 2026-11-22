# JET VPN — Integration Review (PR #16)

## Latest verified snapshot — 2026-11-22 (supersedes older status entries below)

- PR #16 reviewed baseline before the final documentation-only alignment: `1d9bb95d71eb2b3426e57a236cea28edec727b14`; branch `integration/memory-and-recovery-20261122`; base `main` at `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- Application source SHA remains `8571a10a8676bf114ca6eda07657da026e550085`; commits after that source snapshot are documentation-only.
- PR #16 is open, Draft, unmerged, and GitHub reports it mergeable. Diff: 38 files, 3,577 additions, 457 deletions.
- Project-memory audit run [#45026323360](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323360) **succeeded** on the earlier reviewed integration head. A later documentation-alignment audit [#45027343286](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45027343286) also **succeeded** on reviewed head `6d4341b9bfd33d0184519c143844b5135ce79096`. Application regression tests, AST indexer tests, resolved-element indexer tests, critical-path tests, deterministic semantic generation, lexical index freshness, and both artifact uploads passed.
- Non-production PR validation run [#45026323476](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323476) **succeeded** on the earlier reviewed integration head. A later validation run [#45027343367](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45027343367) was still running at the time of this note; the code and validation tooling are unchanged, and only documentation alignment followed. Validation-preparation tests, Flutter analysis, app tests, debug smoke build, split ARM64 release-mode build, package/label/signature/ABI checks, and artifact uploads passed.
- Latest ARM64 test artifact: `JET-VPN-TEST-arm64-validation-69`, artifact ID `14756425339`, ZIP size 27,040,234 bytes, expires 2026-11-29. It is an isolated test APK, not production-signed and not for distribution or updating production.
- Latest semantic artifacts: `jet-vpn-code-index` ID `14755568224` and `jet-vpn-semantic-ast-index` ID `14755153930`, both retained until 2026-12-22.
- User-reported device tests passed for all four scenarios: cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device model/build and diagnostic logs were not supplied; do not generalize beyond the tested environment.
- PR review submissions: none. Inline review threads: none.
- Final scoped diff review found no source-level blocker in the inspected VPN verifier/recovery integration, validation workflow, or project-memory workflow. CI does not prove all Android/device/network conditions.
- Production source on `main`, app version `2.4.5+284`, payment, bot, backend, server configuration, and production release workflow remain outside this PR's changes. No merge, release, or deployment has occurred.
- Next action: present the merge recommendation and wait for explicit user approval. Do not merge, mark ready, release, deploy, or dispatch the production workflow without that approval.

> Review snapshot: 2026-11-22  
> PR: https://github.com/majidbusy09-blip/jetconfig-vpn/pull/16  
> Branch: `integration/memory-and-recovery-20261122`  
> Reviewed head before this documentation update: `287448bfae73d6b38e95e4944b6c23afa0ea80f4`  
> Base: `main` at `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`  
> App version: `2.4.5+284`; `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59`.

## Integration scope

PR #16 consolidates the project-memory tooling and VPN recovery/live-verification work from PRs #8–#13 into one review branch. The PR diff contains 32 changed files (2,762 additions / 432 deletions). The changed paths are limited to:

- Project-memory workflow, generated lexical index, semantic tooling and critical-path manifest.
- Project documentation and operating rules.
- `lib/recovery_policy.dart`, `lib/live_connection_policy.dart`, and `lib/live_connection_verifier.dart`.
- The corresponding unit tests and the integration in `lib/main.dart`.

No payment, bot, backend, server, native Java patch, application dependency, app version, or production release workflow change is included in this PR diff. The user's current priority to defer bot/payment work remains in force.

## CI evidence on the integration head

GitHub Actions run [#91 / 45018162238](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45018162238) ran against the exact integration head `287448bfae73d6b38e95e4944b6c23afa0ea80f4` and completed successfully.

The single job, **Verify generated code index and memory freshness**, succeeded. All listed steps completed successfully:

1. Flutter/Dart setup and application package-context resolution.
2. Application regression tests (`flutter test`).
3. AST indexer, analyzer-resolved indexer, and critical-path report tests.
4. AST, analyzer-resolved, and critical-path generation.
5. Deterministic AST regeneration check.
6. Lexical code-index freshness check.
7. Upload of both machine-readable artifacts.

Artifacts (30-day retention, expected expiry 2026-12-22):

- `jet-vpn-code-index`: ID `14753040563`.
- `jet-vpn-semantic-ast-index`: ID `14752731739`.

This is CI evidence for unit tests and project-memory tooling. It is **not** evidence of a successful Android APK build, real V2Ray tunnel traffic, Android lifecycle behavior, or device connectivity.

## Source review notes

### Verified design properties

- `_isVpnConnected` delegates to `LiveConnectionPolicy.isUiConnected`, requiring native core connected, successful live verification, and no forced-disconnect override.
- Cold restore and app resume clear stale verification/ping state before running a silent live check.
- The async verifier checks its generation/currentness after waits and ping completion, checks native core state before reporting success, and keeps retry timing injectable for deterministic tests.
- Silent verification failure clears the UI verification/ping state without stopping the native core; smart mode falls back to the slow health watcher.
- Smart recovery admission/cooldown rules are isolated in a pure policy and include the already-requested `connect_timeout` reason.
- Explicit disconnect and profile-switch paths invalidate the verifier generation through the existing shared user-disconnect/session-reset path.

### Remaining verification boundary

- The unit tests do not instantiate the Android VPN service, exercise the real Flutter lifecycle callback end-to-end, or prove that packets traverse the tunnel.
- The integration CI workflow does not build a release APK. No emulator/device test or real-network test has been performed.
- Static call graphs and critical-path reachability remain analyzer-derived navigation/impact aids, not runtime traces. Dynamic calls, callbacks, state-field dependencies, and native execution are not fully represented.
- Backend and payment semantics remain outside this repository and unverified.

## Review disposition

- PR #16 is open and draft; GitHub reported it mergeable/clean at the reviewed head.
- CI run #91 passed on that exact head.
- No source-level blocker was identified in the focused review of the new policy/verifier integration. This is not a substitute for device validation.
- Keep PR #16 unmerged and draft until Android device testing is completed and the final diff/docs are reviewed.
- Do not merge, release, deploy, or dispatch the production build workflow without the user's explicit approval.

## Next validation

1. Run a debug APK build in a non-production validation workflow (the current integration workflow does not build an APK).
2. Test cold restore and app resume on an Android device with: (a) working tunnel, (b) native core still CONNECTED but tunnel data path blocked, (c) explicit user disconnect during an in-flight ping, and (d) profile switch during verification.
3. Record device model, Android version, exact commit, expected/actual behavior, and redacted logs.
4. Only after these checks, decide whether PR #16 is ready for final review.

## Non-production APK validation update — 2026-11-22

The integration branch now includes a PR-only validation workflow that generates the Android scaffold in the temporary CI workspace (it does not commit an `android/` directory), applies the repository-maintained V2Ray patches to the CI cache, runs analysis/tests, and builds comparison APKs.

- Workflow-only head: `613d465774e8093d4ba38f7959406ca4c3bf2d8f`.
- PR validation [Run #45021183386](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021183386): success. Static analysis, app tests, Debug build, split-per-ABI ARM64 Release build, and artifact uploads all passed.
- Project-memory audit [Run #45021183398](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021183398): success.
- Debug APK artifact: 153,067,021 bytes; retained until 2026-11-29.
- ARM64 Release artifact ID `14753468185`; contained APK `app-arm64-v8a-release.apk` is 27,773,007 bytes (about 26.48 MiB). The artifact ZIP is 27,063,707 bytes and expires 2026-11-29.
- The APK was downloaded and inspected. Its native library entries are exclusively under `lib/arm64-v8a/`; no other ABI directories were present. This validates that `--split-per-abi` corrected the previous fat-APK output.

### Important limitation

The Android project used for this CI build was generated temporarily because the repository does not contain the production Android scaffold. CI reported the generated application ID/namespace as `com.jetconfig.vpn.jetconfig_vpn`. This is not confirmed to be the installed production JET VPN package ID, and the signing certificate has not been matched. Therefore this APK is for build/size analysis only: do not install it over the production app or distribute it.

### Next checks

1. Inspect the authoritative production Android project/build configuration to establish the production application ID and signing identity.
2. Compare the ARM64 APK size against the actual installed production package using consistent units and packaging basis.
3. Only after package/signature compatibility is established, perform controlled Android device tests for restore, resume, disconnect cancellation, profile switching, and real tunnel traffic.

The successful CI build does not establish production installability, signing compatibility, native runtime correctness, or VPN connectivity. PR #16 remains draft and unmerged; no release/deployment was triggered.
