# JET VPN — Prioritized Next Steps

## Latest verified snapshot — 2026-11-22 (supersedes older status entries below)

- PR #16 current head: `1d9bb95d71eb2b3426e57a236cea28edec727b14`; branch `integration/memory-and-recovery-20261122`; base `main` at `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`.
- Application source SHA remains `8571a10a8676bf114ca6eda07657da026e550085`; commits after that source snapshot are documentation-only.
- PR #16 is open, Draft, unmerged, and GitHub reports it mergeable. Diff: 38 files, 3,577 additions, 457 deletions.
- Project-memory audit run [#45026323360](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323360) **succeeded** on the exact current head. Application regression tests, AST indexer tests, resolved-element indexer tests, critical-path tests, deterministic semantic generation, lexical index freshness, and both artifact uploads passed.
- Non-production PR validation run [#45026323476](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45026323476) **succeeded** on the exact current head. Validation-preparation tests, Flutter analysis, app tests, debug smoke build, split ARM64 release-mode build, package/label/signature/ABI checks, and artifact uploads passed.
- Latest ARM64 test artifact: `JET-VPN-TEST-arm64-validation-69`, artifact ID `14756425339`, ZIP size 27,040,234 bytes, expires 2026-11-29. It is an isolated test APK, not production-signed and not for distribution or updating production.
- Latest semantic artifacts: `jet-vpn-code-index` ID `14755568224` and `jet-vpn-semantic-ast-index` ID `14755153930`, both retained until 2026-12-22.
- User-reported device tests passed for all four scenarios: cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device model/build and diagnostic logs were not supplied; do not generalize beyond the tested environment.
- PR review submissions: none. Inline review threads: none.
- Final scoped diff review found no source-level blocker in the inspected VPN verifier/recovery integration, validation workflow, or project-memory workflow. CI does not prove all Android/device/network conditions.
- Production source on `main`, app version `2.4.5+284`, payment, bot, backend, server configuration, and production release workflow remain outside this PR's changes. No merge, release, or deployment has occurred.
- Next action: present the merge recommendation and wait for explicit user approval. Do not merge, mark ready, release, deploy, or dispatch the production workflow without that approval.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution. Every task must pass the criterion in `AGENTS.md`.

## Current verified state — 2026-11-22

- PR #16 is open, draft, and unmerged. Current validated source head for the isolated validation APK: `8571a10a8676bf114ca6eda07657da026e550085`.
- PR validation [Run #45023210674](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210674) succeeded end-to-end, including Flutter analysis/tests, debug build, ARM64 release-mode APK build, and APK package/label/signature/ABI verification.
- Project-memory audit [Run #45023210902](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210902) succeeded.
- Install candidate: artifact `JET-VPN-TEST-arm64-validation-42` (ID `14754751347`), package `com.jetconfig.vpn.jetconfig_vpn.validation`, label `JET VPN TEST`, version `2.4.5`, ARM64 only, APK size 27,748,544 bytes. Artifact expires 2026-11-29.
- The APK uses Android Debug signing, not the production release key. Its package ID is distinct and the validation updater is disabled.
- No physical-device test, merge, production release, or deployment has occurred. Main and production release workflow remain untouched.

## P0 — Physical-device validation — user reports passed

- User reports all four scenarios in [DEVICE_VALIDATION.md](DEVICE_VALIDATION.md) passed: cold start/restore, background resume, explicit disconnect during verification, and profile switch during verification.
- The result is recorded as user-reported evidence; device model, Android build, network type, and diagnostic logs were not supplied. Do not overgeneralize beyond the tested environment.
- This closes the immediate device-test action. If a defect appears later, capture logs and reproduce before modifying code.
- Purchases, payments, subscriptions, and production updater behavior remain untested and out of scope for this validation APK.

## P1 — Final PR #16 review and merge decision

1. Complete a final review of all changed files against main, focusing on `lib/main.dart` integration points, cancellation/generation guards, CI safety, and test coverage.
2. Verify generated project-memory outputs and all docs against the exact final PR head; stale snapshots block approval.
3. Check CI and PR review feedback on the final head. Resolve any blockers and report residual risks.
4. Present a concise merge recommendation and wait for explicit user approval. Never merge autonomously.

## P2 — Improve project memory and task execution

- Keep task-to-evidence trails: loaded context, source SHA, intended diff, exact tests, artifact/PR, and memory update.
- Extend source-fingerprint coverage to architecture/API/storage decisions and symbol-level evidence as the app is split into files.
- Keep lexical index, semantic index, and critical-path report distinct; none alone proves runtime behavior.
- Prioritize read-only analysis, scoped branches, regression tests, reproducible CI, and safe review workflows.

## Deferred by user

- Telegram bot, payment, backend, and server work: currently working; do not prioritize absent a concrete issue or changed instruction.
- New product features, marketing, and visual redesigns: lower priority than collaborator reliability and project verification.

## Approval boundary

PR #16 remains draft/unmerged. No merge, production release, deployment, production workflow dispatch, or installation over the production app without explicit approval and verified package/signature compatibility.
