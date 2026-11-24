# GitHub Multi-Agent Task Protocol (v1)

## Purpose

GitHub Issues are the shared, provider-neutral command inbox for ChatGPT, Grok, and future agents. A task is authored once and can be independently read by any connected agent. The repository's Task Orchestrator remains authoritative for scope, verification, audit history, and task state.

This protocol does not assume that every GitHub connection has identical permissions. Each agent must use only the operations its own connection actually exposes.

## Creating a command

Create an Issue titled [JET-AGENT] followed by a short task title. Include the marker below and exactly one fenced JSON object after it. The payload is the machine-readable command; prose outside it is explanatory only.

<!-- jet-agent-task:v1 -->

\`\`\`json
{
  "schema_version": 1,
  "task_id": "smart-server-health",
  "goal": "Improve server health selection and report measured behavior.",
  "capability": "implementation",
  "risk": "medium",
  "assigned_agent": "any",
  "allow": ["lib/**", "test/**"],
  "exclude": ["lib/secrets.dart"],
  "scope_reason": "Keep the task within application logic and tests.",
  "verification_profiles": ["flutter-analysis", "flutter-tests"]
}
\`\`\`

Allowed values:
- capability: implementation, bug_fix, refactor, documentation, investigation.
- risk: low, medium, high.
- assigned_agent: any, chatgpt, grok.
- verification_profiles: only the Orchestrator's fixed profiles.

The validator rejects duplicate JSON keys, unknown fields, unsupported profiles, path traversal, protected paths, oversized payloads, and malformed task IDs. It never executes a command or applies a patch.

## Agent operating procedure

1. Parse the Issue's marked JSON payload against the documented v1 schema. If a local checkout is available, run github_task_protocol.py; otherwise rely on the trusted workflow's validator and independently inspect the exact payload.
2. Confirm the assigned agent is any or matches the chat the user activated.
3. Read current project memory at the pinned base SHA and inspect current branch/PR/lease state; never rely on stale chat summaries when GitHub state is available.
4. Obtain the lease through the Issue-comment command bridge before editing. If the chat connector cannot comment on Issues, ask the user to post the exact command. Do not treat a comment alone as ownership proof; verify the remote lock ref. See GITHUB_TASK_LEASES.md.
5. Create a dedicated remote task branch from the exact pinned base SHA and keep all changes within the declared allowlist and outside exclusions.
6. Renew before expiry with a fresh claim ID. If renewal or ownership verification fails, stop writing immediately.
7. Use the connected GitHub integration for in-scope reads/writes, open a Draft PR with the exact PR envelope, and let GitHub Actions run the fixed checks. Report exact run IDs and unresolved risks.
8. Release the lease after completion or abandonment. Read-only review by the other agent is allowed without an implementation lease.
9. Report verified facts separately from assumptions. Never claim a build, test, device check, or runtime behavior passed without evidence.
10. Do not merge, release, deploy, change production settings, or touch credentials/signing/payment paths without separate explicit user approval.

## Concurrency and trust

The lease transport uses Git's server-side \`--force-with-lease\` check to atomically compare the observed remote ref head during update. A first claim uses a non-force create-ref push. A failed or ambiguous operation is not ownership; agents must re-read state and must not edit task files until a successful lease result is verified.

The lease owner field is a protocol identity label, not cryptographic proof of which model or human is operating. GitHub credentials must be independently authorized for contents write access. Read-only reviews do not require a lease, but reviewers must not modify task branches.

A GitHub App installation or repository permission does not prove that an agent has shell access, Actions dispatch, or access to another agent's runtime. Never infer those capabilities from the word connected.

## Privacy and cost

This route does not call a separate model API, require an API key, or manually upload source to an external model endpoint. Repository data is accessed through each provider's GitHub integration, so do not claim that data never leaves GitHub or that ChatGPT and Grok have identical data-handling terms. Chat usage remains subject to each product's plan and limits.

## Current rollout status

- v1 task payload schema and local validator: implemented and tested.
- GitHub Issue intake and event-driven validation: active; it validates/packages tasks but does not dispatch a model.
- Lease state machine and Git transport: implemented, including claim/renew/release, server-side compare-and-swap, and a live race test.
- Trusted Issue-comment workflow: claim/renew/release and lease-verified handoff artifacts are available.
- PR scope guard: validates task Issue, assignment, active lease, pinned base, and changed paths without executing PR-head code.
- Approved implementation route: user-activated ChatGPT/Grok chats using their existing GitHub connections. The agent verifies the lock, creates a remote branch from the pinned base, reads in-scope repository content, commits through the connector, and opens a Draft PR.
- The handoff and agent-input artifacts do not wake a model and are not automatically attached to a chat. The ephemeral Actions branch is not the remote implementation branch.
- A connector's write permissions must be verified operation by operation. If Issue-comment or repository-write actions are unavailable, the user performs that discrete action.
- No paid model API, API key, provider runtime, or external source-upload adapter is part of the approved route. GitHub content is still processed through the connected provider integration.
- Keep one active implementation agent per task; read-only review by the other agent is permitted.
- Human review and explicit approval for merge/release/deploy remain mandatory.

## Comment-based lease operations

For an open task Issue carrying the \`agent-task\` label, an OWNER, MEMBER, or COLLABORATOR may issue one of these exact single-line comments:

\`\`\`text
/jet-agent claim chatgpt <claim-id> [minutes]
/jet-agent renew chatgpt <previous-claim-id> <new-claim-id> [minutes]
/jet-agent release chatgpt <claim-id>
\`\`\`

Replace \`chatgpt\` with \`grok\` when appropriate. The command owner must match \`assigned_agent\`, unless the task is assigned to \`any\`. The workflow validates the Issue payload and fixed command grammar, then uses the trusted default-branch lease adapter. A new claim pins the current \`main\` SHA; renewals preserve the base SHA already recorded in the lease. A result comment reports the verified lease details.

This workflow remains a command bridge, not an agent runtime. Successful claim/renew also creates a bounded lease-verified task handoff artifact in the same GitHub Actions run; it does not wake either model, start a runtime, run implementation commands, or transfer repository source files. Agents must verify the current lease and their own execution capabilities before editing.


## Live workflow verification

On 2026-11-23, the complete Issue command bridge was exercised against temporary Issue [#24](https://github.com/majidbusy09-blip/jetconfig-vpn/issues/24): claim, renew, and release all completed successfully in separate GitHub Actions runs (45178623063, 45178678823, 45178732222). The final lock record was independently checked as released, and the test Issue was closed. This validates the GitHub command/lease workflow, but does not imply model wake-up or autonomous provider execution.


## Submitting an implementation PR

An agent PR must include this marker and exactly one fenced JSON envelope after it. The marker and JSON fence must be the final content in the PR body; do not place the marker at the beginning and do not add trailing prose:

    <!-- jet-agent-pr:v1 -->
    ```json
    {"schema_version":1,"task_issue":42,"owner":"chatgpt","claim_id":"<current-claim-id>"}
    ```

The read-only trusted-main PR guard checks the linked open task Issue, assignment, active lease and expiry, exact claim ID, pinned-base merge ancestor, and every changed path against allow/exclude patterns. Ordinary non-agent PRs are skipped. The guard never checks out or executes PR-head code and never writes to GitHub. Normal PR validation remains responsible for running tests; human review and explicit merge approval remain required.


## Approved ChatGPT + Grok GitHub-connector operating model — 2026-11-24

The active implementation route is the user's existing ChatGPT and Grok chat sessions using each session's already-connected GitHub integration. Do not add, request, configure, or call OpenAI/Grok model APIs, API keys, paid model endpoints, or external source-upload services for this route. GitHub is the durable task inbox, lease authority, source of truth, PR history, and project memory.

### Execution sequence
1. The user creates or selects an open Issue carrying the agent-task label and the validated jet-agent-task v1 payload. The payload defines task ID, goal, capability, risk, assignment, explicit allow/exclude paths, scope reason, and fixed verification profiles.
2. The user activates exactly one implementation chat and identifies the intended owner (chatgpt or grok). If that chat's GitHub integration cannot create Issue comments, the user posts the exact /jet-agent claim command. Do not assume connector write capabilities that have not been verified.
3. Wait for the trusted Issue-comment workflow's success comment. Independently read the lock ref agent-locks/<task_id> and verify owner, claim ID, active status, expiry, pinned base SHA, and lock commit. No successful and current lease means no implementation.
4. Create a dedicated remote implementation branch from the exact pinned base SHA (normally agent/<task_id>). The ephemeral local branch created by the Actions handoff-acceptance step is not the remote implementation branch and must not be mistaken for one.
5. Read the project-memory documents from that exact base SHA. On the PR #89 candidate, the new v1.2 envelope contains eight canonical documents; this is not a main-branch capability until PR #89 is explicitly merged. Never claim a candidate-branch feature is already on main.
6. Inspect only files inside the Issue allowlist. Use semantic source suggestions when the corresponding verified index is available; otherwise use GitHub code search and fetch only relevant in-scope files. Source selection is explicit; suggestions never widen scope automatically.
7. Make commits only on the task branch through the connected GitHub integration. Keep each agent's implementation branch separate. Do not have two agents edit the same task concurrently. A second agent may perform read-only review without taking the implementation lease.
8. Open a Draft PR with the exact jet-agent-pr v1 metadata, Issue number, owner label, and current claim ID. The trusted PR guard checks the task, lease, pinned base, and changed paths; GitHub Actions runs the declared checks. Report exact commit SHA, changed paths, test run IDs, and unresolved risks.
9. Renew before expiry using a fresh claim ID and the same pinned base SHA. If renewal or lease verification fails, stop writing immediately. Release the lease after completion or abandonment. Human approval is required for merge, release, deployment, or production changes.

### Connector and execution boundaries
- A chat session is activated by the user; GitHub Issues do not wake ChatGPT or Grok and neither chat continuously polls the repository in the background.
- The GitHub connector can read repository data and, where its granted operations allow, create branches, commits, and PRs. Each agent must inspect its actual available operations. If an operation is unavailable, the user performs that discrete GitHub action; never invent a successful write.
- The jet-agent-handoff artifact is an audit snapshot of the Issue and lease. The jet-agent-input artifact is generated in a temporary Actions workspace; neither artifact automatically enters a ChatGPT/Grok conversation. The connected agent reads the pinned Issue, memory files, lease, and relevant source directly through its GitHub integration.
- GitHub's connected integration processes repository data through the relevant provider integration. Do not claim that no data leaves GitHub or that provider data handling is identical. The constraint is no separate paid model API, API key, or manual external source upload.
- This route does not execute task-supplied shell commands or run untrusted source in a model runtime. GitHub Actions performs the fixed repository checks. A real isolated sandbox remains a separate requirement only if a future design introduces arbitrary untrusted-code execution.
- The lease owner value is a protocol label, not cryptographic proof of which model or human is operating. The user chooses which chat is activated and controls the claim command. Never describe the owner string as provider authentication.

This section supersedes older instructions in this document that require a separate provider runtime, external model API adapter, source upload, or isolated execution environment before ChatGPT/Grok can perform GitHub-based implementation.

## Verified ChatGPT connector pilot — 2026-11-24

The documentation-only pilot completed on Issue #90 and PR #91. The ChatGPT GitHub integration in this session successfully read the Issue/comments and lease ref, posted the Issue claim/release comments, created a remote branch from the exact pinned base SHA, committed an in-scope Markdown file, and opened a Draft PR. The lock was independently read before/after claim and showed a stable ref; the release workflow then wrote and verified status=released. PR #91 head `652e3d38a594adfb4b0784971c25010b5a5e3382` passed the trusted PR guard (`45461329913`), Non-production PR Validation (`45461334216`), and Project Memory Audit (`45461334389`). PR #91 remains Draft/open/unmerged. The first guard attempt rejected a marker placed at the start of the PR body; moving the marker and JSON block to the very end made the guard pass. Grok's separate connector capabilities have not yet been verified.
