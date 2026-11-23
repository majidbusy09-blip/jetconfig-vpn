# GitHub Multi-Agent Task Protocol (v1)

## Purpose

GitHub Issues are the shared, provider-neutral command inbox for ChatGPT, Grok, and future agents. A task is authored once and can be independently read by any connected agent. The repository's Task Orchestrator remains authoritative for scope, verification, audit history, and task state.

This protocol does not assume that every GitHub connection has identical permissions. Each agent must use only the operations its own connection actually exposes.

## Creating a command

Create an Issue titled [JET-AGENT] followed by a short task title. Include the marker below and exactly one fenced JSON object after it. The payload is the machine-readable command; prose outside it is explanatory only.

<!-- jet-agent-task:v1 -->

```json
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
```

Allowed values:
- capability: implementation, bug_fix, refactor, documentation, investigation.
- risk: low, medium, high.
- assigned_agent: any, chatgpt, grok.
- verification_profiles: only the Orchestrator's fixed profiles.

The validator rejects duplicate JSON keys, unknown fields, unsupported profiles, path traversal, protected paths, oversized payloads, and malformed task IDs. It never executes a command or applies a patch.

## Agent operating procedure

1. Read the Issue and validate its marked payload with python -m tools.task_orchestrator.github_task_protocol --body-file issue-body.md.
2. Confirm the assigned agent is any or matches the current agent.
3. Read current project memory and latest task/branch state before implementation; never rely on an old conversation summary when repository state is available.
4. Claim work visibly in the Issue before making changes. Include agent identity, task ID, intended branch, and timestamp. If another agent has already claimed or started the same task, do not work concurrently; coordinate or choose another task.
5. Create a dedicated task branch and keep all changes within the declared allowlist and outside exclusions.
6. Run the declared fixed checks, record actual outcomes, and open a Draft PR with a concise handoff.
7. Report verified facts separately from assumptions. Never claim a build, test, device check, or runtime behavior passed unless evidence exists.
8. Do not merge, release, deploy, change production settings, or touch credentials/signing/payment paths without separate explicit user approval.

## Concurrency and trust

GitHub Issue comments are an audit trail, not an atomic distributed lock. Agents must check for an existing claim immediately before starting and stop if ownership is ambiguous. The Orchestrator must later add a compare-and-swap claim mechanism before unattended parallel execution is enabled. Until then, safe operating mode is one active implementation agent per task; other agents may perform independent read-only reviews.

A GitHub App installation or repository permission does not prove that an agent has shell access, Actions dispatch, or access to another agent's runtime. Never infer those capabilities from the word connected.

## Privacy and cost

No API key is required to use this Issue protocol. The protocol itself does not call a model or transmit repository content outside the connected agent's normal GitHub integration. Each agent's own model/service usage remains subject to that provider's plan and limits. Do not add paid API calls, external sandboxes, secrets, or source uploads as part of this protocol.

## Current rollout status

- v1 payload schema and local validator: implemented.
- Adversarial fixture tests: implemented.
- GitHub Issue template and event-driven intake validation/artifact workflow: implemented; it does not dispatch an agent or claim a lease.
- CAS lease state machine: implemented as local transition logic; authenticated GitHub adapter and real concurrent-claim test remain pending.
- Automatic model/agent wake-up and multi-agent parallel execution: not implemented.
- Human review and explicit approval for merge/release/deploy remain mandatory.
