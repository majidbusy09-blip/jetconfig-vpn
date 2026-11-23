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
- The adapter is not yet wired into the Issue intake workflow or either provider's execution runtime. No automatic ChatGPT/Grok wake-up or dispatch exists.
- Until a live race test and provider runtime integration are completed, keep one active implementation agent per task. Read-only review by another agent is permitted.
- The Issue intake workflow remains read-only (\`contents: read\`, \`issues: read\`) and only validates task payloads and uploads a task artifact. That artifact is not a lease or execution grant.
- No paid model API, provider credential, private-source upload, or external sandbox is configured.

See also [MULTI_AGENT_GITHUB_PROTOCOL.md](MULTI_AGENT_GITHUB_PROTOCOL.md).


## Issue comment command bridge

The trusted-main workflow \`.github/workflows/agent-lease-commands.yml\` accepts only fixed, single-line commands on open Issues labeled \`agent-task\`:

\`\`\`text
/jet-agent claim chatgpt <claim-id> [minutes]
/jet-agent renew chatgpt <previous-claim-id> <new-claim-id> [minutes]
/jet-agent release chatgpt <claim-id>
\`\`\`

The commenter must be a repository OWNER, MEMBER, or COLLABORATOR, and the command owner must match the task's \`assigned_agent\` unless it is \`any\`. A new claim pins the current default-branch commit; renewal reads the existing lease and preserves its pinned base. The workflow posts the verified result on the Issue.

The workflow checks out trusted \`main\`, uses a short-lived \`GITHUB_TOKEN\` with \`contents: write\` and \`issues: write\`, and treats Issue/comment text as data only. It never runs text from the Issue as shell input. This is a manual lease-control interface, not automatic ChatGPT/Grok dispatch or an implementation runner.


## End-to-end command workflow evidence

The trusted-main Issue command workflow passed a full live claim/renew/release cycle on temporary Issue [#24](https://github.com/majidbusy09-blip/jetconfig-vpn/issues/24), which was closed after the test. Claim, renewal, and release runs succeeded (Actions runs 45178623063, 45178678823, and 45178732222). The final remote lease record was independently read and showed status = released, the renewed claim ID, and the original pinned base SHA. The lock branch is intentionally retained as a released audit record.
