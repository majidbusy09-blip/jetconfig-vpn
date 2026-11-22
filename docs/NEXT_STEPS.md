# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution. Every task must pass the criterion in `AGENTS.md`.

## Current verified state — 2026-11-22

- PR #16 is open, draft, and unmerged. Current validated source head for the isolated validation APK: `8571a10a8676bf114ca6eda07657da026e550085`.
- PR validation [Run #45023210674](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210674) succeeded end-to-end, including Flutter analysis/tests, debug build, ARM64 release-mode APK build, and APK package/label/signature/ABI verification.
- Project-memory audit [Run #45023210902](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45023210902) succeeded.
- Install candidate: artifact `JET-VPN-TEST-arm64-validation-42` (ID `14754751347`), package `com.jetconfig.vpn.jetconfig_vpn.validation`, label `JET VPN TEST`, version `2.4.5`, ARM64 only, APK size 27,748,544 bytes. Artifact expires 2026-11-29.
- The APK uses Android Debug signing, not the production release key. Its package ID is distinct and the validation updater is disabled.
- No physical-device test, merge, production release, or deployment has occurred. Main and production release workflow remain untouched.

## P0 — Physical-device validation

1. Install `JET VPN TEST` alongside the existing JET VPN; do not uninstall or overwrite the production app. The test package is ARM64-only and intended for compatible 64-bit Android devices.
2. Follow the exact checklist in [DEVICE_VALIDATION.md](DEVICE_VALIDATION.md). Record device model, Android version, app behavior, and relevant logs for each scenario.
3. Test only VPN connection/recovery behavior. Do not test purchases, payments, subscriptions, or production updater behavior in the validation build; its updater is intentionally disabled.
4. If any test fails, capture the exact sequence and logs before changing code. Fix only the demonstrated defect, add a regression test, rebuild, and repeat.
5. Do not claim recovery is production-validated until real tunnel traffic and Android lifecycle behavior pass on-device.

## P1 — Review and activate the collaborator foundation safely

1. Review the complete PR #16 diff against main, especially `lib/main.dart` integration points, cancellation/generation guards, and test coverage.
2. Verify generated project-memory outputs and all docs against the exact final PR head; stale snapshots block approval.
3. After device evidence and final review, present a merge decision for explicit user approval. Never merge autonomously.

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
