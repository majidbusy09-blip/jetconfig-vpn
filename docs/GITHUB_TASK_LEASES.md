# GitHub Task Ownership Leases (v1)

## Purpose

Issue comments are audit records, not locks. A read-then-comment flow permits two agents to observe an unclaimed task and both begin implementation. A task may have only one active implementation lease.

## Lock storage and atomicity

Each task has one deterministic control-plane branch: \`agent-locks/<task_id>\`. Its tip commit contains a machine-readable lease at \`.agent-locks/lease.json\`. This branch is not an implementation branch and must never be merged into product code.

The transport adapter uses Git's server-side \`--force-with-lease=<ref>:<expected-old-sha>\` push option for updates. The Git receive-pack service checks the expected old object as part of the ref update; this is materially different from a client-side fetch-then-update check or a plain GitHub REST ref update.

- First claim: create the lock ref with a normal, non-force push. If another claimant created it first, the push fails.
- Existing claim: read the exact remote ref, fetch that ref, validate its lease, create a commit whose parent is the observed head, then push with \`--force-with-lease\` pinned to that exact head.
- A successful push is followed by a remote ref read. The adapter reports success only if the remote still points to the exact commit it created.
- A stale read, failed push, malformed lease, unknown result, or verification mismatch fails closed. The agent must not begin implementation.

## Lease rules

The record binds task ID, owner (\`chatgpt\` or \`grok\`), unique claim ID, status, UTC claim/expiry timestamps, and pinned task base SHA. Duration is at most four hours.

- An active, unexpired lease blocks a new claim by another agent.
- Renew before expiry as the current owner, using a fresh claim ID and the same pinned base SHA. Renewal uses the same server-side compare-and-swap operation.
- A released or expired lease may be replaced only through compare-and-swap against the exact observed lock head.
- Release requires the current owner and claim ID, and changes the record to \`released\` through compare-and-swap. Never delete or force-reset a lock ref to release it.
- Expiry alone does not grant ownership; takeover requires a successful atomic ref update.
- A crashed agent's lease can expire; recovery uses a new claim ID and compare-and-swap.

The owner field is a protocol identity label, not cryptographic proof of which model or human is operating. The token used by the adapter must be independently authorized for repository contents write access.

## Git transport adapter

\`github_lease_git.py\` is the authenticated transport. It requires an existing checkout with Git installed, \`GITHUB_REPOSITORY=owner/repository\`, and a short-lived \`GITHUB_TOKEN\` (or \`GH_TOKEN\`) with \`contents: write\`. It derives the remote URL from the validated repository identity; it does not accept arbitrary hosts. It invokes Git with argument arrays and \`shell=False\`, uses the token only in a process-scoped HTTP authorization header, and suppresses raw Git stderr from user-facing errors.

Claim:

\`\`\`bash
python -m tools.task_orchestrator.github_lease_git claim \\
  --task-id sample-task --owner chatgpt --claim-id 0123456789abcdef \\
  --base-sha <full-pinned-git-sha> --minutes 60
\`\`\`

Renew (must use the original pinned base SHA and a fresh claim ID):

\`\`\`bash
python -m tools.task_orchestrator.github_lease_git renew \\
  --task-id sample-task --owner chatgpt --claim-id fedcba9876543210 \\
  --previous-claim-id 0123456789abcdef --base-sha <same-pinned-git-sha> --minutes 60
\`\`\`

Release:

\`\`\`bash
python -m tools.task_orchestrator.github_lease_git release \\
  --task-id sample-task --owner chatgpt --claim-id fedcba9876543210
\`\`\`

The timestamp defaults to current UTC; \`--now\` is available for deterministic tests. Never store a token in source, task JSON, Issue text, or a committed file.

## Validation and remaining rollout boundary

- Local lease schema/state-machine logic and adversarial tests are implemented.
- The Git transport adapter and tests for its CAS push construction are implemented.
- CI exercises Git commit construction and stale compare-and-swap rejection against a local bare Git remote. The trusted-main live probe passed on 2026-11-23 (Actions run `45176916962`): two concurrent writers used the same expected old SHA, exactly one push succeeded, the resulting ref matched that winner, and the disposable probe ref was deleted.
- The adapter is exposed through the trusted Issue-comment claim/renew/release workflow. Claim and renew also produce a lease-verified handoff artifact; neither action wakes a model or dispatches an implementation runtime.
- No automatic ChatGPT/Grok wake-up or provider runtime dispatch exists. Keep one active implementation agent per task; read-only review by another agent is permitted.
- The reusable Issue intake workflow is read-only (contents: read, issues: read) and can be called by a target repository while loading trusted project manifests and tooling from the central control-plane repository. It validates task payloads and uploads a task artifact; that artifact is not a lease or execution grant.
- A project in registered lifecycle may enter this read-only intake with status validated-awaiting-activation. The lease-command path retains the active-lifecycle gate, so registered/paused/retired projects cannot claim a lease or prepare an implementation handoff.
- No paid model API, provider credential, private-source upload, or external sandbox is configured.

See also [MULTI_AGENT_GITHUB_PROTOCOL.md](MULTI_AGENT_GITHUB_PROTOCOL.md).


## Issue comment command bridge

The trusted-main workflow \`.github/workflows/agent-lease-commands.yml\` accepts only fixed, single-line commands on open Issues labeled \`agent-task\`:

\`\`\`text
/jet-agent claim chatgpt <claim-id> [minutes]
/jet-agent renew chatgpt <previous-claim-id> <new-claim-id> [minutes]
/jet-agent release chatgpt <claim-id>
\`\`\`

The commenter must be a repository OWNER, MEMBER, or COLLABORATOR, and the command owner must match the task's \`assigned_agent\` unless it is \`any\`. A new claim pins the current default-branch commit; renewal reads the existing lease and preserves its pinned base. The workflow posts the verified result on the Issue. Successful claim/renew operations also create a 14-day lease-verified task handoff artifact containing the validated Issue payload, Issue-body digest, active lease identity/expiry, pinned base SHA, lock ref, and workflow run identity. Release operations do not create a handoff.

The workflow checks out trusted \`main\`, uses a short-lived \`GITHUB_TOKEN\` with \`contents: write\` and \`issues: write\`, and treats Issue/comment text as data only. It never runs text from the Issue as shell input. This is a manual lease-control interface with a machine-readable handoff artifact, not automatic ChatGPT/Grok dispatch or an implementation runner.


## End-to-end command workflow evidence

The trusted-main Issue command workflow passed a full live claim/renew/release cycle on temporary Issue [#24](https://github.com/majidbusy09-blip/jetconfig-vpn/issues/24), which was closed after the test. Claim, renewal, and release runs succeeded (Actions runs 45178623063, 45178678823, and 45178732222). The final remote lease record was independently read and showed status = released, the renewed claim ID, and the original pinned base SHA. The lock branch is intentionally retained as a released audit record.


## Agent PR submission guard

Agent implementation PRs include the v1 PR envelope marker, task Issue number, owner label, and current claim ID. The trusted-main pull_request_target guard uses read-only GitHub permissions to verify the open task Issue, assignment, active/unexpired lease, pinned base SHA, and changed paths. It skips ordinary PRs and never checks out or executes PR code. It is a validation check only; it does not approve or merge PRs.


## Reusable cross-repository read-only intake

- `.github/workflows/agent-task-intake-reusable.yml` is a `workflow_call` workflow. It checks out the calling repository at the event revision, checks out the trusted central control-plane repository separately under `.jet-ai/central`, and runs the intake module from that trusted checkout with the caller's original GitHub event payload.
- The local `.github/workflows/agent-task-intake.yml` is a thin caller of the reusable workflow. A registered target repository can add a similarly thin wrapper that calls `majidbusy09-blip/jetconfig-vpn/.github/workflows/agent-task-intake-reusable.yml@main`; repository metadata in the event is therefore the target repository, not the control-plane repository.
- V2 intake validates the exact target repository ID, full name, default branch, project ID, and manifest digest against the central checked-in registry. It does not execute target code, claim a lease, invoke a model, upload source, or grant implementation eligibility.
- Registered projects are explicitly marked `validated-awaiting-activation`. Lease claims continue to require `lifecycle=active`; intake acceptance must never be interpreted as permission to implement.
- The reusable lease/handoff workflow and automatic source-index artifact provisioning are separate remaining milestones. Do not install or invoke cross-repository lease execution until its target checkout, trusted tooling checkout, permissions, and handoff acceptance have their own exact-head integration tests.


## Project-scoped lease schema v2

Project-aware v2 tasks use the shared pure namespace helper in `tools/task_orchestrator/project_namespace.py`.

- Lock ref: `agent-locks/projects/<project_id>/<repository_id>/<task_id>`.
- Lease record: `.agent-locks/projects/<project_id>/<repository_id>/<task_id>.json`.
- Lease record schema version: `2`, with the complete validated project identity tuple (`project_id`, immutable numeric `repository_id`, canonical `repository_full_name`, `default_branch`, `manifest_schema_version`, and `manifest_sha256`) in addition to task/owner/claim/status/timestamps/base SHA.
- The namespace key uses `project_id` + `repository_id`; a repository rename keeps the same namespace but changes the full binding, so an existing lease cannot be silently reused. A manifest digest change behaves the same way.
- Claim, renew, release, handoff generation, handoff acceptance, the PR guard, and patch-review authorization all resolve the same branch/path and compare the same full binding. A v2 task never falls back to the v1 lock path.
- V2 workspace IDs include project_id, repository_id, manifest digest, task ID, and pinned base SHA. Legacy workspace IDs retain the original derivation.

Legacy schema v1 remains byte-for-byte compatible: lock branch `agent-locks/<task_id>` and record `.agent-locks/lease.json`. V1 intake remains restricted to the original JET VPN repository. No automatic migration or namespace rebinding is performed.


## Live read-only intake smoke evidence — 2026-11-25

- Hesabgar temporary Issue #17 successfully invoked the target caller and central reusable workflow in runs `45677327585` and `45678817592`.
- The first successful artifact was `agent-task-17`, ID `15052647029`, 986 bytes, SHA-256 `684fcf539601637432ee08e861dc929ed989757ab1a47ddbab1cbe9f78471481`. The second retry artifact ID was `15053470675`, 1,005 bytes; it was downloaded and inspected.
- The inspected task JSON confirms `validated-awaiting-activation`, `implementation_eligible=false`, `lease_claimed=false`, `agent_dispatched=false`, `model_called=false`, and `source_uploaded=false`. The workflow log independently confirms no lease and no model/implementation agent invocation.
- The temporary issue is closed. No branch, PR, source upload, lease, or implementation change resulted from the test.
- Central PR #134 removes the `opened` trigger and keeps `labeled` as the single admission event plus `edited` for task-body changes. This prevents duplicate intake when an issue is created with the `agent-task` label. Hesabgar PR #18 applies the same correction and ensures workflow changes trigger project validation.
- This proves read-only intake only. It does not prove reusable lease/handoff, target workspace preparation, automatic source-index provisioning, or implementation execution.

