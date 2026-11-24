# JET VPN Task Orchestrator — Local MVP

This standard-library-only Python tool records a task lifecycle and enforces a small set of safety gates. It is an evidence recorder and workflow guard, not an autonomous coding agent.

## Next phase: coding-agent adapter

The provider-neutral design contract is documented in [`docs/CODING_AGENT_ADAPTER_CONTRACT.md`](../../docs/CODING_AGENT_ADAPTER_CONTRACT.md). It specifies the future task/result envelope, isolated patch workflow, permission boundary, and validation gates. It is design only: this MVP does not connect a model provider or execute agent-generated patches.

## Requirements

- Python 3.10 or newer (CI currently uses Python 3.12).
- Git.
- Run commands from inside a clean working tree on a dedicated non-main branch.

## Lifecycle

```sh
python tools/task_orchestrator/task_orchestrator.py init \
  --task-id smart-routing-audit \
  --goal "Trace and verify Smart Routing behavior" \
  --capability "source analysis and verification" \
  --risk medium \
  --allow "lib/**" \
  --allow "test/**" \
  --exclude "lib/generated/**" \
  --check python-tooling-tests \
  --check flutter-analysis \
  --check flutter-tests

python tools/task_orchestrator/task_orchestrator.py prepare --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py suggest-context --task-id smart-routing-audit --query "Smart Routing domestic apps and VPN tunnel" --resolved-index /path/to/jet_vpn_resolved_index.json --critical-paths /path/to/jet_vpn_critical_paths.json
python tools/task_orchestrator/task_orchestrator.py accept-context --task-id smart-routing-audit --suggestions .agent/tasks/smart-routing-audit/context_suggestions_HASH.json --path lib/main.dart
python tools/task_orchestrator/task_orchestrator.py build-envelope --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py impact --task-id smart-routing-audit --resolved-index docs/generated/jet_vpn_resolved_index.json --critical-paths docs/generated/jet_vpn_critical_paths.json
python tools/task_orchestrator/task_orchestrator.py begin --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py validate-scope --task-id smart-routing-audit
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile python-tooling-tests
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile flutter-analysis
python tools/task_orchestrator/task_orchestrator.py verify --task-id smart-routing-audit --profile flutter-tests
python tools/task_orchestrator/task_orchestrator.py validate-scope --task-id smart-routing-audit
# Review the complete tracked, staged, and untracked diff yourself before confirming:
python tools/task_orchestrator/task_orchestrator.py finalize --task-id smart-routing-audit --reviewed-diff
```

The example is illustrative: choose only checks appropriate to the actual task. A check is not successful until its fixed command has actually run and returned zero.

## Commands

