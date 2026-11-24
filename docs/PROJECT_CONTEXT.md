# JET VPN — Project Context

> Current verified repository snapshot: `main` at `3e613a8c03a39e4440c3702ac3505acb7b2eae27` (2026-11-24).
> PR #20, PRs #38–#44, PR #46–#53 are merged.
> Main source blob: `lib/main.dart` = `3d28693b7be8bfe309a850923599830e1a65ab59`.
> App version: `2.4.5+284` (`pubspec.yaml` blob `adc3b22a4538db4738bec789e3c3badf26e4f710`).
> PR #47 Task Orchestrator Tests #45314331567 (247 tests), Project Memory Audit #45314331612, and non-production validation retry #45313415713 passed. PR #48 Task Orchestrator Tests, Project Memory Audit, and Non-production PR Validation #45314885244 all passed.
> Active `main-protection` ruleset requires PR + project-memory freshness check and allows Squash only.

## Product and repository identity

- App: **JET VPN**; related service/brand name: **JetConfig**.
- Telegram bot: [@JetConfig1bot](https://t.me/JetConfig1bot).
- Telegram information channel: [@jetconfig11](https://t.me/jetconfig11).
- In-app purchase is active; the bot remains an alternative purchase and management route. These are user/product context, not proof of backend implementation.
- This repository is the Flutter Android client. The inspected application-source tree contains `.github/workflows/build.yml`, `README.md`, `lib/main.dart`, `pubspec.yaml`, and `tools/v2ray_notif_patch/` with three Java files and one shell script.
- The current main tree contains tracked application tests under `test/` and developer tooling under `tools/project_memory/`. No backend PHP source, Telegram bot source, admin panel, worker, or JET VPN TV source is present in this repository. CI may generate Android scaffold files in its temporary workspace; those generated files are not tracked application source.

## Runtime summary

- Flutter/Dart app; `main()` initializes Flutter and runs `JetConfigApp`.
- `MainVpnScreen` is stateful and owns the bulk of UI, account, subscription, server, connection, recovery, update, and support logic in the large `lib/main.dart`.
- VPN engine dependency: `flutter_v2ray_client: 3.5.0`.
- Repository-maintained native patch sources are applied to the dependency during the build workflow.
- Server APIs observed by the client use `https://majid6064.ir/api.php`, plus `sos_api.php`, `app_version.json`, and `tunnel_bypass.json`.

## Product context versus source truth

Smart routing, direct/domestic app handling, account profiles, purchase/renewal, free tests, server ping, automatic recovery, and APK update are known product areas. Before changing any behavior, verify the implementation in the current source and update the relevant technical documents.

## Collaboration contract

The repository's `AGENTS.md` is the mandatory operating contract. Before prioritizing work, apply the collaborator-priority test stated there. The short version: load project memory and `docs/TASK_TEMPLATE.md` first, verify current source, work on isolated branches, record scope and evidence, show complete diffs, open PRs, and do not merge or release without explicit approval.

## Release workflow

The production workflow `.github/workflows/build.yml` is manual-only after merged PR #5: `workflow_dispatch`, selected ref `main`, and explicit `confirm_release=true` are required. Ordinary pushes and PR merges do not publish a Release. A confirmed manual run can publish signed APKs and a public GitHub Release; never trigger it without explicit approval.

## External source dependencies and unknowns

- The authoritative PHP/API implementation is not present in this repository. Request/response details in `API_CONTRACT.md` are client-observed only.
- JET VPN TV is a separate project/repository and is out of scope for this repository's architecture.
- Never assume that README descriptions of a wider JetConfig ecosystem mean those source files are included here.


## Sandbox evidence verifier

The task orchestrator includes a strict signed-evidence verifier for independent sandbox runtime acceptance reports. PR #51 additionally requires the exact raw evidence bundle for all 20 probes and recomputes every SHA-256 digest. Signature verification remains injected; the test double is not cryptographic security. The Bubblewrap self-check and host preflight inventory are limited diagnostics, not the external acceptance suite. Production pinned-key Ed25519 trust, independent VM/host probes, external canary, and real runtime validation remain outstanding. No execution authorization is possible.


## Sandbox signing trust-store policy — PR #53 merged

- PR #53 head `b0b5f72c1d8c7f0940b1c1cfb8cb5dacdb1cb11b` passed Task Orchestrator Tests #45334662136 (271 tests), Project Memory Audit #45334662120, Non-production PR Validation #45334662100, and Agent PR Lease and Scope Guard #45334659579; squash-merged as `3e613a8c03a39e4440c3702ac3505acb7b2eae27`.

- `tools/task_orchestrator/sandbox_trust.py` adds canonical trust-store parsing, duplicate-key rejection, independently pinned SHA-256 verification, caller-supplied minimum-version enforcement, unique key IDs, Ed25519 public-key shape validation, UTC validity windows, and active-only key selection.
- The caller-supplied digest and minimum version must come from protected out-of-band configuration. The module does not persist anti-rollback state.
- Signature mathematics remains an injected `Ed25519Backend`; the test backend is not cryptography. No production Ed25519 implementation, key generation, signing service, or private key is present.
- The trust-store policy adapter does not authorize execution. Independent runtime probes, protected deployment of trust configuration, audited crypto implementation, and real VM acceptance remain open.

## PR #55 — real Ed25519 verification backend merged (2026-11-24)

- Main includes PR #55 squash merge `3cc2e200dd02416d7b2fba02725b6734dffede39`; this supersedes the older PR #53 snapshot at the top of this document.
- PR #55 final head `56e48fac7e5cfdf25c07492daef9ed3cdd3c0805` passed Task Orchestrator Tests run `45354914545`, Project Memory Audit run `45354914553`, and Non-production PR Validation run `45354914620`.
- `tools/task_orchestrator/ed25519_backend.py` uses PyCA `cryptography` to verify Ed25519 signatures with a raw 32-byte public key and 64-byte signature. It is verification-only; no private-key loading, signing, or key generation is exposed.
- `tools/task_orchestrator/requirements-sandbox-crypto.txt` pins `cryptography==50.0.2`, `cffi==2.1.1`, and `pycparser==3.12`; both Python CI workflows install binary wheels. The pins are not hash-locked, so reproducible wheel hashes/provenance remain a follow-up.
- Tests include RFC 8032 vector 1, tampered/invalid signature cases, and trust-store verifier integration.
- This backend does not solve protected out-of-band trust-store pin/minimum-version delivery, persistent anti-rollback, key lifecycle automation, independent host/guest probe execution, or real VM isolation. No provider, API key, private-source transfer, sandbox spend, or untrusted execution was used.
- Execution remains disabled: `execution_authorized: false`, `eligible_for_untrusted_execution: false`.




## PR #57 — protected trust control-plane design merged (2026-11-24)

- PR #57 final head `d60cf18554f37b0387bc6c5738edefdd2f04f602` passed Task Orchestrator Tests `45358099449`, Project Memory Audit `45358099476`, and Non-production PR Validation `45358099550`.
- Squash merge: `e28e16ba9b4021d3974085639df4c461774e8eaf`.
- `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md` defines the intended protected host-side trust configuration boundary; D-013 records the design decision.
- This is architecture documentation, not an operational control plane. There is no provisioned root key, KMS/HSM, durable monotonic store, service, provider, or VM.
- Next safe implementation is a provider-neutral validator and monotonic-store protocol with fake-only deterministic unit tests. Production trust and durable anti-rollback remain unimplemented.
- Untrusted execution remains disabled: `execution_authorized: false`, `eligible_for_untrusted_execution: false`.


## Authoritative trust acceptance update — PR #59 (2026-11-24)

PR #59 merged as `1e332fcd8f13c5ccebb352c31b72bbf09a27a1bb`. It adds a reference implementation for provider-neutral trust configuration acceptance:

- Strict canonical schema-v1 signed envelope parsing with bounded input, duplicate-key/non-finite/nesting rejection.
- Explicit environment/deployment/provider/region audience, trusted UTC validity checks, maximum one-hour envelope lifetime, root key ID and Ed25519 signature shape.
- Injected root signature verifier; no production root key or verifier provisioning.
- Exact SHA-256 binding to trust-store bytes and validation through `PinnedTrustStoreVerifier`.
- Monotonic-store Protocol requiring atomic durable CAS and append-only audit in the same transaction; acceptance is returned only after successful commit.
- Deterministic fake root/backend and in-memory CAS tests only.

This is **not production-ready**: no durable monotonic-store implementation, transactional audit backend, root key ceremony, KMS/HSM, provider service, or runtime infrastructure exists. The protocol states the required contract; it does not prove a concrete backend meets it. Test doubles are not production trust.

PR #59 final head `177a4090effd838add36188578a5d7e8a7c671f5` passed Task Orchestrator Tests run `45361973408`, Project Memory Audit run `45361973336`, Non-production PR Validation run `45361973411`, and `validate-agent-pr` check `138334033651`.

The current execution policy is unchanged: `execution_authorized: false`; `eligible_for_untrusted_execution: false`. A passing acceptance test or signed evidence report is not execution authorization.


## Authoritative project context — PRs #67 and #68 (2026-11-24)

- PR #67 merge `b0b0b80515f17c01836f558ff5700189c9a7bf32` adds the exact machine-readable 20-probe runtime acceptance inventory, its non-executable specification, and tests. It also adds the tested CI path classifier: tooling-only changes skip unnecessary Flutter/APK steps while retaining Python safety validation; app/build-affecting changes still trigger full validation.
- PR #68 merge `90dd9f848998ebb0c18b6c584938fee148d6fced` adds a host-side evidence assembly contract. Final PR head `f76cdf060a2d7166639f6469bbcdf453d52b539b` passed Task Orchestrator Tests `45376199406`, Project Memory Audit `45376199527`, and Non-production PR Validation `45376199739`.
- The collector consumes typed host/guest/external-canary observations; requires exact manifest-defined trust domains; binds attempt, runtime ID and policy digest; validates monotonic offsets and UTC freshness; bounds payloads; rejects missing, duplicate and untrusted observations; and deterministically assembles per-probe evidence with host-side SHA-256 digests.
- It only checks observer IDs against caller-supplied allowlists. It does not authenticate identities cryptographically, provision trust roots, launch probes, start or inspect VMs/processes, open sockets, contact canaries/providers, collect artifacts, or sign reports.
- The 20 probes remain specified but not executed. No accepted untrusted-code runtime exists. GitHub-hosted Actions and benign Bubblewrap self-tests are not Sandbox acceptance evidence.
- The host-controller lifecycle, out-of-band observer trust, external canary channel, artifact collection and independent runtime threat-model review remain future work. No production infrastructure or paid service is authorized.
- Preserve `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Host lifecycle update — PR #70 (2026-11-24)

- PR #70 merged as `e699293c1495f3137dd319e37764a2db6c5dfff3`; final head `a4b79467d850663ae10f8ffebb8e544f9ecf199e`.
- It adds a pure state machine for future host-controller lifecycle events: runtime readiness, observation, evidence accepted/rejected, termination request, runtime termination, and cleanup.
- Events are bound to attempt/runtime/policy and monotonic deadline. Illegal ordering, stale identity, arbitrary event names, and malformed failure codes are rejected.
- Both passing and rejected evidence paths require termination and cleanup confirmation; cleanup failure is terminal.
- It invokes no adapter and has no OS/process/network/VM/provider capabilities. It cannot prove that an external runtime actually stopped or was cleaned up.
- Final-head checks passed: Task Orchestrator Tests `45377376254`, Non-production PR Validation `45377376173`, Project Memory Audit `45377376300`.
- Runtime execution remains disabled; no probes, provider, VM, API key, private-source transfer or spend was used.


## Artifact inventory update — PR #72 (2026-11-24)

- Current main includes PR #72 squash merge `a199b82ef70f492c2b8df42087992a917d293c7c`; final PR head `26edb96019e3816e4e23cff24b957f2d0187ca12`.
- The artifact inventory validator accepts bounded typed candidate records and exact in-memory byte strings only. It enforces logical path allowlisting, traversal rejection, declared regular-file/symlink/single-link constraints, duplicate rejection, count and byte ceilings, bounded retention metadata, host-side digest recomputation over supplied bytes, and deterministic canonical manifest serialization.
- Manifest metadata binds attempt, runtime, policy digest, evidence digest, signed acceptance-report digest, retention, and each artifact's path/size/SHA-256.
- The candidate object-kind and link-count fields are untrusted assertions. This implementation cannot inspect inodes, prove filesystem identity, authenticate report signatures, enforce retention, or prove artifact provenance. The future host collector must use descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, and TOCTOU defenses.
- Exact final-head CI passed: Task Orchestrator Tests `45379646169`, Non-production PR Validation `45379646094`, Project Memory Audit `45379646100`.
- No application behavior, app version, production release, provider, VM, network, private source transfer, credentials, KMS/HSM, spend, or untrusted execution changed or was enabled.
- The next focus is out-of-band observer authenticity, signed-report/manifest integration, fixed fake-only host-adapter interfaces, and the threat model for trusted filesystem collection.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Observer authenticity update — PR #74 (2026-11-24)

- Current main includes PR #74 squash merge `b40642e9cb58446b60cc356f349656c31818d898`; final PR head `f633295b6c5ceb64eef183340d1fe5162b5edf59`.
- `sandbox_observer_auth.py` validates canonical signed observer envelopes against an externally pinned registry digest/version/audience; checks unique observer identity, trust domain, key ID, active status and validity; binds a one-time 32-byte host nonce challenge to audience, observer, attempt, runtime, policy and exact probe ID; verifies canonical Ed25519 signatures through an injected verifier; and enforces payload digest/size, timestamp freshness, monotonic offsets and strictly increasing per-observer sequence via an injected atomic replay-store protocol.
- Successful verification returns `AuthenticatedObserverResult`, containing the existing `ProbeObservation` plus registry digest/version, key ID, sequence, nonce digest and exact envelope digest.
- The current `CollectedEvidenceBundle` does not yet retain the wrapper provenance. The signed acceptance report must later bind those provenance fields and the assembled evidence digest.
- Only deterministic fake signature and in-memory replay-store implementations were tested. No production observer keys, registry provisioning, CSPRNG challenge generator, authenticated network transport, durable replay store, VM, runtime probe, or untrusted execution was used.
- Exact final-head CI passed: Task Orchestrator Tests `45382515116`, Non-production PR Validation `45382515212`, Project Memory Audit `45382515188`.
- Next focus: signed-report provenance integration, durable replay-store design, host challenge/transport design, and protected identity rotation/revocation.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Signed acceptance provenance update — PR #76 (2026-11-24)

- Current main includes PR #76 squash merge `d393d2e5bb0a93390b8d572bf540ff9ec3f1fe7c`; final PR head `87c19d15f714f4a21200d469ed828d4b83026861`.
- Added a separate schema-v2 verifier that pins expected runtime ID and observer registry digest/version; validates the signed provenance digest and sorted record inventory; derives required probe observer domains from the manifest; recomputes raw evidence and payload digests; and cross-checks observer ID/domain and payload digest against exact evidence bytes.
- Provenance records bind probe, observer domain/ID, signing key ID, registry digest/version, sequence, nonce digest, envelope digest, payload digest, and Ed25519 algorithm label.
- Schema v1 remains unchanged. V2 signature attests that the trusted acceptance-suite signer received already-verified observer envelopes; the verifier does not independently re-check observer signatures because raw envelope bytes are not embedded. Retain those raw bytes separately if independent re-verification is required.
- V2 does not sign reports or provision keys; no private key, durable replay store, nonce generator, TLS transport, VM, provider, network, filesystem collector, or untrusted execution was used.
- Exact final-head CI passed: Task Orchestrator Tests `45384423673` (355 tests), Non-production PR Validation `45384423800`, Project Memory Audit `45384423642`.
- Next focus: durable replay-store design, protected raw-envelope retention, trusted report-signer contract, and host challenge/transport design.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Durable observer replay-store update — PR #78 (2026-11-24)

- Current main includes PR #78 squash merge `74a5b2b760362494711949b799031dc628612671`; final PR head `156511739d82de7dac02adedb31aebc4e3ce4adb`.
- The replay-store protocol now receives complete context: observer/domain, attempt/runtime/policy/probe, registry digest/version, key ID, nonce/envelope digests, sequence, challenge expiry, and trusted acceptance time.
- The verifier supplies these fields only after successful challenge, identity, signature, payload, time, and monotonic checks. Challenge expiry uses exact UTC-second precision; acceptance time preserves microseconds.
- In-memory fake rejects duplicate nonce/envelope digests and non-increasing per-observer sequence, and retains audit context. It is test-only; no durable DB/service exists.
- `docs/SANDBOX_REPLAY_STORE_DESIGN.md` specifies serializable transaction, uniqueness, CAS sequence advance, atomic audit, stable observer identity across key rotation, fencing, external anti-rollback checkpoint, retention, failover, and recovery.
- Exact final-head CI passed: Task Orchestrator Tests `45385761279`, Non-production PR Validation `45385761459`, Project Memory Audit `45385761392`.
- Next focus: protected raw-envelope retention, trusted report-signer contract, host challenge/transport, and protected identity lifecycle.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Protected observer-envelope retention update — PR #80 (2026-11-24)

- Current main includes PR #80 squash merge `6666266f59877e9a066188d418938661075ae38e`; final PR head `f41cee3685c3315ae3373f5c21f9fbaab9fa03dc`.
- Added `docs/SANDBOX_OBSERVER_ENVELOPE_RETENTION.md` defining exact-byte pre-acceptance staging in a host-only content-addressed store, a deterministic manifest, next-schema binding of that manifest digest, and post-acceptance artifact packaging bound to the verified report digest.
- The design requires host-derived content-addressed paths, no-follow descriptor-relative storage, hashing from the same descriptor, bounded count/size, quarantine on uncertain acceptance, crash-safe cleanup, retention, and independent offline re-verification.
- Schema v2 remains unchanged; it binds envelope digests/provenance but not the pre-acceptance staging-manifest digest and does not include raw envelope bytes.
- No filesystem collector, storage backend, DB/service, credentials, report signer, private key, network, VM, provider, or untrusted execution was created.
- Exact final-head CI passed: Task Orchestrator Tests `45386943800`, Non-production PR Validation `45386943924`, Project Memory Audit `45386943682`.
- Next focus: trusted report-signer contract, host challenge/transport, protected identity lifecycle, and separately reviewed filesystem staging.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.


## Trusted acceptance report signer update — PR #82 (2026-11-24)

- Current main includes PR #82 squash merge `d7ef7ed4266ea2606acd76f6e36fb4822af7d179`; final PR head `d91ea3da44fc133e94621df4cae3dfd7dee174bf`.
- Added `docs/SANDBOX_TRUSTED_REPORT_SIGNER.md` and decision D-022.
- Future signer must not treat a caller-created `AuthenticatedObserverResult` as proof. It must independently verify exact raw observer envelope bytes and Ed25519 signatures, then match every result to a trusted read-only replay acceptance receipt with committed ledger revision/fencing epoch.
- Schema v3 should bind the pre-acceptance envelope staging-manifest digest. Existing v1/v2 verifiers remain unchanged.
- Signer output must be independently verified before acceptance. All test signing/replay components remain deterministic fakes.
- No report builder/signer, schema-v3 verifier, private key, signing service, durable replay database, filesystem collector, network, VM, provider, probe execution or untrusted execution exists.
- Exact final-head CI passed: Task Orchestrator Tests `45390283412`, Non-production PR Validation `45390283324`, Project Memory Audit `45390283473`.
- Next focus: replay receipt read contract, pure schema-v3 builder, injected fake signer/verifier, then schema-v3 independent verifier.
- Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`.
