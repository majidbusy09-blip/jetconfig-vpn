# JET VPN — Prioritized Next Steps

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution. Every candidate task must pass the criterion in `AGENTS.md`.

## Current verified state — 2026-11-22

- PR #16: open, draft, unmerged; inspected head `895124409f2c6a302e2ede3c73ccd3af54c747a0`.
- PR validation [Run #45021900956](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900956): passed analysis, app tests, Debug smoke build, ARM64 split Release-mode comparison build, and artifact uploads.
- Project-memory audit [Run #45021900965](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45021900965): passed application tests, AST/resolved-index tooling tests, deterministic generation, critical-path generation, lexical freshness, and artifact uploads.
- Verified ARM64 comparison APK: 27,773,007 bytes (26.48 MiB); native libraries only in `arm64-v8a`. Artifact ID `14754511282`, expires 2026-11-29.
- Production workflow generates application ID `com.jetconfig.vpn.jetconfig_vpn` and signs with the configured release keystore. The comparison APK uses the Android Debug certificate; signing compatibility is not established.
- App source/version unchanged; main branch unchanged; no merge/release/deployment.

## P0 — Safe device-validation path

1. Add a distinct validation application ID (for example, `com.jetconfig.vpn.jetconfig_vpn.validation`) to the non-production CI build only, with a visible “JET VPN TEST” label. Keep the production release workflow and production application ID untouched.
2. Verify the resulting APK package ID, signer identity, ABI contents, and installability in CI. Keep this artifact separate from production release artifacts.
3. Only then offer the test APK for side-by-side installation. Device test cases: cold restore, resume with blocked tunnel traffic, explicit disconnect during in-flight verification, and profile switch during verification. Record exact device/Android version and results.
4. Do not claim VPN recovery is production-validated until real device and tunnel-traffic checks pass.

## P1 — Review and safely activate the collaborator foundation

1. Review the complete PR #16 diff against main, with special attention to `lib/main.dart` integration points and the test coverage for lifecycle/cancellation.
2. Verify generated project-memory outputs and all docs against the exact PR head; stale snapshots block approval.
3. After device evidence and final review, present a merge decision for explicit user approval. Do not merge autonomously.

## P2 — Improve project memory and task execution

- **Completed in this branch:** added a mandatory task template and aligned the current status, next steps, and development log with the latest verified CI head.
- Extend source-fingerprint coverage to documented architecture/API/storage decisions and symbol-level evidence as the app is split into files.
- Keep the lexical index, semantic index, and critical-path report clearly distinguished; none alone proves runtime behavior.
- Build a task-to-evidence trail: each task should record loaded context, source SHA, intended diff, exact tests, artifact/PR, and memory update.

## Deferred by user

- Telegram bot, payment, backend, and server work: currently working; do not prioritize absent a concrete issue or changed instruction.
- New product features, marketing, and visual redesigns: lower priority than collaborator reliability and project verification.

## Approval boundary

PR #16 remains draft/unmerged. No merge, production release, deployment, production workflow dispatch, or installation over the production app without explicit approval and verified package/signature compatibility.