- `init`: requires an initially clean worktree and explicit allowed paths and named checks. Repository-wide patterns (`*`, `**`, `**/*`) require `--risk high` and `--scope-reason`.
- `prepare`: rejects main/master/the detected `origin/HEAD` default branch, detached HEAD, pre-existing changes, and changed repository origin; pins the base SHA and working branch, then builds context from that exact Git revision. Required project documents are automatic; source files are explicitly selected with repeatable `--context REPO_PATH` options at `init`. Each selected source file must match the task allowlist and avoid exclusions.
- `build-envelope`: re-verifies the complete context package against task ID and pinned base SHA, validates every document hash and scope, then writes a deterministic v1.1 `agent_input.json` under the task's local `.agent/tasks/<task-id>/` directory. Existing different output is never overwritten.
- `impact`: calculates the task's complete changed-path set from its pinned base, then maps indexed Dart changes to resolved declarations, call sites, and curated critical paths. It verifies that the resolved index and critical-path report share the same source manifest and checks each changed indexed file's Git blob against the pinned base. It writes `.agent/tasks/<task-id>/impact_report.json`, records report provenance in `task.json`, flags out-of-scope paths, and labels files absent from the index as unknown. Pass `--resolved-index` and `--critical-paths` when the generated artifacts are stored elsewhere. Suggested verification profiles are advisory; the task's declared checks remain authoritative. Static analysis cannot prove runtime impact.
- `suggest-context`: ranks source files from the analyzer-resolved index and curated critical-path report. It verifies that both reports describe the same file manifest and that every indexed Dart file's Git blob SHA matches the task's pinned base commit. It suggests only files inside the task allowlist and outside exclusions. The deterministic ranking uses request terms, paths, resolved declaration/call names, and matched curated critical paths. It writes a local advisory artifact; it never changes `context_paths`, expands scope, or builds an agent envelope.
- `accept-context`: accepts only paths explicitly selected with repeatable `--path` arguments from a task-local suggestion artifact. It rechecks the suggestion's task/base identity, the selected Git blob SHA, and the existing task scope, then rebuilds the full-text context package from the pinned commit. It is allowed only while the task is prepared and before an agent envelope exists. It cannot widen the allowlist or silently accept all suggestions.
- `begin`: verifies that the pinned base has not moved before entering implementation.
- `validate-scope`: compares committed, staged, unstaged, renamed, deleted, and untracked paths with the declared allow/exclude patterns.
- `verify`: runs only fixed profiles declared at init; no shell command can be supplied by task text. The child process receives a restricted environment allowlist so arbitrary local API tokens are not forwarded. It fingerprints the changed source paths immediately before and after each check; if the path set or content changes while the check is running, that attempt is marked failed and cannot satisfy finalization.
- `finalize`: requires passing scope validation, latest attempt for every planned check must be passing (an earlier pass cannot override a later failure), and explicit human confirmation that the complete diff was reviewed. It writes a Markdown handoff.

Task records and handoffs are stored under `.agent/tasks/<task-id>/`. The task record includes a bounded full-text context package (256 KB per file, 512 KB combined), package SHA-256, and pinned source revision. It contains no environment variables, credentials, or raw command output.

## Deterministic Context Builder

- `context_builder.py` reads required project documents and explicitly selected source files from the pinned Git commit, never from mutable working-tree contents.
- Source selection is explicit via repeatable `--context`; this avoids copying the entire repository into the agent context by default.
- Rejects path traversal, protected paths, missing or untracked paths, symlinks, submodules, non-UTF-8/binary content, and size overflow. It never silently truncates.
- Produces reproducible full-text documents with per-file SHA-256 and a canonical package SHA-256. The package is persisted in the task record. `build-envelope` converts it into the exact v1.1 contract (Git base IDs accept SHA-1/SHA-256 object-ID lengths; content hashes remain SHA-256; this distinction is covered by adversarial tests; the integration fixture also checks exact UTF-8 source text) only after recomputing the package digest, checking task/base identity, document hashes, byte totals, and source-path scope.
- Repository text is untrusted data and cannot override the agent's safety or permission boundaries.
- Local-only and provider-neutral: `agent_input.json` duplicates bounded source text under the ignored local task-metadata directory; the repository now ignores `.agent/tasks/` by default, and it is not sent to a provider. Do not force-add these source-bearing local artifacts; the ignore rule is a convenience guard, not a security boundary. No model call, API key, or sandbox is involved.


The integration suite uses temporary Git repositories and covers lifecycle, scope, branch/base pinning, rename/delete handling, symlink safety, timeouts, source mutation during verification, stale results, and retry ordering. A later failed attempt blocks finalization even if an earlier attempt passed. The generated agent envelope is an additional local-only task artifact and is never committed or uploaded.

## Coding-agent contract validation (provider-neutral)

