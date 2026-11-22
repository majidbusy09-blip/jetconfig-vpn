# JET VPN — Current Status

## Latest verified snapshot — 2026-11-22

- Repository: `majidbusy09-blip/jetconfig-vpn`.
- Default branch: `main`.
- Current main HEAD: `eae477a89816a5cfd475c596e166d5cb2575884a` (merged PR #17).
- PR #16 merged at `c4f7f4743b3c6ffc64d34a0efb0c19f41b236f1e`; it consolidated project-memory tooling, recovery/live-verification work, tests, CI and documentation.
- PR #17 merged at `eae477a89816a5cfd475c596e166d5cb2575884a`; it added the push-to-main trigger for the project-memory audit.
- Application version: `2.4.5+284`; `pubspec.yaml` blob `adc3b22a4538db4738bec789e3c3badf26e4f710`.
- `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59` (9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points).
- The app source tree includes regression tests under `test/`, isolated Dart Analyzer tooling under `tools/project_memory/semantic/`, lexical index tooling, native V2Ray patch sources, and CI workflows.
- Project-memory audit after PR #17: [Run #45029689706](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45029689706) completed successfully on `eae477a89816a5cfd475c596e166d5cb2575884a`, triggered by `push`.
- PR #17 pre-merge audit: [Run #45029128595](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45029128595) completed successfully on its PR head.
- Active ruleset `main-protection` targets only `~DEFAULT_BRANCH`; enforces PRs, the status check `Verify generated code index and memory freshness`, resolved review threads, Squash-only merges, deletion protection and force-push protection. Bypass list is empty.
- User-reported physical-device tests passed for cold restore, background resume, explicit disconnect during verification, and profile switch during verification. Device model/build and diagnostic logs were not supplied; do not generalize beyond that reported test environment.
- No app version bump, production release, deployment, bot/payment/backend/server change was part of PR #16 or #17.

## Current engineering boundaries

- Primary objective: build a reliable, independent programming collaborator with durable project memory and safe execution.
- Work on isolated branches; inspect complete diffs; run relevant checks; open PRs; never merge, release, deploy, or dispatch the production release workflow without explicit user approval.
- Telegram bot, payment, backend and server work are deferred unless a concrete issue appears or the user changes priority.
- JET VPN TV and حسابگر من are separate repositories; do not infer their implementation from this repository.

## Historical detail preservation

The complete pre-refresh status document is preserved verbatim at [`docs/archive/CURRENT_STATUS_pre_memory_refresh_20261122.md`](archive/CURRENT_STATUS_pre_memory_refresh_20261122.md). It contains historical PR snapshots and test/build evidence; some statuses and SHAs are superseded and must not be treated as current.

## Known memory-maintenance issue being corrected

Earlier snapshot blocks in this document and related memory files incorrectly described PR #16 as open and used the pre-merge main SHA. This refresh supersedes those operational claims. Historical development records remain append-only in `docs/DEVELOPMENT_LOG.md`.

## Exact source identity

- Main commit: `eae477a89816a5cfd475c596e166d5cb2575884a`.
- `lib/main.dart`: `3d28693b7be8bfe309a850923599830e1a65ab59`.
- `pubspec.yaml`: `adc3b22a4538db4738bec789e3c3badf26e4f710`.
- App version: `2.4.5+284`.
