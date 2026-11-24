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
2. Read `docs/TASK_TEMPLATE.md` and use it to structure every non-trivial task.
3. Read `docs/CURRENT_STATUS.md`, `docs/NEXT_STEPS.md`, and the relevant entries in `docs/DEVELOPMENT_LOG.md`.
4. Read the relevant architecture, API, data, payment, issue, decision, and test documents.
5. Check the actual target branch and current commit SHA. Documentation is a guide, not a substitute for current source.
6. Verify every relevant symbol, caller, state variable, persistence key, network request, native patch, and workflow against the current source.
7. If a document's `Verified against` commit differs from the target source commit, treat its implementation claims as potentially stale and re-verify them.

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
- Current main commit (verified 2026-11-24): `3e613a8c03a39e4440c3702ac3505acb7b2eae27`.
- PR #20 merged at `15fea59e4f83704e0a9955363e0f0b237aac09ac`; PRs #38–#44 merged through PR #44; PRs #46–#53 are merged.
- PR #46 memory refresh merged at `4dbe01eda4078342c17f16a4111919bebaa616ae`.
- PR #47 synthetic-only sandbox lifecycle contract merged at `f360d50b13064c7136eb7ce4a3b38e3413e5b333`.
- PR #48 project-memory refresh merged at `53e00ac2ad5e260a4d214772da4ba9bccd3499f4`.
- PR #49 independent sandbox evidence verifier merged at `4fc59de5a8d6ef9323de3b48896f78f3c426732d`.
- PR #52 memory refresh merged at `440569f769fd0d6871ac370d7923417637f90dc8`.
- PR #53 head `b0b5f72c1d8c7f0940b1c1cfb8cb5dacdb1cb11b` passed Task Orchestrator Tests #45334662136 (271 tests), Project Memory Audit #45334662120, Non-production PR Validation #45334662100, and Agent PR Lease and Scope Guard #45334659579; squash-merged as `3e613a8c03a39e4440c3702ac3505acb7b2eae27`.
- `sandbox_trust.py` delegates Ed25519 signature mathematics to an injected backend and does not persist rollback state or authorize execution.
- PR #51 binds all 20 signed probe digests to supplied raw evidence bytes and independently recomputes SHA-256; merged at `1438d0a047523a22fee26e72ae12cf34cebbb95e`.
- `lib/main.dart` blob: `3d28693b7be8bfe309a850923599830e1a65ab59`; source metrics: 9,008 lines / 352,770 UTF-8 bytes / 336,710 Unicode code points.
- `pubspec.yaml` blob: `adc3b22a4538db4738bec789e3c3badf26e4f710`; app version remains `2.4.5+284`.
- PR #47 head `846b4cf15ba176178c811f45e51384bc25ae3c28` passed Task Orchestrator Tests #45314331567 (247 tests, including 13 sandbox tests), Project Memory Audit #45314331612, and `validate-agent-pr`. Non-production PR Validation retry #45313415713 passed after an initial Maven Central HTTP 429; PR #48 validation #45314885244 also passed. PR #49 passed Task Orchestrator Tests #45320041554 (259 tests), Project Memory Audit #45320041561, and `validate-agent-pr` #45320038880. PR #51 head `42c208398ef0b044ba54c17ca183957022eb0288` passed Task Orchestrator Tests #45325193322, Project Memory Audit #45325193253, Agent PR Lease and Scope Guard #45325195790, and Non-production PR Validation #45325193266.
- Active `main-protection` ruleset requires a PR and the `Verify generated code index and memory freshness` check, blocks deletion/force pushes, permits Squash only, and has no bypass actors.
- The local orchestrator supports fixture dispatch, local result ingestion, content-addressed patch artifacts, and live review-only authorization. Success remains `ready_for_human_review`, `applied: false`.
- `sandbox_contract.py` now defines a synthetic-only provider protocol, strict resource/capability checks, VM-only snapshot validation, lifecycle state machine, bounded artifact verification, and confirmed termination/destruction. It has only a fake provider test; it is not a real sandbox.
- No live model provider, untrusted code execution, vendor account, API key, payment method, real sandbox, private-source transfer, provider spend, or production deployment is enabled or authorized.

Snapshot verification source: GitHub branch/ref, file/blob, PR, workflow-run, and ruleset APIs checked on 2026-11-24.