- `agent_contract.py` validates task envelopes and structured results against contract version `1.1`; it is data validation only and does not connect a provider, execute commands, fetch artifacts, or apply patches.
- Rejects unknown/missing fields, duplicate JSON keys, malformed/oversized JSON, invalid enums/types, unsafe or protected paths, out-of-scope/excluded changes, unknown verification profiles, arbitrary URL/shell patch references, invalid budgets/usage, and stale or mismatched context fingerprints, missing context text, content/hash mismatches, and per-file/total context-size limits.
- Patch references are opaque `artifact:sha256:<64-hex>` identifiers only. The artifact itself still requires independent patch parsing and acceptance gates before any future application.
- Agent status and assertions are not verification evidence. Non-completed statuses cannot carry a patch; only the orchestrator may later record actual check outcomes or advance task state.
- Run the fixture suite with `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py'`.

## Read-only adapter prototype

- `readonly_adapter.py` defines a minimal provider protocol: a provider receives only a deeply immutable, validated task envelope and returns structured data that is validated against the same task contract.
- Project and source context are passed as bounded full-text documents, not just hashes; each document's SHA-256 is checked before the provider is called. The result echoes only path/hash fingerprints.
- A deterministic fixture provider supports local tests. No model SDK, API key, network client, shell, Git, filesystem handle, patch fetcher, or patch applier is included.
- The boundary rejects invalid envelopes before calling the provider and rejects malformed or contract-invalid provider output. Provider exception text is not copied into diagnostics.
- Important limitation: this Python interface is not an OS-level sandbox. It only constrains the capabilities passed through this interface; any real provider implementation must be separately trusted, permission-limited, and reviewed. No live provider is connected.
- Run all orchestrator tests with `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py'`.

## Fixed verification profiles

- `python-tooling-tests`
- `flutter-tests`
- `flutter-analysis`
- `lexical-memory-audit`

Profiles use fixed argument vectors, bounded timeouts, `shell=False`, and a restricted environment allowlist. A missing executable, OS execution error, timeout, or source mutation during a check is recorded as failure. Repeated attempts append to the record; an earlier failure is not erased.

## Explicit non-goals

This MVP cannot create commits, push branches, call GitHub write APIs, open or merge PRs, create tags, publish releases, deploy, or dispatch the production workflow. It does not infer runtime/device success from static analysis, tests, or builds. Human review and explicit user approval remain mandatory for merge/release/deployment.


## Continuous integration

Changes to this orchestrator, its tests, or the adapter contract run `.github/workflows/task-orchestrator.yml`, which compiles the Python modules and executes the complete standard-library test suite on Python 3.12.

Envelope provenance is checked against the pinned Git blobs immediately before serialization; a matching package hash alone is not treated as proof of source authenticity; the CLI also re-reads the pinned Git objects; fixture coverage uses the full six-document project-memory set.


## Verified Impact Analyzer

- Run `impact` after preparing the task and before implementation to establish a baseline; run it again after edits to refresh the report.
- Example: `python tools/task_orchestrator/task_orchestrator.py impact --task-id smart-routing-audit --resolved-index docs/generated/jet_vpn_resolved_index.json --critical-paths docs/generated/jet_vpn_critical_paths.json`.
- The report is stored at `.agent/tasks/<task-id>/impact_report.json`; the task record stores its digest, source revision, changed paths, impacted critical-path IDs, recommended profiles, and risk flags.
- A task with no changed paths is reported as not applicable without requiring semantic artifacts. When changed paths exist, both semantic artifacts must be available, valid, and from the same source manifest; changed indexed files are checked against the pinned Git blob.
- Files missing from the index are explicitly marked unknown. Out-of-scope changes and critical-path reachability are surfaced as risk flags. The analyzer does not silently widen scope or execute suggested tests.
- The suggested profiles are advisory. Only the profiles declared in the task plan are required for finalization.

## Semantic Context Selector

