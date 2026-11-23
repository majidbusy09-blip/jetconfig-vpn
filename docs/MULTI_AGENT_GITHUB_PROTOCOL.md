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

1. Read the Issue and validate its marked payload with \`python -m tools.task_orchestrator.github_task_protocol --body-file issue-body.md\`.
2. Confirm the assigned agent is \`any\` or matches the current agent.
3. Read current project memory and latest task/branch state before implementation; never rely on an old conversation summary when repository state is available.
4. Acquire the task's GitHub ref lease using \`github_lease_git.py\` before editing. Do not rely on an Issue comment as ownership proof. See [GITHUB_TASK_LEASES.md](GITHUB_TASK_LEASES.md).
5. Create a dedicated task branch and keep all changes within the declared allowlist and outside exclusions.
6. Renew the lease before expiry with a fresh claim ID. If renewal fails or ownership cannot be verified, stop editing immediately.
7. Run the declared fixed checks, record actual outcomes, and open a Draft PR with a concise handoff.
8. Release the lease after the implementation is complete or abandoned.
9. Report verified facts separately from assumptions. Never claim a build, test, device check, or runtime behavior passed unless evidence exists.
10. Do not merge, release, deploy, change production settings, or touch credentials/signing/payment paths without separate explicit user approval.

## Concurrency and trust

The lease transport uses Git's server-side \`--force-with-lease\` check to atomically compare the observed remote ref head during update. A first claim uses a non-force create-ref push. A failed or ambiguous operation is not ownership; agents must re-read state and must not edit task files until a successful lease result is verified.

The lease owner field is a protocol identity label, not cryptographic proof of which model or human is operating. GitHub credentials must be independently authorized for contents write access. Read-only reviews do not require a lease, but reviewers must not modify task branches.

A GitHub App installation or repository permission does not prove that an agent has shell access, Actions dispatch, or access to another agent's runtime. Never infer those capabilities from the word connected.

## Privacy and cost

No model API key is required to use this Issue protocol or the Git lease transport. The protocol itself does not call a model or transmit repository content outside the connected agent's normal GitHub integration. The lease adapter sends Git ref/object operations to GitHub using the configured repository token; it does not upload source context to an external model or sandbox. Each agent's own model/service usage remains subject to that provider's plan and limits.

## Current rollout status

- v1 payload schema and local validator: implemented and tested.
- GitHub Issue template and event-driven intake validation/artifact workflow: active on the default branch; it validates and packages tasks but does not dispatch an agent.
- Lease state machine: implemented and tested, including renewal.
- Git transport adapter: implemented; CI verifies its commit construction and server-side force-with-lease behavior against a local bare remote. A live GitHub concurrent-claim test remains outstanding.
- Live concurrent-claim race test against GitHub: not yet performed; CI validates Git CAS behavior against a local bare remote.
- Provider runtime integration and automatic ChatGPT/Grok wake-up: not implemented.
- Until the live race test and provider runtime integration are complete, use the lease adapter explicitly and keep one active implementation agent per task. Read-only review by another agent is permitted.
- Human review and explicit approval for merge/release/deploy remain mandatory.
