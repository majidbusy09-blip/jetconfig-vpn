---
name: JET Agent Task
about: Create a structured task for ChatGPT, Grok, or another connected agent
title: "[JET-AGENT] "
labels: ["agent-task"]
assignees: []
---

Describe the requested outcome briefly. The JSON payload below is authoritative.

<!-- jet-agent-task:v1 -->

```json
{
  "schema_version": 1,
  "task_id": "replace-with-unique-kebab-case-id",
  "goal": "Describe the desired outcome and acceptance criteria.",
  "capability": "implementation",
  "risk": "medium",
  "assigned_agent": "any",
  "allow": ["lib/**", "test/**"],
  "exclude": [],
  "scope_reason": "Explain why these paths are sufficient.",
  "verification_profiles": ["flutter-analysis", "flutter-tests"]
}
```

Allowed agents: any, chatgpt, grok.
Allowed capabilities: implementation, bug_fix, refactor, documentation, investigation.
Allowed risk levels: low, medium, high.
Only fixed Orchestrator verification profiles are accepted.