- The selector reuses the existing analyzer-resolved index and curated critical-path report; it does not introduce another Dart parser or call graph.
- Obtain `jet_vpn_resolved_index.json` and `jet_vpn_critical_paths.json` from the successful Project Memory Audit artifact generated for the exact commit pinned by the task. The selector independently verifies every indexed source blob against that commit; stale or mixed-snapshot artifacts are rejected.
- Run `suggest-context` with a plain-language request. The query is treated strictly as search data, never as a command or instruction.
- The ranking is deterministic and explainable: matching file paths, resolved declaration names, call-site target names, and matching curated critical paths contribute weighted scores. Results are bounded to 25 and filtered through the task's existing allowlist and exclusions.
- Output is saved under `.agent/tasks/<task-id>/context_suggestions_<query-hash>.json`. It contains source blob fingerprints, artifact hashes, matched terms, ranking reasons, and explicit limitations.
- This is a candidate generator, not semantic proof. Dynamic dispatch, UI state dependencies, callbacks, event wiring, generated code, native Java, and runtime behavior can be missed. A human or higher-level planner must explicitly choose which paths become task context using `accept-context --path`. The selector does not silently widen a task. The acceptance command is a local metadata-only operation, restricted to the prepared state, and re-verifies selected source blobs and task scope before changing the context package. The selector's Python tests run in the dedicated Task Orchestrator CI workflow, including exact NUL-delimited Git-tree provenance checks, including the metadata tab separator and Unicode token normalization and common-language stop-word filtering.


Context-selection integration tests verify explicit acceptance, rejection of paths not present in the suggestion artifact, and rejection of stale Git-blob fingerprints and unsafe source paths. The accepted context package is rebuilt from the pinned commit; the allowlist is never modified.


## Limited OpenAI planning adapter (opt-in; no source upload)

- `openai_planner.py` uses the OpenAI Responses API through Python's standard library; importing it performs no network request and installs no SDK.
- It is a planning-only adapter. The request contains only the task ID, user goal, capability description, risk, allow/exclude path patterns, scope reason, and declared verification-profile names.
- It deliberately excludes repository identity, branch/base identifiers, project-memory documents, source files, context packages, semantic indexes, Git history, credentials, and prior conversation content. No source code is uploaded.
- No tools are declared or enabled. The model cannot access the filesystem, shell, Git, GitHub, secrets, or patch application through this adapter. Its output is a bounded JSON plan, not an implementation patch or verification evidence.
- It requires `OPENAI_API_KEY` and `OPENAI_MODEL` in the environment. Set `OPENAI_MODEL` to a model enabled for the API project; the adapter intentionally does not guess a model entitlement. Neither setting is stored in the repository or task record. The API endpoint is fixed to OpenAI over HTTPS; the adapter does not accept a custom base URL. Standard Python HTTPS proxy environment settings may still affect network routing. A missing setting fails before any request.
- This command is explicitly opt-in and may incur API usage charges when invoked: `python -m tools.task_orchestrator.openai_planner --task-id <task-id>`. Do not run it until the owner has separately configured an API key and approved the intended request. No key is present in CI and CI tests use a fake transport only.
- Responses are size-bounded, schema-validated (including requiring at least one planning step), and errors are sanitized. There are no automatic retries. This does not yet connect the planner to the orchestrator lifecycle or authorize sending source context.


## GitHub task ownership leases (v1)

The shared Issue protocol now has a deterministic lease record/state machine in `github_lease.py`, with adversarial tests. See `docs/GITHUB_TASK_LEASES.md` for the Git-ref compare-and-swap acquisition, renewal, release, expiry, and failure rules. The local helper validates and plans transitions only; it does not call GitHub or prove ownership. A connected GitHub adapter must execute create-ref and update-ref with an exact expected head SHA. Until that adapter is implemented and concurrency-tested, do not enable unattended parallel implementation.

## Shared GitHub multi-agent task inbox (v1)

GitHub Issues can carry provider-neutral commands for ChatGPT, Grok, and future connected agents. Create an Issue using `.github/ISSUE_TEMPLATE/agent-task.md`; the marked JSON payload is validated by `github_task_protocol.py`:

```bash
python -m tools.task_orchestrator.github_task_protocol --body-file issue-body.md
```

