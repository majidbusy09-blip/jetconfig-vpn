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



## Authoritative snapshot superseding earlier entries — PR #59 (2026-11-24)

- Current verified main includes PR #59, squash merge commit `1e332fcd8f13c5ccebb352c31b72bbf09a27a1bb`; this supersedes all earlier main HEAD values recorded above.
- PR #59 adds `tools/task_orchestrator/trust_config_acceptance.py` and `tools/task_orchestrator/tests/test_trust_config_acceptance.py`.
- The module is a provider-neutral reference acceptance layer: strict canonical signed-envelope parsing, audience/time/digest checks, injected root-signature verification, trust-store validation, and a monotonic-store protocol whose contract requires atomic durable CAS plus append-only audit.
- It is not production-ready. No production root verifier/key is provisioned; no durable CAS/audit implementation exists. In-memory store and fake verifiers/backends are test-only.
- PR #59 final head `177a4090effd838add36188578a5d7e8a7c671f5` passed Task Orchestrator Tests run `45361973408`, Project Memory Audit run `45361973336`, Non-production PR Validation run `45361973411`, and `validate-agent-pr` check `138334033651`; then squash-merged.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`. Do not provision a root key, production persistence, provider, VM, or run untrusted code without separate approval and independent evidence.


## Authoritative snapshot — PRs #67 and #68 merged (2026-11-24)

