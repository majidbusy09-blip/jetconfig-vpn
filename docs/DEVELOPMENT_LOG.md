# JET VPN — Development Log

Append-only record of meaningful project work. Each entry should include branch/commit, changed files, and exact verification performed.

## 2026-11-22 — Stage 3: agent memory foundation

- **Base:** `main` `47949178016a6ef3e855a215550b06f4eae8378d`.
- **Branch:** `docs/agent-memory-foundation-20261122`.
- **Scope:** Documentation and agent operating rules only.
- **Source reviewed:** `lib/main.dart` (9,002 lines; blob `df2914b2954d723869e4196d96f96b050618985a`), `pubspec.yaml`, production workflow, recursive repository tree, native VPN service patch, and PR #1 documentation patch.
- **Findings:** Corrected source baseline; mapped key functions, actions, storage keys, and connection/recovery state; recorded source-level risks and backend unknowns; documented production-release trigger.
- **Validation:** Re-fetched source files and verified file paths/blob SHAs and current PR states. No app code changed. No build, analyzer, automated test, or device test run for this docs-only task.
- **Review PR:** [#3 — Establish durable JET VPN agent memory and operating rules](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/3), initially opened as draft.
- **PR contents:** 15 Markdown files; no executable source/configuration changes.
- **PR policy at that point in history:** PR had not yet been merged; no Release was performed.

## 2026-11-22 — Stage 5: protect production release workflow

- **PR:** [#5 — Require explicit confirmation before publishing JET VPN releases](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/5).
- **Merged commit:** `f396f57459c9863a325f27e7d438e9456d560e92`.
- **Changed file:** `.github/workflows/build.yml` only.
- **Verified result:** manual `workflow_dispatch` only; required Boolean `confirm_release` defaults false; release job requires ref `main` and confirmation true; `contents: write` is job-scoped; build/sign/release steps preserved.
- **Safety:** No app/Dart/native source changed; no release workflow run, APK publication, or GitHub Release was created by this PR.

## 2026-11-22 — Stage 3 documentation refresh after release-gate merge

- **Base main:** `f396f57459c9863a325f27e7d438e9456d560e92`.
- **Branch:** `docs/agent-memory-foundation-20261122` (PR #3 head).
- **Scope:** Correct stale release-workflow claims; refresh authoritative main snapshot; record the user-approved collaborator-priority test; update release decision, known issue status, file map and next steps.
- **Files intended:** `AGENTS.md`; `docs/ARCHITECTURE.md`; `docs/CURRENT_STATUS.md`; `docs/DECISIONS.md`; `docs/DEVELOPMENT_LOG.md`; `docs/DEVELOPMENT_RULES.md`; `docs/FILE_MAP.md`; `docs/KNOWN_ISSUES.md`; `docs/NEXT_STEPS.md`; `docs/PROJECT_CONTEXT.md`.
- **Source evidence:** current `main` SHA and release workflow/blob re-fetched; current PR states #1–#5 checked.
- **Validation:** Documentation consistency and complete PR diff to be checked after updates. No application source or production workflow is to be modified by this refresh. No Build, analyzer, app test, device test, merge, or Release is part of this task.


## 2026-11-22 — Stage 4: automated code index and memory freshness audit

- **Base after PR #3:** `main` `477ff12fb5a82ba2b2bb3f68a268d27f679c40ab`.
- **Branch:** `tools/project-memory-index-20261122`, rebased onto the merged main snapshot for review.
- **Scope:** Developer tooling, generated navigation index, memory documentation, and read-only GitHub Actions audit.
- **Added:** `tools/project_memory/index_dart.py`, `docs/generated/jet_vpn_code_index.json`, `docs/PROJECT_MEMORY_AUTOMATION.md`, and `.github/workflows/project-memory-audit.yml`.
- **Updated:** `AGENTS.md`, `docs/CURRENT_STATUS.md`, `docs/DEVELOPMENT_LOG.md`, `docs/FILE_MAP.md`, `docs/NEXT_STEPS.md`, and `docs/TEST_PLAN.md`.
- **Index baseline:** `lib/main.dart` blob `df2914b2954d723869e4196d96f96b050618985a`; 9,001 lines; 352,404 UTF-8 bytes; 336,257 Unicode code points; 14 import/export/part directives; 326 lexical symbols.
- **Audit behavior:** Rebuilds and compares the deterministic lexical index, verifies source fingerprint and size metrics, and uploads the JSON index as a 30-day artifact. Workflow permissions are `contents: read`; it cannot commit or publish releases.
- **Prior validation:** Strict run [#44992436433](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/44992436433) passed before rebasing; a fresh run is required.
- **Limitations:** The index is lexical, not a Dart AST or semantic call graph. Token counts do not prove caller/callee relationships or runtime reachability.
- **Safety:** No Dart application source, Native code, app dependencies, Android build configuration, or production release workflow is changed by this stage. No merge or Release is authorized by this PR.


## 2026-11-22 — Stage 6: Dart AST navigation index (PR #8, review pending)

- **Base main:** `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- **Branch:** `tools/dart-ast-memory-20261122`.
- **Scope:** Isolated developer tooling and read-only project-memory CI; no application behavior changes.
- **Added:** `tools/project_memory/semantic/` with analyzer 6.11.0, an AST visitor, a CLI generator, and three focused tests.
- **Workflow:** Added Flutter/Dart setup, dependency resolution, unit tests, deterministic double-generation check, and 30-day semantic-index artifact upload. Existing lexical audit remains enabled.
- **Initial CI debugging:** First compile exposed analyzer 6.11 API differences; corrected the LineInfo import, removed a nonexistent visitor type, and used the public type source representation. Tests then exposed constructor parsing and diagnostic handling; the fixture now uses explicit constructor syntax, class declarations are indexed, and parser diagnostics fail closed.
- **Verified run:** PR #8 [Run #39](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45001992670) succeeded. All three AST indexer tests passed; semantic generation, deterministic regeneration, lexical freshness audit, and both artifact uploads completed successfully. The semantic snapshot records 177 declarations, 3,394 call sites, 3,332 caller edges, 485 unique-name candidates, 7 ambiguous candidates, and 2,902 unresolved names.
- **Safety:** `lib/main.dart`, app `pubspec.yaml`, native patch sources, app version, and production release workflow are unchanged. No merge or Release performed.
- **Limitations:** This is a syntactic AST call-site graph with name-based candidates, not resolved analyzer elements. Detailed JSON is a generated CI artifact; its source fingerprint is tied to the checked-out `lib/main.dart` blob.


## 2026-11-22 — Stage 7: analyzer-resolved Element graph (follow-up PR in progress)

- **Dependency/base:** PR #8 branch `tools/dart-ast-memory-20261122`; this follow-up is intentionally based on its AST tooling and targets that branch rather than `main`.
- **Branch:** `tools/dart-semantic-resolution-20261122`.
- **Scope:** Add a second, package-aware static call-site index using resolved Dart analyzer Elements. Preserve the existing AST name-candidate index for comparison.
- **Added:** `tools/project_memory/semantic/lib/resolved_indexer.dart`, `bin/resolve.dart`, and focused tests for same-name methods, constructor/function calls, and dynamic invocation.
- **Workflow:** Resolve the application package context with `flutter pub get`; run resolver tests; generate both indexes twice and compare outputs; upload the resolved JSON as part of the existing read-only audit artifact.
- **Memory updates:** Documented the new index and its precision boundaries in `PROJECT_MEMORY_AUTOMATION.md`; updated `NEXT_STEPS.md`.
- **Safety:** No app Dart/native source, app dependency manifest, app version, production build/release workflow, or runtime behavior is intended to change. No merge or release is authorized.
- **Verification status:** Pending CI on the final follow-up PR head. Do not describe analyzer resolution as validated until the resolver tests, full source generation, deterministic comparison, and lexical audit all pass.
- **Precision boundary:** Analyzer Elements represent static resolution, not runtime reachability. Dynamic calls remain unresolved; virtual dispatch may differ at runtime. The graph still covers only `lib/main.dart`.


## 2026-11-22 — Stage 7 verification: analyzer-resolved Element graph (PR #9)

- **Final head:** `0999a59289c655c48314120fae9d01870be64022`.
- **CI:** [Run #54](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45003174239) completed successfully.
- **Tests:** All seven tooling tests passed (three AST-indexer tests and four resolved-indexer tests); the resolver test file also passed as its own CI step.
- **Pipeline:** Flutter package-context resolution, isolated lockfile resolution, AST tests, resolved-element tests, both index generations, deterministic regeneration comparison, lexical freshness audit, and both artifact uploads all passed.
- **Resolved source snapshot:** `lib/main.dart` blob `df2914b2954d723869e4196d96f96b050618985a`; 9,001 lines; 352,404 UTF-8 bytes.
- **Analyzer result:** analyzer 6.11.0; resolved unit true; 112 diagnostics, zero errors.
- **Resolved graph:** 468 declarations; 3,394 call sites; 3,353 statically resolved targets; 41 unresolved targets; 3,321 resolved caller-target edges; 2,870 external targets. Own-app `package:jet_vpn/...` elements are correctly classified as repository code; the package-URI classification has a focused regression test.
- **Artifact:** `jet-vpn-semantic-ast-index`, ID `14746174961`, 30-day retention; includes the AST index, resolved-element graph, and isolated tooling lockfile.
- **Diff review:** only `.github/workflows/project-memory-audit.yml`, project-memory documentation, and files under `tools/project_memory/semantic/` changed relative to the PR #8 base. No app source, native source, app dependency manifest, app version, or production release workflow changed.
- **Review state:** PR #9 remains draft/open/unmerged and targets PR #8's branch. No app build, runtime/device test, merge, or Release was performed.


## 2026-11-22 — Stage 8: multi-file Dart resolution and critical-path impact maps (PR #10)

- **Base branch:** `tools/dart-semantic-resolution-20261122`, base SHA `ceea8af5aac276473c3c0422d3e1a3c0d1576a69`.
- **Branch/head:** `tools/dart-critical-paths-20261122`, final SHA `a611d9e995d889aa7d560c92e30c184d497c2fdb`.
- **PR:** [#10 — index Dart source set and critical paths](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/10); open, draft, unmerged; depends on PR #9 and PR #8.
- **Scope:** Isolated project-memory tooling, read-only workflow, curated manifest, and docs. No app/native source, app dependency manifest, app version, or production release workflow changed.
- **Implementation:** Resolver discovers all tracked `lib/**/*.dart` files via `git ls-files`, records per-file blob SHA/metrics/diagnostics, and links cross-file calls by analyzer Element IDs. Critical-path generator traverses internal resolved edges from curated entrypoints and reports external/unresolved calls plus missing/ambiguous anchors. Native Java patch sources are included as explicit references only, not Dart-analyzed edges.
- **Critical-path anchors:** VPN connection/recovery 5/5 resolved; lifecycle 5/5; purchase/payment 4/4; profiles/account 2/2. No missing or ambiguous configured entrypoints.
- **Current source set:** one tracked Dart file under `lib/`; `lib/main.dart` blob `df2914b2954d723869e4196d96f96b050618985a`. A two-file analyzer fixture verifies cross-file resolution and repository classification.
- **Resolved graph:** 468 declarations; 3,394 call sites; 3,353 resolved targets; 41 unresolved targets; 3,321 caller-target edges; 481 internal edges; 2,870 external targets; 112 analyzer diagnostics, zero errors.
- **Workflow:** [CI Run #58](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45004481949) succeeded. Ten distinct tooling tests passed (3 AST, 5 resolved indexer, 2 critical-path). AST, resolved index, and critical-path outputs regenerated twice and compared byte-for-byte; lexical index freshness audit passed.
- **Critical-path summaries:** connection/recovery 51 declarations / 602 calls (149 internal, 437 external, 16 unresolved); lifecycle 29 / 273 (67, 201, 5); purchase/payment 27 / 279 (51, 227, 1); profiles/account 23 / 238 (37, 200, 1).
- **Artifact:** `jet-vpn-semantic-ast-index`, ID `14747635635`, 30-day retention; contains AST, resolved multi-file index, critical-path report, manifest, and tooling lockfile.
- **Verification boundary:** No app build, runtime/device test, merge, or Release was performed. Static transitive reachability is not proof of runtime execution; callbacks, state-field dependencies, dynamic calls, and native runtime behavior remain incomplete.


## 2026-11-22 — PR #9 audit-trigger refresh for dependent PR #10

- **PR #9 head:** `ceea8af5aac276473c3c0422d3e1a3c0d1576a69` on `tools/dart-semantic-resolution-20261122`.
- **Change:** Added the PR #10 target branch to the existing read-only project-memory workflow filter so the dependent PR receives CI from its base branch.
- **Verification:** [CI Run #57](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45003966803) succeeded; AST/resolved tooling tests, generation, deterministic check, and lexical freshness audit passed.
- **Safety:** No app/native source, app dependencies, app version, production release workflow, merge, or Release changed.


## 2026-11-22 — Stage 9: first application regression seam (recovery admission)

- **Base:** PR #10 branch `tools/dart-critical-paths-20261122`, commit `9278785227757f83fb11ac676dd018b4053de545`.
- **Branch:** `tests/recovery-regression-20261122`.
- **Scope:** Extract deterministic smart-recovery admission rules, add unit tests, and execute the app test suite in the read-only CI workflow.
- **Changed application files:** `lib/recovery_policy.dart` added; `lib/main.dart` delegates existing recovery gates, reason admission, and cooldown selection to the pure policy. The policy now includes `connect_timeout`, which the 8-second timeout path already requests.
- **Tests:** `test/recovery_policy_test.dart` covers allowed/unknown reasons, smart-mode and user-intent gates, intentional-stop rejection, and cooldown values. Four test cases are authored; execution is pending CI.
- **CI:** Added root `flutter test` after `flutter pub get`; added the PR #10 base branch to the audit workflow filter so this dependent PR receives checks.
- **Memory:** Regenerated `docs/generated/jet_vpn_code_index.json` from the updated source fingerprint `dc1d0832d55c412d7a475cc596d6b20bd611cf38` (8,997 lines; 352,351 UTF-8 bytes; 336,225 code points).
- **Safety:** No payment/profile/lifecycle code, native Java patch, app dependencies, app version, main branch, or production release workflow changed. No merge, release, build, or device test performed.
- **Commits:** policy `02c24939352be09998a64334ec9946a76d195f25`; tests `7a368cf3e27a44ea2ee80f6cf1e5558befed1b94`; source integration `b7101afa870262ca116ebb9fcf7e6ab4b9df00cc`; CI `aca73de4a499f0edaa5e9a1d3d24931c92ba05eb`; lexical index `ed05584a624b9686a6ed1cf5b05e0541e0121c30`.
- **Verification status:** Not yet run. CI must pass before this change is considered validated.

## 2026-11-22 — Stage 10: live connection verification on restore and resume (PR #12)

- **Base:** PR #11 branch `tests/recovery-regression-20261122`; PR #11 full CI Run [#45008026404](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008026404) succeeded.
- **Branch:** `tests/live-verification-resume-20261122`.
- **Priority capability:** safer implementation and verification; a future collaborator can enforce and test one explicit UI connected-state invariant rather than infer connectivity from native state.
- **Source evidence:** prior `_restoreWantConnectedAfterLoad` marked `_connectionVerified=true` from native `CONNECTED` without ping. Resume silent verification could retain a stale true flag when ping failed.
- **Changes:** added `lib/live_connection_policy.dart`; `_isVpnConnected` now delegates to a pure policy requiring core connected, verified ping, and no forced-disconnect override. Both cold restore and resume clear verification/ping first and run `_verifyLiveConnection(silent: true)`. Silent failure clears verification and active ping, does not stop the core, and returns control to the caller's slow health-watch fallback.
- **Tests:** added four unit cases in `test/live_connection_policy_test.dart` for native-only false, verified true, disconnected-core false, and explicit override false. They test the pure UI gate, not asynchronous lifecycle/native behavior.
- **CI:** added `tests/recovery-regression-20261122` to the PR base-branch filter so this dependent PR can run the read-only memory audit. CI pending at this log snapshot.
- **Memory:** regenerated `docs/generated/jet_vpn_code_index.json` for `lib/main.dart` blob `a2483f2bb90e528a70440978ac62b9f58264c778` (9,016 lines; 352,934 UTF-8 bytes; 336,842 Unicode code points; 16 imports; 326 lexical symbols).
- **Safety:** no payment/profile logic, native Java, app dependencies, app version, main branch, or production release workflow changed. No build, device test, merge, or Release performed.

### Stage 10 verification update — PR #12

- **CI:** Run [#45008634023](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008634023) completed successfully on head `62ebdd4ea65e641cad8fa7ef19ca881b813070fc`.
- **Passed:** application `flutter test`; AST indexer tests; resolved-element indexer tests; critical-path report tests; AST/resolved/critical-path generation; deterministic regeneration comparison; lexical code-index and CURRENT_STATUS freshness verification.
- **Artifacts:** `jet-vpn-code-index` ID `14748897624`; `jet-vpn-semantic-ast-index` ID `14748603470`; both retained until 2026-12-22.
- **Not performed:** Flutter APK build, Android emulator/device test, runtime VPN/network test, merge, or Release.


## 2026-11-22 — Stage 11: injectable asynchronous live verifier (PR #13)

- **Base:** PR #12 head `f600a6e5eae13aced2d58c99fc1ec51484ca3429`; final PR #12 documentation audit Run [#45008853860](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45008853860) succeeded.
- **Branch:** `tests/async-live-verifier-20261122`.
- **Priority capability:** implementation and verification; the async ping sequence used by the app is now independently testable with injected wait and ping dependencies.
- **Changes:** added `lib/live_connection_verifier.dart`; `_verifyLiveConnection` delegates only its settle/ping/retry decision sequence to this class. Flutter state transitions, generation checks, native stop behavior, and smart recovery remain in `lib/main.dart`.
- **Tests:** seven cases cover silent one-shot verification, silent failure, core disconnect during an in-flight ping, obsolete-result cancellation, two-attempt retry timing, explicit-disconnect cancellation, and app-entrypoint compilation against the extracted verifier.
- **Scope:** no payment/profile code, native Java, app dependencies, app version, or production release workflow changed. No device/emulator test, merge, or Release performed.
- **Source:** `lib/main.dart` blob `2d833223153c61a0209123553b99f9d982bf4574`; 9,006 lines, 352,724 UTF-8 bytes, 336,664 Unicode code points.
- **CI:** [Run #45011976765](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45011976765) succeeded on final head `e11598dfb3978e44e01aa52a3e3afa95f87307b1`.
- **Passed:** all 15 application tests (including all seven verifier tests); 10 AST-indexer tests; 5 resolved-indexer tests; 2 critical-path tests; semantic index generation; deterministic regeneration; lexical index and CURRENT_STATUS freshness checks; both artifact uploads.
- **Artifacts:** `jet-vpn-code-index` ID `14750137931`; `jet-vpn-semantic-ast-index` ID `14750411193`; both expire 2026-12-22.
- **Not performed:** Flutter APK build, Android emulator/device test, runtime VPN/network test, merge, or Release.


## 2026-11-22 — Stage 12: integration review and CI verification (PR #16)

- **PR:** [#16 — consolidate project memory and VPN recovery work](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/16).
- **Branch:** `integration/memory-and-recovery-20261122`.
- **Reviewed source head:** `287448bfae73d6b38e95e4944b6c23afa0ea80f4`; app version `2.4.5+284`; `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`.
- **Diff:** 32 files, 2,762 additions, 432 deletions. Scope is project-memory tooling/docs plus recovery/live-verification policy, verifier, app integration, and tests. No payment, bot, backend, server, native Java, app dependency, app version, or production release workflow changes.
- **CI:** Run [#45018162238](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45018162238) succeeded on the exact reviewed head. Application `flutter test`, semantic tooling tests/generation, deterministic AST regeneration, lexical freshness, and both artifact uploads all passed.
- **Artifacts:** `jet-vpn-code-index` ID `14753040563`; `jet-vpn-semantic-ast-index` ID `14752731739`; 30-day retention.
- **Source review:** Confirmed the UI connection gate requires core-connected + verified ping + no forced-disconnect override; restore/resume clear stale verification and run the async verifier; stale verifier generations are cancelled; silent failure leaves the native core running and delegates to slow health watch; recovery policy includes `connect_timeout`.
- **Limitations:** CI is not an APK build or Android device test. No real tunnel traffic, Android lifecycle integration, or native V2Ray behavior was verified. No source-level blocker was identified in the focused review; device validation remains mandatory.
- **Safety:** PR remains draft/unmerged. No merge, production release, deployment, or production workflow dispatch occurred.
- **Detailed record:** `docs/INTEGRATION_REVIEW.md`.


## 2026-11-22 — Stage 8: integration CI, ARM64 packaging verification, and memory synchronization

- **Branch:** `integration/memory-and-recovery-20261122`.
- **Verified head:** `895124409f2c6a302e2ede3c73ccd3af54c747a0`; base main `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- **Scope:** CI-only ARM64 packaging correction and project-memory synchronization. No production app source, app version, payment, bot, backend, server, or production release workflow was changed in this stage.
- **CI:** PR validation [Run #45021900956](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900956) passed Flutter analysis, application tests, Debug smoke build, ARM64 split Release-mode comparison build, and artifact uploads. Project-memory audit [Run #45021900965](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900965) passed application tests, AST/resolved-index tests, deterministic generation, critical-path generation, lexical freshness, and artifact uploads.
- **Artifacts:** Debug `JET-VPN-debug-25`, ID `14754525304`, 153,067,024 bytes; ARM64 `JET-VPN-arm64-release-mode-25`, ID `14754511282`, ZIP 27,063,719 bytes. Both expire 2026-11-29. The contained ARM64 APK is 27,773,007 bytes (26.48 MiB); archive inspection confirmed only `lib/arm64-v8a/` native libraries.
- **Identity evidence:** production `.github/workflows/build.yml` and non-production scaffold both use `flutter create . --platforms=android --project-name=jetconfig_vpn --org com.jetconfig.vpn`, yielding `com.jetconfig.vpn.jetconfig_vpn`. The comparison APK certificate is `CN=Android Debug`; the production release workflow uses the configured release keystore. Certificate fingerprints were not compared.
- **Memory changes:** corrected the current-status header, made next steps reflect completed APK work and the actual safe next action, appended this log entry, and added `docs/TASK_TEMPLATE.md`; `AGENTS.md` now requires use of the template for non-trivial tasks.
- **Limitations:** no production APK signature comparison, install test, Android device test, native V2Ray runtime test, or real tunnel-traffic validation was performed. PR #16 remains draft/unmerged. No release or deployment occurred.


## 2026-11-22 — Documentation protocol finalized

- **Docs-only head:** `c8c40f3e174248a5c01b5b4449e874abd983e464` (application source unchanged from the previously validated integration source).
- Added `docs/TASK_TEMPLATE.md` and linked it from the mandatory context-loading sequence in `AGENTS.md`.
- Corrected `docs/CURRENT_STATUS.md` to identify the current integration head and exact CI/artifact evidence; rewrote `docs/NEXT_STEPS.md` so the next action reflects verified state rather than already-completed APK work.
- This commit changes documentation only. A fresh project-memory audit must pass on the final docs head before this documentation refresh is marked fully validated.


## 2026-11-22 — Stage 13: isolated validation APK and physical-device handoff

- **Branch/source head:** `integration/memory-and-recovery-20261122`, validated source head `8571a10a8676bf114ca6eda07657da026e550085`; PR #16 remains draft/unmerged.
- **CI:** PR validation [Run #45023210674](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210674) succeeded through validation-tool unit tests, Flutter analysis, app tests, debug smoke build, ARM64 split Release-mode APK build, package/label/signature/ABI verification, and upload. Project-memory audit [Run #45023210902](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210902) succeeded.
- **Changes:** added `tools/validation/prepare_validation_build.py` and its unit tests; updated `.github/workflows/pr-validation.yml` to prepare a separate validation package in the ephemeral CI workspace, disable the updater in that build, and verify the resulting APK. Production `lib/main.dart` and production `.github/workflows/build.yml` are untouched by the validation preparation step.
- **Verified artifact:** `JET-VPN-TEST-arm64-validation-42`, ID `14754751347`, expires 2026-11-29 12:43:53 UTC. APK is 27,748,544 bytes (~26.46 MiB), package `com.jetconfig.vpn.jetconfig_vpn.validation`, label `JET VPN TEST`, versionName `2.4.5`, versionCode `2284`, ABI set exactly `arm64-v8a`.
- **Signature:** CI `apksigner` verified v1 and v2 signatures; one signer `CN=Android Debug`; certificate SHA-256 `524cfda67adac575c959bdeaf99484cd5f0f1a260a87a275cd84f2f6d833fdf9`. This is not the production signing key.
- **Local inspection:** downloaded the workflow artifact, extracted its sole APK, confirmed archive structure and ARM64-only native library directory. No production app installation was attempted.
- **Memory:** appended exact artifact and verification evidence to `docs/CURRENT_STATUS.md`; replaced `docs/NEXT_STEPS.md` with the device-validation-first sequence; added `docs/DEVICE_VALIDATION.md`; mapped validation tooling and checklist in `docs/FILE_MAP.md`.
- **Next:** user installs the isolated test app alongside production and runs the four documented recovery scenarios. Payment, bot, backend, production updater, merge, and release remain out of scope.
- **Limitations:** physical-device installation, Android lifecycle behavior, native V2Ray tunnel behavior, and real tunnel traffic are not yet validated. A passing CI build does not establish those properties. A fresh project-memory audit is required on the documentation-updated head.


## 2026-11-22 — Stage 14: user-reported physical-device recovery validation passed

- **PR/head:** #16, `integration/memory-and-recovery-20261122`, head `eefde6baa1556e56c11ce4c872ca4cdd9cee3722`; open, draft, unmerged, mergeable at inspection.
- **Device test:** user reports all four scenarios in `docs/DEVICE_VALIDATION.md` passed: cold start/restore, background resume, explicit disconnect during verification, and profile switch during verification.
- **Evidence qualification:** this is a user-reported manual result. No logs or recording were provided; device model, Android version/build, network type, and profile are unknown. Do not infer device details or claim universal coverage.
- **CI:** current-head PR validation [Run #45024183497](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45024183497) passed Flutter analysis, application tests, debug smoke build, isolated ARM64 validation APK build, package/label/signer/ABI verification, and artifact upload. Project-memory audit [Run #45024183512](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45024183512) passed app tests, semantic indexer tests, deterministic generation, critical-path generation, and lexical freshness.
- **PR review state:** no submitted PR reviews or inline review threads were returned by the GitHub review-list endpoints at inspection. PR is still draft and unmerged.
- **Next:** finish final diff/source review and validate documentation/indexes on the latest head; then present merge recommendation for explicit user approval. No merge/release/deploy was performed.


## Follow-up — documentation head correction and test evidence qualification

- The Stage 14 record above was written at commit `eefde6baa1556e56c11ce4c872ca4cdd9cee3722`. Subsequent branch commits are documentation-only; the application/validation source remains `8571a10a8676bf114ca6eda07657da026e550085`.
- CI runs #45024183497 (PR validation) and #45024183512 (project-memory audit) both passed at `eefde6baa1556e56c11ce4c872ca4cdd9cee3722`. A separate successful run on the newest documentation-only head has not yet been confirmed in this log.
- The PR contains 38 changed files at the latest review snapshot. Final source/diff review and a current-head CI confirmation remain the gates before presenting a merge recommendation.


## Follow-up — final project-memory audit on user-test documentation

- Project-memory audit [Run #45026094298](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026094298) completed successfully on commit `a6690d0d9efe310624946d47207ffd19016a6f25`. Application tests, semantic indexer tests, deterministic AST/resolved/critical-path generation, lexical freshness, and both index artifact uploads passed.
- Non-production PR validation [Run #45026094310](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026094310) was created for the same docs-only snapshot but remained queued at the time of this note. The exact application/validation source had already passed complete analysis/tests/ARM64 APK validation in Run #45024183497; no app code changed in the later documentation commits.
- Final review spot-check confirmed `_applyUserDisconnect` increments `_verifyGen`, `_activateProfile` increments `_verifyGen`, and the verifier checks generation/currentness after async waits and ping completion. This matches the two race-condition device scenarios reported as passing by the user.


## 2026-11-22 — Authoritative memory refresh after PR #16/#17 and main protection

- **Base main:** `eae477a89816a5cfd475c596e166d5cb2575884a`.
- **Branch:** `docs/refresh-authoritative-memory-20261122`.
- **Scope:** Documentation-only correction of operational snapshots and repository map.
- **Verified GitHub state:** PR #16 merged at `c4f7f4743b3c6ffc64d34a0efb0c19f41b236f1e`; PR #17 merged at `eae477a89816a5cfd475c596e166d5cb2575884a`; main branch points to `eae477a89816a5cfd475c596e166d5cb2575884a`.
- **Source identity:** `lib/main.dart` blob `3d28693b7be8bfe309a850923599830e1a65ab59`; `pubspec.yaml` blob `adc3b22a4538db4738bec789e3c3badf26e4f710`; app version `2.4.5+284`.
- **CI evidence:** post-merge audit [#45029689706](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45029689706) completed successfully on main after PR #17.
- **Ruleset:** `main-protection` verified active; default branch only; PR required; required status context `Verify generated code index and memory freshness`; deletion and force-push blocked; Squash-only; no bypass actors.
- **Problem found:** top-level snapshots still described PR #16 as open and used the pre-merge main SHA. This could mislead future agent decisions.
- **Files refreshed:** `AGENTS.md`, `docs/CURRENT_STATUS.md`, `docs/NEXT_STEPS.md`, `docs/PROJECT_CONTEXT.md`, `docs/FILE_MAP.md`, `docs/TEST_PLAN.md`, `docs/PROJECT_MEMORY_AUTOMATION.md`; this append-only log records the correction.
- **Verification scope:** GitHub API metadata, tree, source blob IDs, version, PR states, ruleset and workflow run were re-fetched. Documentation-only changes; no Flutter source, bot, payment, backend, server, release workflow, version, signing or deployment changes.
- **Checks:** project-memory audit will run on this PR; no local Flutter/Dart execution was performed through the GitHub connector.
- **Approval boundary:** PR remains unmerged; no release or deployment.


## 2026-11-23 — PR #19 merged; validation Android parity and required-check reliability

- **Main commit:** `abdff3a59b89419e869c98d7dbb4ac91512fe950` (PR #19 squash merge).
- **PR:** #19, `fix/validation-android-parity-20261122`; final head `3d47359c1ebaf6dcd6adfb19e886b9f148bbf030`.
- **Scope:** Added `tools/validation/align_validation_android.py` and `tools/validation/test_align_validation_android.py`; updated `.github/workflows/pr-validation.yml` to align the temporary validation Android scaffold with production SDK/package-visibility configuration. Updated `.github/workflows/project-memory-audit.yml` so the required memory-audit check runs on every PR targeting main, avoiding path-filter-induced pending required checks.
- **CI:** Project Memory Audit [#45065541236](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541236) and Non-production PR Validation [#45065541255](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541255) both completed successfully on the final PR head before merge.
- **Application boundary:** No `lib/` files, native tunnel Java/Kotlin, DNS/routing implementation, app version, signing, production release workflow, bot, payment, backend, or server configuration changed. No release or deployment occurred.
- **Device evidence:** User reported the Build 104 validation APK appeared to work in testing. This remains user-reported evidence; no broad Android/device/network compatibility claim is inferred.
- **Memory maintenance:** This PR #18 refresh updates operational snapshots to main commit `abdff3a59b89419e869c98d7dbb4ac91512fe950` and records PR #19. Historical entries remain preserved; no older event is rewritten.


## 2026-11-23 — PR #18 merged; task-orchestrator design started

- **Main before merge:** `abdff3a59b89419e869c98d7dbb4ac91512fe950`.
- **PR:** #18, `docs/refresh-authoritative-memory-20261122`; merged by Squash at `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- **Post-merge verification:** Project Memory Audit [#45069210457](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45069210457) completed successfully on the merge commit. Application regression tests, AST/resolved-index tests, critical-path tests and generation, deterministic comparisons, lexical index freshness, and artifact uploads passed.
- **Next-stage finding:** current `AGENTS.md`, `docs/CURRENT_STATUS.md`, and `docs/NEXT_STEPS.md` still referenced the pre-PR-18 main SHA or described PR #18 as pending. This branch corrects that snapshot and records the current task-orchestrator design.
- **Design:** `docs/TASK_ORCHESTRATOR_DESIGN.md` specifies a Python 3.12 standard-library-only local MVP, explicit lifecycle/state record, fail-closed scope and branch gates, reuse of existing semantic tooling, fixed verification profiles, and no GitHub write/merge/release/deploy capabilities.
- **Branch:** `design/task-execution-orchestrator-20261123`, based on current main `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- **Scope:** documentation/design only. No Dart/Java/Kotlin application code, dependency, app version, signing, production release workflow, bot, payment, backend, or server behavior changed.
- **Checks:** post-merge Project Memory Audit passed; this design branch's CI is pending/not yet run at the time of this entry. No implementation tests are claimed.
- **Approval boundary:** branch only; no merge, release, or deployment.


## 2026-11-23 — PR #20: local task orchestrator MVP (implementation in review)

- **Base main:** `a09cdb0be35e3072be29973f7ae8df66ab44d07f`.
- **Branch:** `design/task-execution-orchestrator-20261123`.
- **Design-only checkpoint:** head `f7d9fa028d99e62e5d7c1ef453578440055e5cc9`; Project Memory Audit [#45070004438](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45070004438) and Non-production PR Validation [#45070004449](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45070004449) both succeeded. This checkpoint predates the implementation commits and does not validate them.
- **Added:** `tools/task_orchestrator/task_orchestrator.py` (standard-library CLI), `tools/task_orchestrator/tests/test_task_orchestrator.py` (temporary-Git-repository integration tests), and `tools/task_orchestrator/README.md`.
- **Implemented lifecycle:** `init → prepare → impact → begin → validate-scope → verify → finalize`; task JSON and handoff live under `.agent/tasks/<task-id>/`.
- **Safety gates:** clean worktree at init; protected-branch and dirty-worktree rejection; mandatory context fingerprints; pinned base SHA; explicit allow/exclude patterns; full tracked/untracked/rename/delete path validation; content fingerprints bind approval to exact validated contents; fixed named verification profiles, subprocess `shell=False`, bounded timeouts, append-only check attempts, and explicit reviewed-diff confirmation.
- **Impact limitation:** current MVP records presence/hash of existing semantic and critical-path artifacts and labels them `present_unverified`; it does not claim fresh or complete path-specific semantic analysis.
- **CI:** extended only the non-production PR validation workflow to run the orchestrator test suite under Python 3.12. No new required branch-protection check was added.
- **Explicit non-goals:** no GitHub write API, commit/push, PR creation, merge, tag, release, deploy, or production workflow dispatch capability.
- **Scope:** developer tooling, its tests/docs, and non-production CI only. No Dart/Java/Kotlin app source, app version, signing, production release workflow, bot, payment, backend, or server behavior changed.
- **Verification of implementation commits:** pending CI on the latest branch head; no implementation test result is claimed yet.
- **Approval:** PR #20 remains Draft; no merge/release/deploy.


## 2026-11-23 — PR #20 verification stability hardening

- **Finding:** the orchestrator compared the post-check source fingerprint with the finalization fingerprint, but did not prove that the worktree remained stable during the check itself. A file could change while a test process was running, making the resulting pass ambiguous.
- **Change:** `verify` now snapshots the complete changed-path set and fingerprints immediately before and after each fixed verification profile. If either differs, the attempt is recorded as failed (exit code 125 when the check itself returned success) and cannot satisfy finalization. Both snapshots and the stability flag are retained in the task record.
- **Regression test:** added an integration test that deliberately mutates a source file during the check and asserts that the attempt is rejected.
- **Documentation:** updated the orchestrator README and design invariants to describe stable-source verification.
- **CI:** previous runs [#45100960414](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45100960414) and [#45100960755](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45100960755) passed before this hardening. New runs [#45101712631](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45101712631) and [#45101712642](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45101712642) are validating the updated code and are still in progress at this entry.
- **Boundary:** PR #20 remains Draft and unmerged. No production app, bot, payment, backend, server, release, or deployment behavior was changed.


## 2026-11-23 — PR #20 orchestrator hardening verified; coding-agent adapter contract drafted

- **Branch:** `design/task-execution-orchestrator-20261123`.
- **Verified implementation head:** `c4acaf8c32a5c70cea2919b9eb5f2c68303b3559`.
- **CI:** Project Memory Audit [#45105873991](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45105873991) and Non-production PR Validation [#45105874008](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45105874008) both completed successfully. The PR validation job passed the Orchestrator integration suite, validation tooling tests, Flutter analysis, application tests, debug APK smoke build, and ARM64 validation APK build. This is CI/build evidence, not a physical-device VPN runtime test.
- **Regression correction:** fixed the latest-attempt ordering test to write a valid JSON newline rather than a literal backslash-n sequence. Both workflows passed on the corrected implementation head.
- **Added:** `docs/CODING_AGENT_ADAPTER_CONTRACT.md`, a provider-neutral contract for task envelopes, structured agent results, sandbox permissions, patch acceptance/rejection gates, failure/retry semantics, audit/privacy, and phased rollout.
- **Updated:** `docs/NEXT_STEPS.md` to mark the local MVP's CI verification complete and prioritize schema/fixture tests followed by a read-only provider adapter.
- **Design boundary:** no provider is connected; no agent patch execution, GitHub write permission, commit/push, PR creation, merge, release, deployment, or production workflow dispatch is implemented or authorized.
- **Application boundary:** no Dart/Java/Kotlin app source, app version, signing, production release workflow, bot, payment, backend, or server behavior changed.
- **PR state:** PR #20 remains Draft and unmerged. New documentation changes require fresh CI on the updated branch head.


## 2026-11-23 — PR #20 coding-agent contract schema validator and security fixtures

- **Branch:** `design/task-execution-orchestrator-20261123`; PR #20 remains Draft/open/unmerged.
- **Added:** `tools/task_orchestrator/agent_contract.py`, a Python-standard-library validator for immutable task envelopes and structured agent results (contract version 1.0). It enforces exact object fields, enums/types, repository and branch identity, normalized repository-relative paths, protected-path rejection, declared allow/exclude scope, context SHA-256 fingerprints, fixed verification-profile allowlist, bounded budgets/usage, opaque SHA-256 artifact references, and consistent non-completed/failure semantics. JSON parsing rejects duplicate keys, malformed input, non-object roots, and oversized payloads.
- **Added:** `tools/task_orchestrator/tests/test_agent_contract.py` with fixtures and adversarial cases for malformed/missing/extra fields, wrong types, traversal/absolute/Windows paths, protected/excluded/out-of-scope paths, invalid glob scopes, budget overflow, arbitrary profile/command/URL injection, patch reference errors, task mismatch, stale fingerprints, and blocked/clarification states.
- **Updated:** Orchestrator README, verified file map, and next-step roadmap.
- **Security boundary:** validator handles data only. No provider connection, command execution, patch retrieval/application, filesystem write access for an agent, or GitHub API permission was added. Patch artifact content must be parsed and independently gated in a later phase.
- **Verification:** both pre-change CI workflows passed on the previous head (Project Memory Audit #45106590264; Non-production PR Validation #45106590252). New commits require fresh CI; do not claim these tests passed until the new head's workflows complete.
- **Application boundary:** no Dart/Java/Kotlin app source, app version, signing, production workflow, bot, payment, backend, or server behavior changed.


## 2026-11-23 — Read-only coding-agent adapter prototype

- **Added:** `tools/task_orchestrator/readonly_adapter.py` with a minimal provider protocol and a fail-closed `run_readonly` boundary. It validates the task envelope before invoking a provider, exposes a recursively immutable context object, and validates the provider's structured result against the same task envelope.
- **Added:** `tools/task_orchestrator/tests/test_readonly_adapter.py` covering valid fixture output, nested immutability, invalid input rejected before provider invocation, malformed output, provider exceptions, required interface, and caller-data integrity.
- **No live integration:** the only included provider is a deterministic fixture. No SDK, API key, network client, shell, Git, filesystem handle, patch fetch/apply, or GitHub write capability was added.
- **Security limitation:** this interface is not an OS sandbox and cannot constrain arbitrary behavior inside a provider implementation. Any real connector must be separately reviewed and run with explicit permission restrictions.
- **CI baseline:** validator head `4dd6f8110bd9462fde73c7c9ab256a72c971c55e` passed Project Memory Audit [#45107836885](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45107836885) and Non-production PR Validation [#45107836882](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45107836882). Adapter commits are newer and require fresh CI.
- **Application boundary:** no Dart/Java/Kotlin app source, app version, signing, production workflow, bot, payment, backend, or server behavior changed.


## 2026-11-24 — PR #20 and patch-review pipeline verified; authoritative memory refresh

- **Verified base:** `main` `f682c56331bfb7c07bc4c5be26fddc33a3043969`; application source blob remains `3d28693b7be8bfe309a850923599830e1a65ab59`; app version remains `2.4.5+284`.
- **PR #20:** verified merged at `15fea59e4f83704e0a9955363e0f0b237aac09ac`. The local orchestrator, agent contract, context/impact tooling, and fixture-only read-only adapter are now part of main.
- **PRs #38–#44:** independently re-fetched and confirmed merged. They add content-addressed patch storage, fail-closed live review authorization, read-only live review, provider-result ingestion, and integration coverage through the human-review boundary.
- **PR #44:** merge commit `f682c56331bfb7c07bc4c5be26fddc33a3043969`; head `af5fc704f61fd8a656966b35ddbe9450630d8c1f`. Task Orchestrator Tests #45307323849, Non-production PR Validation #45307323773, and Project Memory Audit #45307323780 all completed successfully.
- **Memory defect found:** `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/CURRENT_STATUS.md`, `docs/NEXT_STEPS.md`, `docs/PROJECT_MEMORY_AUTOMATION.md`, and architecture decisions still described the pre-PR-20 snapshot and/or PR #20 as unmerged. This refresh corrects the authoritative current state while preserving archive/history.
- **Sandbox decision corrected:** E2B prior-written-consent and EU payment-method requirements, and Daytona's Tier 3 $500 top-up requirement for strict sandbox-level egress, mean neither candidate is eligible under current constraints. No account, key, sandbox, source upload, or spend was created.
- **Refresh branch:** `docs/refresh-collaborator-memory-20261124`. Documentation-only; no Dart/Java/Kotlin app source, version, signing, release workflow, bot, payment, backend, or server behavior changed.
- **Verification scope:** GitHub branch/ref, file/blob, PR, workflow-run, and ruleset APIs were checked. This documentation refresh itself requires its own Project Memory Audit on the PR head; no Flutter build, application test, or device test is claimed for this docs-only change.


## 2026-11-24 — PR #46 memory refresh merged; synthetic sandbox contract started

- **PR #46:** merged at `4dbe01eda4078342c17f16a4111919bebaa616ae`. It refreshed 11 project/architecture documents after PR #20 and PRs #38–#44, corrected stale PR states, and superseded the outdated E2B-first pilot recommendation.
- **PR #46 checks:** Project Memory Audit #45313415951, Task Orchestrator Tests #45313415720, and `validate-agent-pr` #45313412813 passed. Non-production validation attempt 1 hit Maven Central HTTP 429 during debug APK dependency resolution; retry attempt 2 (#45313415713) completed successfully. The PR changed documentation only and did not change application source.
- **New branch:** `feat/sandbox-lifecycle-contract-20261124-v2`, based on main `4dbe01eda4078342c17f16a4111919bebaa616ae`.
- **Added:** `tools/task_orchestrator/sandbox_contract.py` with a provider-neutral synthetic-only protocol, strict resource/request validation, Linux VM capability gate, provider-reported runtime checks, lifecycle state machine, bounded artifact SHA-256 validation, interruption cleanup, and mandatory destruction confirmation.
- **Added:** `tools/task_orchestrator/tests/test_sandbox_contract.py` with fake-provider tests for success, capability rejection, open egress, guest credentials/host sockets, timeout, artifact tampering/size, destroy failure, sanitized provider errors, interruption cleanup, and invalid transitions.
- **Updated:** `tools/task_orchestrator/README.md` with synthetic-only boundaries and focused test command.
- **Security boundary:** no real provider, process execution, source upload, model-generated code, credentials, network call, account, payment, sandbox, or spend is involved. Every success record states `eligible_for_untrusted_execution: false` and `patch_applied: false`.
- **Verification:** GitHub file/ref operations only; the new sandbox tests have not yet run in CI. PR creation and CI are the next step. No local or device test is claimed.


## 2026-11-24 — PR #47 merged: synthetic-only sandbox lifecycle contract

- **PR:** #47 merged at `f360d50b13064c7136eb7ce4a3b38e3413e5b333`; base was `4dbe01eda4078342c17f16a4111919bebaa616ae`.
- **Added:** `tools/task_orchestrator/sandbox_contract.py` and `tools/task_orchestrator/tests/test_sandbox_contract.py`.
- **Updated:** `tools/task_orchestrator/README.md`, `AGENTS.md`, and project/architecture memory documents.
- **Behavior:** strict Linux-VM capability gate, pinned image/policy digests, deny-all network request, explicit CPU/RAM/PID/disk/wall-time limits, provider-reported runtime snapshot checks, fail-closed lifecycle, bounded SHA-256 artifact validation, and mandatory termination/destruction confirmation.
- **Test evidence:** Task Orchestrator Tests #45314331567 passed 247 Python tests, including all 13 new sandbox tests. Project Memory Audit #45314331612 passed; `validate-agent-pr` passed. Non-production PR Validation #45314331545 was still running at this log snapshot.
- **Security boundary:** fixed synthetic payload only; no arbitrary shell, source upload, credentials, model-generated code, real provider, real sandbox, or external spend. The result always records `eligible_for_untrusted_execution: false` and `patch_applied: false`.
- **Next:** independently test a real candidate runtime only after a separate account/consent/cost decision. Do not treat provider-reported snapshots or fake-provider tests as isolation proof.


## 2026-11-24 — Independent signed sandbox acceptance evidence verifier

- **Base:** `main` `53e00ac2ad5e260a4d214772da4ba9bccd3499f4` (PR #48 merged).
- **Branch:** `feat/trusted-sandbox-evidence-gate-20261124`.
- **Goal:** Make the sandbox trust boundary depend on independently signed evidence rather than provider-declared capabilities or snapshots.
- **Added:** `tools/task_orchestrator/sandbox_acceptance.py`, `tools/task_orchestrator/tests/test_sandbox_acceptance.py`, and `docs/SANDBOX_RUNTIME_ACCEPTANCE.md`.
- **Verifier:** strict canonical UTF-8 JSON; duplicate-key and non-finite-number rejection; exact schema/suite/version; pinned provider, region, task, attempt, image, policy and key ID; fresh UTC timestamps; exact 20-probe inventory; per-probe SHA-256 evidence digests; bounded report/signature; injected signature-verifier interface.
- **Adversarial tests:** missing/duplicate/failed/unknown probes, identity mismatch, stale/future/overlong report, bad key/signature, duplicate JSON keys, noncanonical encoding, oversized report/signature, verifier exception, and invalid trusted clock.
- **Critical limitation:** The implementation verifies a report; it does not run the guest probes, provide an Ed25519 implementation, create a signing service, provision a VM, or authorize execution. Production requires an out-of-band pinned public key and an audited asymmetric verifier. Test verifier is a fake only.
- **Safety:** Every passing result remains `execution_authorized: false`, `eligible_for_untrusted_execution: false`, and `patch_applied: false`. No account, provider, network probe, key, source transfer, sandbox, or spend is involved.
- **Verification:** To be run by the Task Orchestrator CI workflow after PR creation; no local/device/runtime test is claimed.
- **Next:** Build the fixed external probe runner and independently controlled signing trust root, then test an approved real candidate VM.


## 2026-11-24 — PR #49 merged: independent signed sandbox evidence verifier

- **Base:** `main` `53e00ac2ad5e260a4d214772da4ba9bccd3499f4`.
- **PR:** [#49 — Verify independently signed sandbox acceptance evidence](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/49).
- **Merge commit:** `4fc59de5a8d6ef9323de3b48896f78f3c426732d`.
- **Added:** `tools/task_orchestrator/sandbox_acceptance.py`, `tools/task_orchestrator/tests/test_sandbox_acceptance.py`, and `docs/SANDBOX_RUNTIME_ACCEPTANCE.md`.
- **Verification:** Task Orchestrator Tests #45320041554 passed 259 tests total (12 new evidence-verifier tests); Project Memory Audit #45320041561 passed; Agent PR Lease and Scope Guard #45320038880 passed.
- **Non-production validation:** #45320041553 remained pending at merge; no application source, app version, release, signing, or production behavior was changed.
- **Security boundary:** The verifier checks a canonical signed report and all 20 probe records. It does not run probes, provision VMs, implement the production signature verifier, or authorize execution. All success results remain `execution_authorized: false`, `eligible_for_untrusted_execution: false`, and `patch_applied: false`.
- **Next:** Build the actual fixed probe suite and independently controlled signing trust root. No account, payment, source transfer, provider sandbox, or spend without separate approval.


## 2026-11-24 — Stage 20: bind signed sandbox acceptance to raw evidence (PR #51)

- **Base:** `main` after PR #50; **branch:** `feat/bind-raw-sandbox-probe-evidence-20261124`.
- **PR:** [#51 — bind signed sandbox probe reports to raw evidence](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/51).
- **Merged commit:** `1438d0a047523a22fee26e72ae12cf34cebbb95e`.
- **Scope:** Hardened `tools/task_orchestrator/sandbox_acceptance.py`, adversarial tests, and `docs/SANDBOX_RUNTIME_ACCEPTANCE.md`.
- **Security change:** Require the exact 20-entry raw evidence bundle; recompute each SHA-256 from raw bytes; reject missing, extra, empty, altered, per-probe oversized (>128 KiB), and aggregate oversized (>2 MiB) evidence. Execution authorization remains false.
- **Verification:** PR head `42c208398ef0b044ba54c17ca183957022eb0288`; Task Orchestrator Tests #45325193322, Project Memory Audit #45325193253, Agent PR Lease and Scope Guard #45325195790, and Non-production PR Validation #45325193266 all completed successfully.
- **Safety:** No VM provisioned, no guest/untrusted code executed, no provider/account/API key/payment/private-source transfer/signing key/spend, and no app source/version/release/backend/payment/server changes.

## 2026-11-24 — Stage 21: project memory refresh after PR #51

- **Base:** PR #51 merged main `1438d0a047523a22fee26e72ae12cf34cebbb95e`.
- **Branch:** `docs/refresh-raw-evidence-verification-20261124`.
- **Scope:** Synchronize current status, next steps, project context, file map, and agent instructions with PR #51; preserve the distinction between the limited Bubblewrap self-check, host preflight inventory, and the still-missing independent 20-probe runtime suite.
- **Safety:** Documentation only. No production code, application source, provider connection, external execution, credentials, or spend.
- **Verification:** Pending PR CI and memory audit; do not claim this documentation refresh merged until its PR and required checks are observed.


## 2026-11-24 — Stage 22: pinned sandbox trust-store policy adapter

- **Base:** `main` at `440569f769fd0d6871ac370d7923417637f90dc8` (PR #52 merged).
- **Branch:** `feat/pinned-sandbox-trust-store-20261124`.
- **Goal / priority:** Yes — improve safe verification and durable project memory by binding report signature verification to an independently pinned, versioned trust policy.
- **Added:** `tools/task_orchestrator/sandbox_trust.py` and `tools/task_orchestrator/tests/test_sandbox_trust.py`.
- **Policy:** Strict canonical trust-store JSON; duplicate-key rejection; out-of-band SHA-256 pin; caller-supplied minimum version; unique key IDs; max 64 keys; Ed25519 algorithm and exact 32-byte public-key shape; UTC validity windows; active-only acceptance; revoked/retired/unknown/expired/not-yet-valid keys fail closed; backend errors and non-boolean success fail closed.
- **Trust boundary:** Ed25519 math is injected through an `Ed25519Backend`. The test backend is not cryptographic security. Protected deployment of the pinned digest and monotonically advanced version floor remains external; this module does not persist rollback state or create/rotate keys.
- **Expected tests:** Python 3.12 `compileall` and `python -m unittest discover -s tools/task_orchestrator/tests -p "test_*.py" -v` via Task Orchestrator CI.
- **Safety:** No private key, signing service, provider, VM, untrusted code execution, account, API key, payment method, source transfer, or spend. No app source/version/release/backend/payment/server changes.
- **Review:** Pending PR and CI. Do not claim production Ed25519 verification or execution authorization.


## 2026-11-24 — Stage 23: project memory refresh after PR #53

- **Base:** main at 3e613a8c03a39e4440c3702ac3505acb7b2eae27 (PR #53 squash merge).
- **Branch:** docs/refresh-memory-after-pr53-20261124.
- **Scope:** Documentation-only synchronization of repository baseline, trust-store adapter status, verification evidence, and next priorities.
- **Verified PR:** head b0b5f72c1d8c7f0940b1c1cfb8cb5dacdb1cb11b; Task Orchestrator Tests #45334662136 passed 271 tests; Project Memory Audit #45334662120 passed; Non-production PR Validation #45334662100 passed; Agent PR Lease and Scope Guard #45334659579 passed.
- **Safety:** Documentation only. No app source/version/release, provider, API key, VM, private-source transfer, signing key, untrusted execution, or spend.
- **Verification:** Pending docs PR checks and Project Memory Audit; do not claim this refresh merged until checks pass and merge is observed.
- **Final review cleanup:** Corrected stale PR/main snapshot labels and literal escaped line breaks in agent instructions before final CI.

## 2026-11-24 — PR #55: real Ed25519 verification backend

- Added `tools/task_orchestrator/ed25519_backend.py` using PyCA `cryptography` for public-key verification only.
- Added `tools/task_orchestrator/requirements-sandbox-crypto.txt` with exact version pins for cryptography, cffi, and pycparser; both Python CI workflows install binary wheels.
- Added RFC 8032 test vector 1, invalid/tampered signature coverage, and integration coverage through `PinnedTrustStoreVerifier`.
- Fixed invalid YAML block-scalar syntax in both `.github/workflows/task-orchestrator.yml` and `.github/workflows/pr-validation.yml` so the dependency-install step parses and executes.
- Final PR head: `56e48fac7e5cfdf25c07492daef9ed3cdd3c0805`. Successful runs: Task Orchestrator Tests `45354914545`; Project Memory Audit `45354914553`; Non-production PR Validation `45354914620`.
- PR #55 squash-merged as `3cc2e200dd02416d7b2fba02725b6734dffede39`.
- Limits retained: dependencies are not hash-locked; protected trust-root delivery, persistent anti-rollback, key lifecycle automation, independent runtime probes, and real VM acceptance remain open. No provider, VM, API key, private source transfer, untrusted execution, production action, or spend occurred.




## 2026-11-24 — PR #57 protected trust control plane design merged

- PR: https://github.com/majidbusy09-blip/jetconfig-vpn/pull/57
- Final PR head: `d60cf18554f37b0387bc6c5738edefdd2f04f602`.
- Squash merge commit: `e28e16ba9b4021d3974085639df4c461774e8eaf`.
- Scope: documentation/design only; added `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`, recorded D-013, and refreshed next-step/status references.
- Verification on the exact final head: Task Orchestrator Tests run `45358099449` — success; Project Memory Audit run `45358099476` — success; Non-production PR Validation run `45358099550` — success.
- The design specifies offline root trust, a signed audience-bound configuration envelope, monotonic epoch/version floors, atomic CAS, fail-closed semantics, rotation/revocation, append-only audit, and recovery.
- No service, KMS/HSM, root key, durable monotonic store, provider, VM, API key, external spend, or runtime execution was provisioned or used. This merge does not establish a production control plane or safe sandbox.
- Execution gates remain false: `execution_authorized: false`; `eligible_for_untrusted_execution: false`.


## 2026-11-24 — PR #59 trust configuration acceptance

- Added by PR #59, merged as `1e332fcd8f13c5ccebb352c31b72bbf09a27a1bb`; final PR head: `177a4090effd838add36188578a5d7e8a7c671f5`.
- Added `trust_config_acceptance.py` and its focused tests. It validates canonical schema-v1 envelopes, audience and UTC validity, bounded lifetime, root signature via an injected verifier, exact trust-store digest, and trust-store policy via `PinnedTrustStoreVerifier`.
- The monotonic-store interface requires a durable atomic compare-and-swap with append-only audit in one transaction. Acceptance is returned only after successful commit.
- Tests cover happy path/idempotency, rollback and conflict, malformed/oversized values, expiry/digest mismatch, CAS races, invalid prior state, and storage/audit failures. Fakes are test-only.
- Final-head CI: Task Orchestrator Tests `45361973408` success; Project Memory Audit `45361973336` success; Non-production PR Validation `45361973411` success; `validate-agent-pr` check `138334033651` success.
- Explicit non-deliverables: no production root key/verifier, persistent monotonic store, atomic audit backend, KMS/HSM, provider, network client, VM, or untrusted execution. Runtime flags remain false.


## 2026-11-24 — PR #67 runtime probe contract and CI path optimization

- PR #67 squash-merged as `b0b0b80515f17c01836f558ff5700189c9a7bf32`; final head `e216f2d7d9eab51f62b34733b630fd02af6c6973`.
- Added `tools/task_orchestrator/runtime_probe_manifest.json`, `docs/SANDBOX_RUNTIME_PROBE_SPEC.md`, and manifest inventory/trust-boundary tests for all 20 required probes.
- Added a tested path classifier so tooling-only PRs keep Python safety checks while avoiding unnecessary Java/Flutter setup, app analysis/tests and APK builds. App/build-affecting changes retain full validation. Hash-locked dependency installation from PR #63 is preserved.
- Final-head CI: Task Orchestrator Tests `45371950918`, Project Memory Audit `45371951039`, Non-production PR Validation `45371950980` — all success.

## 2026-11-24 — PR #68 host evidence collector contract

- PR #68 squash-merged as `90dd9f848998ebb0c18b6c584938fee148d6fced`; final head `f76cdf060a2d7166639f6469bbcdf453d52b539b`.
- Added `tools/task_orchestrator/sandbox_host_evidence.py` and `tools/task_orchestrator/tests/test_sandbox_host_evidence.py`.
- Collector validates the manifest-defined observer domains, explicit observer-ID allowlists, attempt/runtime/policy digest binding, monotonic offsets, UTC freshness, duplicate/missing observations, bounded raw payloads and aggregate evidence size. It serializes deterministic per-probe evidence and recomputes payload SHA-256; a failed observer remains a failed probe.
- Added `docs/SANDBOX_HOST_EVIDENCE_COLLECTOR.md` and README documentation.
- A first CI run exposed an assertion-order issue in the duplicate-observer test; it was corrected. The final exact head passed Task Orchestrator Tests `45376199406`, Project Memory Audit `45376199527`, and Non-production PR Validation `45376199739`.
- No VM, process, guest, socket, network request, provider, identity root, signing key, or untrusted code was used. The collector is not a runtime controller and does not cryptographically authenticate its caller-supplied observer identities.


## 2026-11-24 — PR #70 host lifecycle state machine contract

- PR #70 squash-merged as `e699293c1495f3137dd319e37764a2db6c5dfff3`; final head `a4b79467d850663ae10f8ffebb8e544f9ecf199e`.
- Added `tools/task_orchestrator/sandbox_host_lifecycle.py`, `tools/task_orchestrator/tests/test_sandbox_host_lifecycle.py`, and `docs/SANDBOX_HOST_LIFECYCLE.md`.
- The pure state machine validates pinned attempt/runtime/policy identity, monotonic event order/deadline, allowlisted events/failure codes, evidence accepted/rejected outcomes, explicit termination, and cleanup confirmation. Cleanup failure is terminal.
- Tests cover success and failure paths, cancellation, deadline expiry, adapter error, cleanup failure, identity mismatches, out-of-order events and malformed payloads.
- Final-head CI: Task Orchestrator Tests `45377376254`, Non-production PR Validation `45377376173`, Project Memory Audit `45377376300` — all success.
- No process, VM, provider, network, guest, filesystem, credential, or untrusted code was accessed. The state machine does not prove actual termination or cleanup.


## 2026-11-24 — PR #72 bounded artifact collector contract

- PR #72 squash-merged as `a199b82ef70f492c2b8df42087992a917d293c7c`; final head `26edb96019e3816e4e23cff24b957f2d0187ca12`.
- Added `tools/task_orchestrator/sandbox_artifacts.py`, `tools/task_orchestrator/tests/test_sandbox_artifacts.py`, and `docs/SANDBOX_ARTIFACT_COLLECTOR.md`; updated `tools/task_orchestrator/README.md`.
- The pure in-memory validator checks normalized relative allowlisted paths, rejects traversal and unsupported path components, rejects declared symlinks/directories/devices and link counts other than one, rejects duplicate paths and empty files, bounds file count/per-file/aggregate bytes/retention metadata, recomputes SHA-256 from exact supplied bytes, and emits a sorted canonical manifest bound to attempt/runtime/policy/evidence/report digests.
- Added adversarial coverage for hard-link metadata and malformed link-count values.
- Final-head CI passed: Task Orchestrator Tests `45379646169`, Non-production PR Validation `45379646094`, Project Memory Audit `45379646100`.
- The module does not open/stat files, authenticate metadata or signed reports, retain/delete files, or enforce actual retention. No filesystem collection, VM, provider, network, credentials, or untrusted code was used.


## 2026-11-24 — PR #74 signed observer authenticity contract

- PR #74 squash-merged as `b40642e9cb58446b60cc356f349656c31818d898`; final head `f633295b6c5ceb64eef183340d1fe5162b5edf59`.
- Added `tools/task_orchestrator/sandbox_observer_auth.py`, `tools/task_orchestrator/tests/test_sandbox_observer_auth.py`, and `docs/SANDBOX_OBSERVER_AUTHENTICITY.md`; updated orchestrator README.
- Added strict canonical JSON parsing and pinned observer registry validation (out-of-band digest, minimum version, exact audience, unique identities, domain/key/status/validity checks).
- Added host-challenge binding with a 32-byte nonce and 120-second maximum lifetime; envelope checks include observer identity/domain/key, attempt/runtime/policy/probe, sequence, UTC timestamp, monotonic offsets, outcome, payload digest/size, and Ed25519 signature through an injected verifier.
- Added an atomic replay-store protocol requiring one-time nonce consumption and strictly increasing per-observer sequence across attempts. Tests use a deterministic fake verifier and in-memory replay store.
- Successful results preserve `ProbeObservation` plus registry digest/version, key ID, sequence, nonce digest, and envelope digest in `AuthenticatedObserverResult`.
- Final-head CI: Task Orchestrator Tests `45382515116`, Non-production PR Validation `45382515212`, Project Memory Audit `45382515188` — all success.
- No durable replay store, challenge generator, TLS transport, identity provisioning, report signing, VM, provider, network, or untrusted code was used. Existing evidence bundle does not yet bind observer provenance.


## 2026-11-24 — PR #76 signed acceptance provenance schema v2

- PR #76 squash-merged as `d393d2e5bb0a93390b8d572bf540ff9ec3f1fe7c`; final head `87c19d15f714f4a21200d469ed828d4b83026861`.
- Added `tools/task_orchestrator/sandbox_acceptance_provenance.py`, `tools/task_orchestrator/tests/test_sandbox_acceptance_provenance.py`, and `docs/SANDBOX_ACCEPTANCE_PROVENANCE_V2.md`; updated orchestrator README.
- Kept schema-v1 acceptance verification unchanged; added a separate schema-v2 verifier that pins runtime ID and observer registry digest/version.
- V2 signs observer provenance records containing probe/domain/observer/key, registry digest/version, sequence, nonce/envelope digest, payload digest, and Ed25519 algorithm label.
- Verifier recomputes provenance digest and raw probe evidence digests; parses canonical evidence; validates required probe/domain coverage from manifest; cross-checks exact observer identity/domain and payload digest; checks time/monotonic fields; and rejects replayed or incomplete provenance.
- Initial CI found three test/logic issues (runtime expectation not bound, missing provenance detected too late, and an overly specific test regex). Fixed all three and reran exact final head.
- Final-head CI: Task Orchestrator Tests `45384423673` (355 tests), Non-production PR Validation `45384423800`, Project Memory Audit `45384423642` — all success.
- No report signer, private key, raw-envelope storage, durable replay store, TLS, VM, provider, network, or untrusted code was used.


## 2026-11-24 — PR #78 durable observer replay-store design

- PR #78 squash-merged as `74a5b2b760362494711949b799031dc628612671`; final head `156511739d82de7dac02adedb31aebc4e3ce4adb`.
- Expanded `ObserverReplayStore.consume` to receive observer/domain, attempt/runtime/policy/probe, registry digest/version, key ID, nonce/envelope digests, sequence, challenge expiry, and trusted acceptance timestamp.
- The verifier commits those values only after all envelope checks pass. Challenge expiry uses whole UTC-second precision; host acceptance time retains microseconds.
- Strengthened the in-memory fake to reject duplicate nonce/envelope digests and non-increasing per-observer sequence while retaining full audit context.
- Added `docs/SANDBOX_REPLAY_STORE_DESIGN.md` covering atomic serializable transactions, compare-and-swap sequence updates, uniqueness, audit, stable identity through key rotation, fencing, anti-rollback checkpoint, retention, failover, restore, and failure test matrix.
- Final-head CI: Task Orchestrator Tests `45385761279`, Non-production PR Validation `45385761459`, Project Memory Audit `45385761392` — all success.
- No durable DB/service, credentials, network, VM, provider, or untrusted execution was implemented or used.


## 2026-11-24 — PR #80 protected observer-envelope retention design

- PR #80 squash-merged as `6666266f59877e9a066188d418938661075ae38e`; final head `f41cee3685c3315ae3373f5c21f9fbaab9fa03dc`.
- Added `docs/SANDBOX_OBSERVER_ENVELOPE_RETENTION.md`; updated schema-v2 documentation and orchestrator README.
- Defined two-phase retention: exact-byte pre-acceptance staging with content-addressed paths and deterministic manifest; next report schema binds staging-manifest digest; post-acceptance artifact manifest binds retained envelopes to verified report digest.
- Specified no-follow descriptor-relative access, same-descriptor hashing, trusted path derivation, bounded size/count, quarantine, retention, cleanup, and independent offline re-verification.
- Clarified schema v2 does not include raw envelopes or a staging-manifest digest; it remains unchanged.
- Final-head CI: Task Orchestrator Tests `45386943800`, Non-production PR Validation `45386943924`, Project Memory Audit `45386943682` — all success.
- No filesystem collector, storage service, database, credentials, network, report signer, private key, VM, provider, or untrusted code was used.


## 2026-11-24 — PR #82 trusted acceptance report signer contract

- PR #82 squash-merged as `d7ef7ed4266ea2606acd76f6e36fb4822af7d179`; final head `d91ea3da44fc133e94621df4cae3dfd7dee174bf`.
- Added `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md`; updated orchestrator README, NEXT_STEPS and DECISIONS D-022.
- Specified trusted host-only signing boundary, exact raw-envelope and Ed25519 revalidation, read-only replay acceptance receipts, immutable ledger snapshot/fencing, schema-v3 binding to the pre-acceptance envelope manifest, independent post-sign verification and adversarial tests.
- Explicitly documented that a caller-created `AuthenticatedObserverResult` is not proof of verifier execution.
- Final-head CI: Task Orchestrator Tests `45390283412`, Non-production PR Validation `45390283324`, Project Memory Audit `45390283473` — all success.
- No signer/key/service, durable replay DB, filesystem collector, network, VM, provider, probe execution or untrusted execution was introduced.


## 2026-11-24 — PR #88 schema-v3 report pipeline and non-circular trusted signing

- PR #88 remains Draft/open/unmerged; base `main` is `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e`. Implementation checkpoint `566fbb58c4e039ef88abee64a987995b029ba534`.
- Added `sandbox_acceptance_report_v3.py`: deterministic report and raw-envelope manifest construction from exact probe evidence, raw observer envelopes, pinned registry, observer signature verification, and read-only replay receipts.
- Added `sandbox_acceptance_report_v3_verifier.py`: independent reconstruction and exact-byte verification, optional final report signature verification, and a verifier-side attestation issuer.
- Added `sandbox_trusted_report_signer.py`: strict schema-v3 and attestation validation, exact report/manifest digest binding, one-time authorization consumption, and injected protected signing backend.
- Added `sandbox_acceptance_pipeline_v3.py` to connect the non-executing stages; expanded host challenge CSPRNG generation and observer key rotation/revocation tests.
- Corrected a circular authorization design: the independent verifier validates unsigned report content first, then issues a short-lived attestation authorizing the signer; after signing, an independent pass verifies the final signature. The signer is not asked to prove a signature that cannot exist until after it signs.
- Final checkpoint CI: Task Orchestrator Tests run `45428730520` succeeded with 401 tests; Non-production PR Validation run `45428731306` succeeded with Flutter/APK build steps skipped for tooling-only changes; Project Memory Audit run `45428731849` succeeded, including app regression tests, semantic-index tests/generation, real-source task-intelligence smoke test, and lexical freshness verification.
- The semantic/resolved/critical-path indexes were uploaded as 30-day CI artifacts, not committed. This distinction must remain explicit in agent context.
- No mTLS deployment, KMS/HSM provisioning, private key, isolated signer service, durable Replay Store, production trust-control-plane, live probe, VM/provider, source transfer, untrusted execution, release, or deployment was performed.


## 2026-11-25 — Multi-project architecture Phase 1 and Phase 2A start

- PR #97 squash-merged as `914445b758d049ad5b97d670a66635f4cf8aba7b`.
- Added repository-neutral multi-project architecture, a project manifest JSON Schema with Flutter/Dart and Python-only examples, and a read-only onboarding procedure.
- PR #97 exact-head Project Memory Audit (`45483195909`), Non-production PR Validation (`45483195875`), and Agent PR Lease and Scope Guard (`45483192332`) passed. A later ready-for-review event occurred after lease release and the guard correctly failed closed; this was not the exact-head pre-release pass.
- Post-merge Project Memory Audit run `45484504394` was still running when this log entry was prepared; its conclusion must be verified separately.
- Created Phase 2A Issue #98. The lease claim is verified and active: task `project-registry-validation-20261125`, claim `202611250017ab98`, pinned base `914445b758d049ad5b97d670a66635f4cf8aba7b`.
- Added the initial pure validator `tools/task_orchestrator/project_registry.py` and focused tests `tools/task_orchestrator/tests/test_project_registry.py` on the isolated task branch. The validator is designed for the checked-in schema subset, compares trusted GitHub metadata, rejects duplicate project/repository identities, enforces lifecycle and runner availability, and computes canonical SHA-256 manifest digests.
- The task remains in progress. Exact-head tests, memory audit, scope guard, diff review, Draft PR, and lease release are still required.
- No external repository, API key, paid service, provider account, app source, release, deployment, or untrusted execution was changed or enabled.


## 2026-11-25 — Phase 2A registry validator first verification checkpoint

- PR #99 is Draft and open. Source/test checkpoint `835708e582513d73a7ec94ff632ffbdf93b77844`.
- Task Orchestrator Tests run `45486062484` passed all 414 tests, including project manifest schema validation, GitHub identity mismatch cases, duplicate identity rejection, lifecycle gating, fixed-runner availability, unsafe-path/URI checks, duplicate JSON-key parsing, and canonical digest tests.
- Non-production PR Validation run `45486062444` passed.
- Agent PR Lease and Scope Guard run `45486062154` passed with the active task lease.
- The first attempt failed because the checked-in schema also declares the optional `metadata.registered_at` field with JSON Schema `date-time` format. The validator was corrected to support URI and RFC3339 date-time formats, and malformed schema format declarations are now rejected with the registry error type.
- Project Memory Audit run `45486062165` was still in progress at this checkpoint. The final memory-only update in this PR requires fresh exact-head CI before the task is complete.
- No source/app changes outside the two validator files, no dependency changes, no network or persistence, no external project, no API spend, and no untrusted execution.


## 2026-11-25 — Phase 2B explicit project identity implementation

- PR #99 Phase 2A merged into main as `9b54a7158a1fbba7405f04ad503bcb8126c457bc`; Issue #98 closed as completed.
- Created Issue #100 for Phase 2B. Its task payload is bootstrapped through the existing v1 protocol only because the current lease bridge is v1; the v1 exception is bound to the exact JET VPN repository identity. Lease claim and renewal were verified; latest claim `202611250550de39`, pinned base `9b54a7158a1fbba7405f04ad503bcb8126c457bc`.
- Created Draft PR #101 on `agent/project-identity-intake-v2-20261125`.
- Added a declarative JET VPN manifest at `docs/projects/jet-vpn-android/manifest.json`; lifecycle is deliberately `registered`, not active.
- Added strict v1/v2 task payload parsing, v1 compatibility restriction, v2 binding validation against the trusted manifest and live GitHub metadata, and a v2 intake path.
- Added v2 handoff schema 3 with project identity, persisted the identity tuple and pinned base SHA into the local task record, and added identity comparisons for PR base/head repositories.
- Extended Issue revalidation and patch-review authorization to verify repository identity and prevent project-aware records from being downgraded to legacy v1.
- Initial PR #101 CI: Agent PR Lease and Scope Guard passed; Task Orchestrator Tests and Non-production PR Validation exposed remaining old patch-review consumers and test fixture mismatches. Those call sites and fixtures were updated. New exact-head CI is required; no passing result is claimed yet.
- No registry persistence, activation, context/envelope schema change, lease namespace change, workspace/cache/artifact namespacing, app-source change, external repo change, API spend, credentials, provider source upload, release, deployment, or untrusted execution.


## 2026-11-25 — PR authorization envelope v2 added to close downgrade path

- A control-plane review found that validating the current v2 Issue body and base/head repository identity was not sufficient by itself: an Issue could be changed to a legacy v1 body while an existing PR authorization envelope and lease remained.
- Extended the separate PR authorization envelope with schema v2. It binds the exact Issue-body SHA-256, validated project-binding tuple, and lease-pinned base SHA. V2 tasks require PR envelope v2; legacy v1 tasks require PR envelope v1.
- The agent context/input envelope contract remains unchanged. This is a PR control-plane envelope, not a context/envelope migration.
- Added tests for v2 PR authorization, base/head identity mismatch, PR envelope downgrade, project binding mismatch, and pinned base mismatch. Fresh exact-head CI is required.


## 2026-11-25 — Phase 2B exact-head verification completed

On implementation head `33357ea746d3e2a5147416a8da9385ee1002b340` (base `9b54a7158a1fbba7405f04ad503bcb8126c457bc`), all four required workflows passed:

- Task Orchestrator Tests: 426 tests — run `45534458358`.
- Non-production PR Validation — run `45534458288`.
- Agent PR Lease and Scope Guard — run `45534455835`.
- Project Memory Audit — run `45534458336`.

PR #101 remains Draft and unmerged for human review. No review submissions or review threads were present at verification time. Latest active lease claim: `202611250555cafe`; expiry `2026-11-25T04:34:16Z`.
