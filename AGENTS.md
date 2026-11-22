# JET VPN repository agent instructions

This file is mandatory operating guidance for any AI agent or contributor working in this repository.

## Mission and priority test

The primary objective is to build a reliable, independent programming collaborator with durable project memory.

Before prioritizing any task, ask exactly:

**«آیا این کار ما را به داشتن یک همکار برنامه‌نویس مستقل، دقیق و دارای حافظه پروژه نزدیک‌تر می‌کند؟»**

If the answer is no, the task must not receive priority unless the user explicitly requests it. If the answer is yes, state briefly which capability it improves: project understanding, source navigation, implementation, verification, durable memory, or safe maintenance.

## Mandatory context-loading sequence

Before proposing or changing code:

1. Read this file and `docs/PROJECT_CONTEXT.md`.
2. Read `docs/CURRENT_STATUS.md`, `docs/NEXT_STEPS.md`, and the relevant entries in `docs/DEVELOPMENT_LOG.md`.
3. Read the relevant architecture, API, data, payment, issue, decision, and test documents.
4. Check the actual target branch and current commit SHA. Documentation is a guide, not a substitute for current source.
5. Verify every relevant symbol, caller, state variable, persistence key, network request, native patch, and workflow against the current source.
6. If a document's `Verified against` commit differs from the target source commit, treat its implementation claims as potentially stale and re-verify them.

Do not assume previous chat context is complete. Git-tracked project memory is the durable baseline.

## Scope and repository boundaries

- This repository is the Flutter Android JET VPN client.
- Do not assume the PHP backend, Telegram bot, website/admin, Cloudflare worker, or JET VPN TV source is present here.
- Server-side behavior is **unverified** unless its authoritative source is separately inspected.
- Never infer a missing file or implementation from an old ZIP, README prose, or product description.

## Change-control protocol

1. Work on a dedicated branch created from the latest appropriate base.
2. Keep one task coherent and minimize unrelated changes.
3. Do not commit directly to `main`.
4. Do not merge a PR, publish a Release, create a production tag, or trigger a production deployment without explicit user approval.
5. Before editing, state the intended files, impact, assumptions, and risks.
6. After editing, inspect the complete diff and confirm only intended paths changed.
7. Run relevant formatting, analysis, tests, and build checks where possible. Record exact commands and outcomes.
8. Open or update a PR for review. Leave it unmerged pending explicit approval.
9. Update project memory in the same change when behavior, architecture, APIs, storage, risks, or workflow changes.

## Release boundary

`.github/workflows/build.yml` is manual-only. It requires `workflow_dispatch`, the selected ref to be exactly `main`, and the explicit Boolean input `confirm_release=true`. Ordinary pushes and PR merges do not publish a Release. The release job has `contents: write` scoped to that job. A manually confirmed run can publish signed APK variants and a public GitHub Release. Never dispatch this production workflow or approve a release without explicit user authorization.

## Engineering rules

- Preserve existing behavior unless the requested change explicitly changes it.
- Trace connection intent, native VPN state, Flutter UI state, app lifecycle, recovery generations, timers, and notification-originated disconnects before touching VPN logic.
- Never treat native CONNECTED status alone as proof of working internet; inspect the verification path.
- Treat credentials, payment tokens, signing secrets, and user data as sensitive.
- Never print or commit secrets. Avoid logging credentials, tokens, or full sensitive URLs.
- Do not change app version/build number without a release reason and approval.
- Do not silently broaden a task into refactoring or feature work.
- Mark facts as `verified`, `client-observed/server-unverified`, `inferred`, or `unknown`.

## Evidence and reporting

Every material implementation claim should cite a source path and symbol/line range and identify the verified commit SHA. For tests, distinguish:
- executed and passed;
- executed and failed;
- skipped because no test exists;
- not run / unavailable.

A successful build is not a runtime/device test. A CI workflow definition is not evidence that a workflow passed.

## Memory maintenance

- Keep `docs/generated/jet_vpn_code_index.json` synchronized with `lib/main.dart`; regenerate it with `python tools/project_memory/index_dart.py --write`.
- Before submitting a source change, run `python tools/project_memory/index_dart.py --check --check-status`. A stale index or source fingerprint is a blocking documentation-maintenance failure; update the index and `docs/CURRENT_STATUS.md` in the same PR.
- Treat the generated lexical index as a navigation aid only, not a semantic Dart AST, verified call graph, or proof of runtime reachability.
- The isolated semantic tooling resolves every tracked `lib/**/*.dart` file discovered by `git ls-files`; its generated resolved index is a CI artifact, not committed application source.
- `docs/critical_paths.json` contains curated entrypoint anchors; the generated critical-path report is a static transitive closure over resolved invocation edges, not proof of runtime execution. Revalidate anchors after symbol moves/renames.
- Native Java patch files are linked as explicit cross-language boundaries, not analyzed as Dart Elements.
- Keep `docs/CURRENT_STATUS.md` tied to a precise branch, commit SHA, source file blob SHA, app version, and snapshot date.
- Keep `docs/KNOWN_ISSUES.md` limited to evidence-backed issues; include confidence and reproduction/verification status.
- Record accepted technical choices in `docs/DECISIONS.md`.
- Append meaningful work and exact verification results to `docs/DEVELOPMENT_LOG.md`.
- Keep next actions prioritized in `docs/NEXT_STEPS.md`.
- If source changes invalidate a document, update it or explicitly mark it stale in the same PR.
- Do not overwrite history: append log entries and preserve superseded decisions with status.

## Current authoritative source snapshot

- Repository: `majidbusy09-blip/jetconfig-vpn`
- Branch: `main`
- Commit: `1f2519923cdd9f85ab280a3a4359d7ed5aed3949`
- `.github/workflows/build.yml` blob: `abdb595af8df6b2d02ab0ba1da665ac9de1d6461`
- `lib/main.dart` blob: `df2914b2954d723869e4196d96f96b050618985a`
- `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`
- App version: `2.4.5+284`
- Snapshot date: 2026-11-22