- PR #67 squash merge: `b0b0b80515f17c01836f558ff5700189c9a7bf32`; final head `e216f2d7d9eab51f62b34733b630fd02af6c6973`.
- PR #67 final-head checks all passed: Task Orchestrator Tests `45371950918`, Project Memory Audit `45371951039`, Non-production PR Validation `45371950980`.
- PR #67 adds the machine-readable 20-probe contract in `tools/task_orchestrator/runtime_probe_manifest.json`, specification in `docs/SANDBOX_RUNTIME_PROBE_SPEC.md`, and unit-tested changed-path classification to avoid unnecessary Flutter/APK builds for tooling-only PRs while retaining Python safety checks and hash-locked dependency installation.
- PR #68 adds `sandbox_host_evidence.py`, deterministic trust-boundary tests, and `docs/SANDBOX_HOST_EVIDENCE_COLLECTOR.md`. Squash merge: `90dd9f848998ebb0c18b6c584938fee148d6fced`; final head `f76cdf060a2d7166639f6469bbcdf453d52b539b`.
- PR #68 final-head checks all passed: Task Orchestrator Tests `45376199406`, Project Memory Audit `45376199527`, Non-production PR Validation `45376199739`.
- The host evidence collector only validates and assembles bounded observations from caller-configured observer IDs. It binds evidence to attempt/runtime/policy digest, monotonic offsets, timestamps, observer domains, payload and host-recomputed digests. It has no probe runner, subprocess, VM, socket, network client, provider integration, identity provisioning, or signing implementation.
- Observer identity allowlists are not cryptographically authenticated by this module; production provisioning must be out-of-band. Fake observer IDs are test fixtures only.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`. No untrusted code execution, provider, VM, API key, private-source transfer, KMS/HSM, or spend is authorized.


## Authoritative snapshot — PR #70 merged (2026-11-24)

- PR #70, `feat(sandbox): add pure host lifecycle state machine contract`, squash-merged as `e699293c1495f3137dd319e37764a2db6c5dfff3`; final head `a4b79467d850663ae10f8ffebb8e544f9ecf199e`.
- Final-head checks all passed: Task Orchestrator Tests `45377376254`, Non-production PR Validation `45377376173`, Project Memory Audit `45377376300`.
- Adds `tools/task_orchestrator/sandbox_host_lifecycle.py`, a pure typed state-transition validator for readiness, observation, evidence accepted/rejected, termination, runtime termination, and cleanup. It pins attempt/runtime/policy identity and monotonic start/deadline; rejects invalid ordering and failure codes.
- It invokes no adapter and has no process, shell, filesystem, socket, network, VM, guest, provider, or credential capability. It records lifecycle claims; it does not prove a runtime was actually terminated or cleaned.
- Deterministic tests cover success, rejected evidence, cancellation, deadline, adapter failure, cleanup failure, identity mismatch, and invalid transitions.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #72 merged (2026-11-24)

- Current `main` includes PR #72 squash merge `a199b82ef70f492c2b8df42087992a917d293c7c`; PR #72 final head: `26edb96019e3816e4e23cff24b957f2d0187ca12`.
- Final-head CI passed: Task Orchestrator Tests `45379646169`, Non-production PR Validation `45379646094`, and Project Memory Audit `45379646100`.
- PR #72 adds `tools/task_orchestrator/sandbox_artifacts.py` and deterministic in-memory tests. It validates normalized relative paths under fixed `artifacts/` and `reports/` roots; rejects traversal, symlink/directory/device declarations, duplicate paths, empty content, and caller-declared hard links; bounds inventory to 64 artifacts, 256 KiB per file, 2 MiB aggregate, and 30-day retention metadata; recomputes SHA-256 from supplied bytes; and emits a deterministic manifest bound to attempt, runtime, policy, evidence, and acceptance-report digests.
- The artifact module is a pure in-memory validator, not a trusted filesystem collector. Its `kind`, `symlink_target`, and `link_count` fields are caller-supplied assertions, not proof of actual inode properties. It does not open/stat files, authenticate signed reports, enforce retention, or authorize execution.
- A future trusted host collector must use descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, trusted retention, and independently verified report/evidence bindings.
- No VM, provider, network, credentials, filesystem collector, private-source transfer, KMS/HSM, spend, or untrusted code execution was used. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #74 merged (2026-11-24)

- Current `main` includes PR #74 squash merge `b40642e9cb58446b60cc356f349656c31818d898`; final PR head: `f633295b6c5ceb64eef183340d1fe5162b5edf59`.
- Final-head CI passed: Task Orchestrator Tests `45382515116`, Non-production PR Validation `45382515212`, and Project Memory Audit `45382515188`.
- PR #74 adds `tools/task_orchestrator/sandbox_observer_auth.py` and deterministic tests. It validates canonical signed observer envelopes, an externally pinned registry digest/version/audience, observer-to-domain/key mapping, a one-time host challenge bound to audience/observer/attempt/runtime/policy/probe, UTC validity, payload digest/size, monotonic offsets, Ed25519 signature through an injected verifier, and an atomic replay-store protocol for nonce consumption plus strictly increasing per-observer sequence.
- Successful verification returns `AuthenticatedObserverResult`: the existing `ProbeObservation` plus registry digest/version, key ID, sequence, nonce digest, and envelope digest. Only `result.observation` is passed to the current evidence collector; preserve the wrapper provenance separately.
- No host challenge generator, TLS transport, identity provisioning, durable replay-store implementation, or signed-report integration exists. Registry pins must come from protected out-of-band configuration; production signature verification must use the existing pinned Ed25519 trust-store verifier.
- The current `CollectedEvidenceBundle` does not retain the authenticated envelope/registry/sequence provenance. The next phase must bind those fields and the evidence digest into the signed acceptance report.
- Tests use a fake signature verifier and in-memory replay store only. No VM, provider, network, credentials, probes, filesystem collector, or untrusted code was used. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #76 merged (2026-11-24)

- Current `main` includes PR #76 squash merge `d393d2e5bb0a93390b8d572bf540ff9ec3f1fe7c`; final PR head: `87c19d15f714f4a21200d469ed828d4b83026861`.
- Final-head CI passed: Task Orchestrator Tests `45384423673` (355 tests), Non-production PR Validation `45384423800`, and Project Memory Audit `45384423642`.
- PR #76 adds `tools/task_orchestrator/sandbox_acceptance_provenance.py`, a separate schema-v2 signed acceptance verifier. Existing schema-v1 report verification remains unchanged.
- V2 pins expected runtime ID plus observer registry digest/version; requires a sorted signed observer-provenance inventory; recomputes provenance and raw probe-evidence digests; parses canonical evidence; derives required observer domains from the probe manifest; cross-checks observer ID/domain and exact payload SHA-256; rejects duplicate nonce/envelope/observer-sequence tuples, incomplete/extra provenance, stale/future evidence, invalid monotonic intervals, and non-Ed25519 algorithm labels.
- The report signature covers all v2 provenance records. The trusted acceptance-suite signer attests that observer envelopes were verified by the trusted host verifier. The v2 verifier does not independently re-verify observer signatures because raw signed envelope bytes are referenced by digest and must be retained separately for later re-verification.
- V2 requires protected expectations for exact runtime ID and observer registry digest/version. It does not create or sign reports, provision keys, run probes, or authorize execution.
- No report signer/private key, durable replay store, nonce generator, TLS transport, VM, provider, network, filesystem collector, or untrusted execution was used. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #78 merged (2026-11-24)

- Current `main` includes PR #78 squash merge `74a5b2b760362494711949b799031dc628612671`; final PR head: `156511739d82de7dac02adedb31aebc4e3ce4adb`.
- Final-head CI passed: Task Orchestrator Tests `45385761279`, Non-production PR Validation `45385761459`, and Project Memory Audit `45385761392`.
- PR #78 expands the `ObserverReplayStore.consume` contract to carry observer/domain, attempt/runtime/policy/probe, registry digest/version, key ID, nonce/envelope digests, sequence, challenge expiry, and trusted acceptance time. The verifier passes these fields only after signature, challenge, and payload validation.
- Challenge expiry is exact UTC-second precision; host acceptance timestamp preserves microseconds. The in-memory test fake rejects duplicate nonce/envelope digests and non-increasing per-observer sequence while retaining the audit context.
- Added `docs/SANDBOX_REPLAY_STORE_DESIGN.md`: serializable transaction/CAS sequence advancement, unique constraints, atomic audit, stable observer identity across key rotation, fencing, protected anti-rollback checkpoint, nonce/audit retention, failover, backup restore, failure modes, and implementation test matrix.
- No durable DB/service, persistence credentials, network endpoint, production replay store, KMS/HSM, VM, provider, or untrusted execution was created. Production replay persistence still requires separate trust-boundary review and explicit approval.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #80 merged (2026-11-24)

- Current `main` includes PR #80 squash merge `6666266f59877e9a066188d418938661075ae38e`; final PR head: `f41cee3685c3315ae3373f5c21f9fbaab9fa03dc`.
- Final-head CI passed: Task Orchestrator Tests `45386943800`, Non-production PR Validation `45386943924`, and Project Memory Audit `45386943682`.
- Added `docs/SANDBOX_OBSERVER_ENVELOPE_RETENTION.md`, a design-only two-phase raw-envelope retention contract. Phase A stages exact canonical signed-envelope bytes in a protected content-addressed host store and produces a deterministic staging manifest; the next acceptance schema must bind that manifest digest. Phase B packages the retained envelopes after report verification into a final artifact manifest bound to the report digest.
- Schema v2 remains unchanged: it binds envelope digests and payload provenance but does not include a pre-acceptance staging-manifest digest or raw envelope bytes.
- Design covers descriptor-relative no-follow storage, same-descriptor hashing, path derivation by trusted host, file/count/aggregate bounds, quarantine, retention, crash-safe cleanup, and independent offline re-verification.
- No filesystem collector, storage service, database, credential, network endpoint, report signer, private key, VM, provider, or untrusted execution was created. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Authoritative snapshot — PR #82 merged (2026-11-24)

- Current `main` includes PR #82 squash merge `d7ef7ed4266ea2606acd76f6e36fb4822af7d179`; final PR head: `d91ea3da44fc133e94621df4cae3dfd7dee174bf`.
- Final-head CI passed: Task Orchestrator Tests `45390283412`, Non-production PR Validation `45390283324`, and Project Memory Audit `45390283473`.
- Added `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md` and decision D-022. The design requires exact raw-envelope revalidation, Ed25519 signature verification, trusted read-only replay acceptance receipts, complete evidence/provenance checks, and a signed raw-envelope staging-manifest digest in schema v3.
- A caller-created `AuthenticatedObserverResult` is not a trust root. A future signer must match every result and exact raw envelope to the committed replay ledger receipt, including ledger revision/fencing epoch.
- Schema v1/v2 remain unchanged. Schema v3 is only a design target; no report builder, signer, verifier, key, signing service, replay database, or filesystem collector was added.
- No probe execution, VM/provider, network, credentials, production signing, release, deployment, or spend occurred. Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Active candidate branch snapshot — PR #88 (verified 2026-11-24)

- Current main base: `dcb9d1c01a50974d9ef38bdf5f0e4aaf744b409e` (PR #84 merge); do not confuse the active candidate branch with main.
- Active branch: `feat/host-csprng-challenge-issuer-20261124`; PR #88 is Draft/open/unmerged.
- Implementation checkpoint SHA: `566fbb58c4e039ef88abee64a987995b029ba534`. Verify the current PR head again before relying on this snapshot because documentation commits may advance it.
- PR #88 adds the schema-v3 deterministic report builder, independent pre-sign verifier, short-lived verifier authorization attestation, fail-closed report signer gate, post-sign verification path, integrated non-executing pipeline, and stronger CSPRNG challenge/key lifecycle contracts.
- Exact checkpoint checks passed: Task Orchestrator Tests run `45428730520` (401 tests), Non-production PR Validation `45428731306`, and Project Memory Audit `45428731849`. The latter generated semantic/resolved/critical-path indexes as temporary 30-day artifacts and verified task-intelligence against real indexed source.
- The green audit did not itself enforce freshness of all project-level memory documents. This PR updates the baseline; a future required check should make such updates enforceable.
- No production transport, KMS/HSM key, durable Replay Store, isolated signer deployment, external security approval, live probe, VM/provider, source transfer, or untrusted execution exists. All execution flags remain false.


## Multi-project architecture and registry update — 2026-11-25

- PR #97 was squash-merged as `914445b758d049ad5b97d670a66635f4cf8aba7b`. It adds the repository-neutral multi-project architecture, project manifest JSON Schema, and read-only onboarding specification.
- JET VPN is the first compatibility fixture, bound to immutable GitHub repository ID `1349356614`. The proposed project ID `jet-vpn-android` remains a candidate until a separately reviewed registry activation; documentation merge did not register or activate it.
- Phase 2A is tracked in Issue #98. Its scope is a pure standard-library manifest/schema/identity/uniqueness/lifecycle/runner validator and adversarial tests. Task-envelope, lease, context, workspace, cache, and artifact identity propagation are explicitly later phases.
- The checked-in schema is a deliberately constrained JSON Schema 2020-12 subset. The implementation must reject remote references and unknown schema keywords; do not describe a partial implementation as a full standards-compliant validator.
- Do not register «حسابگر من» or any other repository until the owner supplies its exact repository URL and live immutable repository identity is independently checked.
- Project manifests are declarative data, never executable instructions. Global safety policy remains stronger than project-specific configuration.


## Authoritative multi-project snapshot — 2026-11-25

- Current verified `main` includes Phase 2A PR #99 (merge base for Phase 2B: `9b54a7158a1fbba7405f04ad503bcb8126c457bc`) and Phase 2B PR #101, squash-merged as `a0046fd5d17c32293bef3f904adc2bda89cd48c5`.
- Phase 2B adds explicit v2 project identity to task intake and persisted handoffs, JET VPN-only v1 compatibility, base/head repository identity checks, and a separate PR authorization envelope v2. Final PR #101 head `028e5aea501abde1ceb2ff3d84d91aae9423d162` passed 426 orchestrator tests and all four required exact-head workflows.
- Phase 2C is tracked by Issue #102 on branch `agent/project-memory-manifest-context-20261125`; it is implementing manifest-selected project context and identity-bound context packages/envelopes. Keep legacy v1 limited to the fixed JET VPN six-document context.
- حسابگر من repository was supplied as `majidbusy09-blip/hesabgar_man`; GitHub repository ID `1423683236`, default branch `main`, primary language Dart. It has been inspected read-only only; no manifest registration, target-repository write, activation, or app-source change has occurred.
- No paid model API, provider spend, credentials, release/deployment, production changes, or untrusted-code execution is authorized.


## Phase 2D-1 active work — 2026-11-25

- Phase 2C PR #103 is merged as `c145412206f62be0f08349d1530646dfb5a776da`.
- Phase 2D-1 Issue #104 / branch `agent/project-scoped-lease-workspace-namespace-20261125` introduces a pure project namespace helper and project-bound lease schema v2. V2 lease refs and record paths derive from validated `project_id` + immutable numeric `repository_id`; the lease record binds the full project identity tuple. V2 workspace IDs include the project namespace, task ID, manifest digest, and pinned base SHA.
- Legacy v1 lease refs and `.agent-locks/lease.json` remain unchanged. Local task-record and artifact paths are deliberately deferred to Issue #106 (Phase 2D-2).
- حسابگر من remains read-only and inactive; onboarding plan is Issue #105.


### Phase 2D-1 lease consumer audit — 2026-11-25

The shared project namespace resolver must be used by every lease consumer, including the trusted PR guard and patch-review gate, not only by claim/renew/release and handoff code. V2 lease consumers must compare the complete project binding; v1 remains on its exact legacy ref and file path.


## حسابگر من onboarding task — 2026-11-25

- Issue #105 is now an active, leased control-plane onboarding task after Phase 2C PR #103 and Phase 2D-1 PR #107 were merged.
- The target is exactly `majidbusy09-blip/hesabgar_man`, immutable repository ID `1423683236`; candidate project ID is `hesabgar-man`.
- The target app baseline is `1.0.9+10`. Preserve it; do not bump the version as part of onboarding.
- Keep target repository changes in a separate PR. Do not activate the project; its manifest lifecycle remains `registered`.
- A dedicated target-repository Flutter analysis/test workflow is being validated. Do not claim a profile passed until the exact Actions run is successful.
- The existing JET VPN Dart index CLI and output names are project-specific. Do not point the hesabgar manifest at them; use `source_index.strategy=none` until a generic adapter is implemented and reviewed.