## Sandbox trust boundary update — 2026-11-24

The repository includes `sandbox_acceptance.py`, a strict verifier for independently signed runtime-acceptance reports. It is not a probe runner, signing service, provider adapter, or execution authorization. Production use requires an out-of-band pinned asymmetric public key and a separately controlled probe suite. A passing report must never be interpreted as permission to execute untrusted code; the verifier explicitly returns `execution_authorized: false`.


## Current sandbox evidence gate

PR #49 merged `sandbox_acceptance.py`, a strict verifier for independently signed runtime acceptance reports. It is not the runtime probe runner or an execution authorization. Production use requires an independently controlled probe suite and out-of-band pinned asymmetric public key. Never enable untrusted code execution from a report alone.

## Authoritative snapshot superseding earlier status — 2026-11-24

- Current main includes PR #55, squash merge commit `3cc2e200dd02416d7b2fba02725b6734dffede39`. This supersedes the earlier main SHA and PR #53-only snapshot recorded above.
- PR #55 adds `tools/task_orchestrator/ed25519_backend.py`, a PyCA `cryptography`-backed Ed25519 public-key verification adapter, plus `requirements-sandbox-crypto.txt` and RFC 8032/integration tests.
- Exact PR #55 head: `56e48fac7e5cfdf25c07492daef9ed3cdd3c0805`. Successful final-head workflows: Task Orchestrator Tests run `45354914545`; Project Memory Audit run `45354914553`; Non-production PR Validation run `45354914620`. Each completed with conclusion `success`.
- The Task Orchestrator run installed pinned crypto dependencies, compiled modules, and passed the orchestrator test suite. Non-production validation passed its dependency-install, safety-gate/lifecycle, static analysis, application tests, and validation APK build steps.
- Dependency versions are exact pins, not hash-locked artifacts: `cryptography==50.0.2`, `cffi==2.1.1`, `pycparser==3.12`. Provenance/hash verification remains a supply-chain hardening item.
- The backend performs verification only. It does not load private keys, sign, generate keys, provision a provider, or authorize code execution. Protected out-of-band trust-store digest/minimum-version delivery, persistent anti-rollback, key lifecycle, independent host/guest probes, and real VM acceptance remain outstanding.
- `execution_authorized` and `eligible_for_untrusted_execution` remain false. GitHub-hosted runner, Bubblewrap self-test, and current evidence verifiers do not establish a safe runtime for untrusted code.

## Latest authoritative update — PR #56 and trust control plane design (2026-11-24)

- PR #56 project-memory refresh merged as `5354ba7c38d1b27ff75ace2ed288feb50551d701`; its final head `e07b35b4ccde0b78c50bf3bada16b1ad1ca9bf3f` passed Project Memory Audit run `45356110882` and Non-production PR Validation run `45356110761`.
- The protected trust-control-plane design is in `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`; decision D-013 is in `docs/DECISIONS.md`.
- The design is not an implementation: no root signing key, KMS/HSM, transactional monotonic store, service, provider, or VM exists. A fake in-memory store may be used for deterministic tests only and must never be called production anti-rollback.
- Next safe implementation: strict provider-neutral signed-envelope validator + monotonic-store protocol with fake-only tests and explicit non-production status. Follow with the independent 20-probe runner/host-controller work.
- Execution remains disabled: `execution_authorized: false`, `eligible_for_untrusted_execution: false`.




## Authoritative snapshot — PR #57 merged (2026-11-24)

- PR #57, "docs: design protected trust control plane and anti-rollback", was squash-merged as `e28e16ba9b4021d3974085639df4c461774e8eaf`. Its final head was `d60cf18554f37b0387bc6c5738edefdd2f04f602`.
- On that exact final head, Task Orchestrator Tests run `45358099449`, Project Memory Audit run `45358099476`, and Non-production PR Validation run `45358099550` all completed successfully.
- PR #57 adds the design in `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md` and records decision D-013. It is design documentation only; it does not provision a root key, KMS/HSM, transactional store, service, provider, VM, or production anti-rollback mechanism.
- Next safe implementation is a provider-neutral signed-envelope acceptance module with injected root-signature verification and a monotonic-store interface. Tests may use deterministic fake verification and an in-memory CAS store only; these are not production trust or durable anti-rollback.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`. Do not execute untrusted code or provision external infrastructure without the separate approvals described above.
