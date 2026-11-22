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