The validator is local-only: it performs no GitHub API call, model request, shell execution, or patch application. It enforces a strict schema, supported agent/capability/risk values, fixed verification profiles, bounded text, and protected-path rules. See `docs/MULTI_AGENT_GITHUB_PROTOCOL.md`.

Important: Issue comments are not an atomic lock. Acquire a lease with `github_lease_git.py` before editing; until provider runtimes and automatic dispatch are connected, keep one active implementation agent per task. Other agents may perform read-only review. This protocol does not imply that each GitHub App has the same write, shell, or Actions permissions.

## GitHub Issue intake bridge

Add the `agent-task` label to an open Issue containing the v1 marker and JSON payload. The `.github/workflows/agent-task-intake.yml` workflow validates the GitHub event with `github_issue_intake.py` and uploads a bounded JSON artifact for retrieval. The artifact binds the parsed task to the Issue URL, repository, issue number, and body digest.

This is an intake/validation bridge only. It does not create a local task branch, claim a lease, invoke ChatGPT/Grok, call a model API, run implementation commands, apply patches, or upload source files. A validated artifact is marked `validated-awaiting-claim`; an agent must separately verify assignment, acquire a proven lease through a trusted CAS adapter, and prepare its isolated task workspace. Invalid or closed Issues fail closed.


### Atomic GitHub task leases

Use \`github_lease_git.py\` to claim, renew, or release a task's shared lock branch using Git server-side \`--force-with-lease\` compare-and-swap. It requires a checkout, Git, \`GITHUB_REPOSITORY\`, and a short-lived \`GITHUB_TOKEN\`/ \`GH_TOKEN\` with \`contents: write\`. The token is not stored in the repository or task artifact.

\`\`\`bash
python -m tools.task_orchestrator.github_lease_git claim \\
  --task-id sample-task --owner chatgpt --claim-id 0123456789abcdef \\
  --base-sha <full-pinned-git-sha> --minutes 60
\`\`\`

Renewal requires the same base SHA, the previous active claim ID, and a fresh new claim ID; release requires the current claim ID. The adapter fails closed on malformed state, stale refs, failed CAS, or an unverified final ref. CI tests Git plumbing and stale compare-and-swap rejection against a local bare Git remote. The trusted-main live GitHub CAS probe passed (Actions run `45176916962`): exactly one of two concurrent writers won, the final ref was verified, and the temporary ref was deleted. The adapter is not yet connected to automatic provider dispatch. See \`docs/GITHUB_TASK_LEASES.md\`.


### Issue-comment lease controls

On an open Issue with the \`agent-task\` label and a valid v1 task payload, a repository owner/member/collaborator can operate its shared lease with a comment:

\`\`\`text
/jet-agent claim chatgpt <claim-id> [minutes]
/jet-agent renew chatgpt <previous-claim-id> <new-claim-id> [minutes]
/jet-agent release chatgpt <claim-id>
\`\`\`

Use \`grok\` instead of \`chatgpt\` for the other agent. Claim IDs are 16-64 lowercase hexadecimal characters; lease duration defaults to 60 minutes and is capped at 240. The workflow verifies the task assignment, uses the trusted default-branch code and short-lived GitHub token, and posts the verified lock ref/base SHA back to the Issue. A claim pins the current \`main\` commit; renewal reads and preserves that original base. Issue text is parsed as data and never run as shell input.

This is a manual lease-control bridge, not an agent wake-up mechanism. It does not invoke ChatGPT/Grok or start implementation. The provider runtime must still be active and independently verify the returned lease before editing.


The live Issue command workflow was end-to-end tested on temporary Issue #24: claim, renew, and release succeeded, the final lease record was verified as released, and the test Issue was closed. Evidence: Actions runs 45178623063, 45178678823, 45178732222.


### Agent implementation PR envelope

Include the following after the PR description when submitting a leased task:

    <!-- jet-agent-pr:v1 -->
    ```json
    {"schema_version":1,"task_issue":42,"owner":"chatgpt","claim_id":"<current-claim-id>"}
    ```

The trusted-main PR guard validates the linked Issue, lease, pinned base, and changed paths using read-only API access. It does not execute PR code or merge the PR.


## Accept a lease-verified GitHub task handoff

Successful claim/renew workflows now automatically prepare and upload a `jet-agent-input-*.zip` artifact. For manual recovery or a separate local clone, download the `jet-agent-handoff-*.zip` artifact and run:

```sh
GITHUB_REPOSITORY=owner/repository GITHUB_TOKEN="$GITHUB_TOKEN" \
  python -m tools.task_orchestrator.github_task_handoff_accept \
  --handoff-file /path/to/jet-agent-handoff.zip --create-branch
```

The acceptance command rechecks the live Issue and lock ref through read-only GitHub APIs, verifies the body digest and active claim/expiry, checks that the local origin and HEAD match the repository and pinned base, and requires a clean worktree on a non-default branch. It then creates the local task record and contract v1.1 `agent_input.json` with the six required project-memory documents. The downloaded ZIP is read without extracting its contents to disk.

This prepares a local agent envelope; it does not invoke ChatGPT/Grok, execute agent code, upload source, create/push branches, modify the lease, or apply patches. Source context remains empty until an agent explicitly selects in-scope files through the existing context-selection workflow.


If the lease is renewed after the local task has already been accepted, download the newest artifact and rerun the same command with `--refresh-existing`. This updates only the verified lease metadata in the local task record; it does not rebuild the envelope or touch implementation files. Refresh is allowed only for the same Issue body, task definition, owner, pinned base SHA, and exact previous claim ID from the renewal command.


## Provider-neutral sandbox lifecycle contract (synthetic-only)

- `sandbox_contract.py` defines a narrow provider protocol, immutable request/limit records, capability checks, runtime snapshot checks, a fail-closed lifecycle state machine, bounded artifact validation, and mandatory termination/destruction confirmation.
- The only supported operation is the fixed `synthetic-acceptance-v1` payload. The interface exposes no arbitrary shell command, source upload, credential injection, GitHub token, or model output execution.
- A successful result means only `synthetic_acceptance_passed`; it always reports `eligible_for_untrusted_execution: false` and `patch_applied: false`.
- Provider capability declarations are not proof. A real adapter must be independently reviewed and pass the runtime acceptance requirements in `docs/ISOLATED_WORKER_ARCHITECTURE_DECISION.md` before any untrusted code can be considered.
- The lifecycle fails closed for shared-kernel containers, missing VM/kernel/image/egress/resource/termination/destruction capabilities, open egress, credentials in the guest, mismatched image digest, timeout, invalid/oversized artifacts, or unconfirmed cleanup.
- Tests use an in-memory fake provider only; no real provider, sandbox, process, source upload, network call, account, or spend is involved.

Run the focused tests:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_sandbox_contract.py'
```


## Independent sandbox runtime acceptance evidence

- `sandbox_acceptance.py` validates a strict, canonical, bounded, signed report from a separately trusted runtime-acceptance suite.
- It pins the suite ID/version, signing key ID, provider, region, task, attempt, image digest, policy digest, UTC time window, and exact 20-probe inventory.
- Required probes cover VM/kernel separation, non-root/capabilities, Seccomp, cgroup CPU/memory/PID, disk quota, read-only source, secrets/sockets/devices, metadata, IPv4/IPv6, DNS, QUIC, external canary, timeout, process-tree kill, artifact integrity, cleanup failure paths, and fresh-attempt residue.
- Duplicate JSON keys, unknown/missing probes, stale/future reports, identity mismatches, non-canonical bytes, oversized evidence, and invalid signatures fail closed.
- The signature verifier is injected. Production must supply an audited asymmetric verifier (for example Ed25519) backed by an out-of-band pinned public key. The unit-test verifier is a test double only.
- This is an evidence verifier, not the probe runner, VM provisioner, attestation service, or execution authorization. A passing report always has `execution_authorized: false` and `eligible_for_untrusted_execution: false`.
- No real provider, sandbox, network probe, signing key, private source, API key, or spend is involved.

Run the focused verifier tests:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_sandbox_acceptance.py'
```

Full suite:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py' -v
```


## Production Ed25519 verification backend

- `ed25519_backend.py` implements the `Ed25519Backend` protocol using PyCA `cryptography` and exposes public-key verification only. It rejects non-byte inputs, public keys not exactly 32 bytes, and signatures not exactly 64 bytes; invalid signatures return `False`.
- The canonical dependency versions are listed in `requirements-sandbox-crypto.txt`. Both current Python 3.12 CPython `ubuntu-latest` x86_64 CI workflows install the platform-specific `requirements-sandbox-crypto-linux-x86_64-py312.lock` with `pip --require-hashes --only-binary=:all:`. It pins the exact cryptography, cffi, and pycparser wheel artifacts. The lock provides artifact integrity, not publisher provenance: PyPI reports provenance for cryptography 50.0.2, but not for cffi 2.1.1 or pycparser 3.12. See the supply-chain findings recorded in [PR #62](https://github.com/majidbusy09-blip/jetconfig-vpn/pull/62).
- The tests include RFC 8032 test vector 1 and an end-to-end `PinnedTrustStoreVerifier` check with a test-only RFC seed. No private-key operation is exposed by the production adapter.
- This provides actual Ed25519 signature verification for a supplied trust store; it does not establish protected external pin delivery, persistent anti-rollback, key rotation/revocation operations, independent VM evidence, or execution authorization.
- Run `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_*.py' -v`.


### CI evidence requirement for cryptographic verifier changes

A pull request that changes the trust-store verifier or its cryptographic backend is not validated by the memory audit or PR-scope guard alone. Require an actual successful run of both `JET VPN - Task Orchestrator Tests` and `JET VPN - Non-production PR Validation` on the exact final PR head. A missing, skipped, or job-less workflow run is not a passing test result. Do not merge until both test workflows have completed successfully for the current head SHA.

## Protected trust control plane — design contract

See `docs/PROTECTED_TRUST_CONTROL_PLANE_DESIGN.md`. The design specifies a root-authenticated configuration envelope, exact audience and expiry checks, independently pinned trust-store digest, monotonic epoch/version floors backed by a transactional compare-and-swap store, key rotation/revocation, append-only audit, and fail-closed recovery.

This is design only. No service, KMS/HSM, root key, durable monotonic store, or provider integration exists. Any future local/in-memory store in tests is a fake and must never be described as production anti-rollback. The next implementation phase may add a provider-neutral validator/protocol, but production acceptance remains blocked until the actual protected infrastructure is separately selected, provisioned, and independently reviewed.


## Trust configuration acceptance (reference-only; PR #59)

`trust_config_acceptance.py` provides provider-neutral validation for a schema-v1 signed trust-configuration envelope. It checks canonical/bounded JSON, audience, trusted UTC validity and expiry, root signature through an injected verifier, exact SHA-256 binding to the trust-store bytes, and trust-store policy through `PinnedTrustStoreVerifier`.

The monotonic-store Protocol requires a durable atomic compare-and-swap and append-only audit in one transaction. The acceptance result is exposed only after successful commit. The included in-memory CAS, fake root verifier, and fake crypto backend are test fixtures only.

**Production boundary:** this module is not a deployed trust control plane. No production root key/verifier, durable monotonic store, transactional audit backend, KMS/HSM, network service, provider, or VM is provisioned. A Protocol definition does not prove a concrete storage backend is atomic, durable, rollback-resistant, or crash-safe.

Run the focused tests:

```bash
python -m unittest discover -s tools/task_orchestrator/tests -p 'test_trust_config_acceptance.py' -v
```

Keep `execution_authorized: false` and `eligible_for_untrusted_execution: false`. Do not use this module's test success as permission to execute untrusted code.

## Host-side Sandbox evidence collector contract

- `sandbox_host_evidence.py` assembles bounded observations from explicitly trusted host, guest, and external-canary observer identities according to the pinned 20-probe manifest.
- It enforces attempt/runtime/policy binding, required independent observer domains, monotonic offsets, duplicate rejection, timestamp freshness, per-observation/probe/aggregate size limits, deterministic evidence encoding, and host-side payload digests.
- It preserves failed outcomes and rejects missing or untrusted observations. Returned evidence maps are immutable.
- This is an evidence-assembly contract only: no probe runner, subprocess, VM, socket, network client, provider, identity provisioning, signature creation, or execution authorization exists.
- The observer identity sets must eventually come from a protected out-of-band trust source; this module does not cryptographically authenticate them.
- Both `execution_authorized` and `eligible_for_untrusted_execution` remain false.
- See [the host evidence collector contract](../../docs/SANDBOX_HOST_EVIDENCE_COLLECTOR.md).

## Host-controller lifecycle state machine contract

- `sandbox_host_lifecycle.py` validates a fixed, typed lifecycle event stream: runtime readiness, observation, evidence outcome, termination, runtime termination, and cleanup.
- It pins attempt/runtime/policy identity and monotonic start/deadline; rejects out-of-order events, stale identity, invalid deadline transitions, arbitrary event names, and unbounded failure text.
- Both successful and rejected evidence paths require explicit termination and cleanup confirmation. Cleanup failure is terminal.
- It is a pure state-transition validator, not a process supervisor or VM controller. It invokes no adapter and has no subprocess, shell, filesystem, socket, network, provider, or guest capability.
- All execution authorization flags remain false. See [the lifecycle contract](../../docs/SANDBOX_HOST_LIFECYCLE.md).


## Bounded Sandbox artifact collector contract

- `sandbox_artifacts.py` validates typed in-memory artifact candidates and emits a deterministic manifest bound to attempt, runtime, policy, evidence digest, and signed acceptance-report digest.
- It restricts logical paths to normalized relative `artifacts/` and `reports/` roots; rejects traversal, absolute/Windows paths, symlink/directory/device declarations, duplicate paths, empty files, and unsupported components.
- Limits are 64 artifacts, 256 KiB per file, 2 MiB aggregate, 240 path bytes, and 30 days maximum retention. Host-side SHA-256 is recomputed from supplied bytes.
- This is not a filesystem collector: it does not open paths, inspect inode types, authenticate evidence/report signatures, store/delete artifacts, or prove that a candidate is a regular file. The retention value is metadata only.
- A real host collector must use descriptor-relative no-follow traversal, `fstat`, same-descriptor hashing/copying, TOCTOU defenses, trusted retention enforcement, and independently verified report/evidence bindings. See [the artifact collector contract](../../docs/SANDBOX_ARTIFACT_COLLECTOR.md).
- Tests use in-memory fixtures only. Both execution authorization flags remain false.


## Sandbox artifact inventory contract

- `sandbox_artifacts.py` validates bounded in-memory artifact candidates and produces a deterministic SHA-256 manifest bound to attempt, runtime, policy, evidence, and signed-report digests.
- It rejects non-normalized/out-of-root paths, symlink/directory/device declarations, hard-linked records, duplicates, empty files, and count/per-file/aggregate/retention limit violations.
- This is not a filesystem collector: caller-supplied file-kind/link-count metadata is not independently verified. A future host adapter must use descriptor-relative no-follow traversal and `fstat` on the same descriptor used to hash/copy bytes.
- The manifest does not authenticate the signed report or artifact provenance, enforce retention, apply patches, or authorize execution. Unit tests use in-memory fixtures only.
- Run focused tests with `python -m unittest discover -s tools/task_orchestrator/tests -p 'test_sandbox_artifacts.py' -v`. Keep both execution authorization flags false.
