# Task Orchestrator — Verified Current Status

- **Updated:** 2026-11-24
- **Repository:** `majidbusy09-blip/jetconfig-vpn`
- **Authority:** This file records the verified state on `main` after PR #44. It supersedes older status sentences in design notes that still describe PR #20 as open or CI as pending. Those documents remain useful for design rationale, but their historical status headers must not be treated as current.

## 1. What is now implemented and merged

The local, provider-neutral task workflow has the following merged building blocks:

1. **Task orchestrator MVP (PR #20):** task lifecycle, pinned repository/base state, scope checks, fixed verification profiles, evidence and human-review handoff.
2. **Task contract and context preparation:** bounded full-text project/source context, deterministic envelope construction, strict schema/path/budget validation, content fingerprints and semantic-context provenance.
3. **GitHub task protocol and intake:** structured Issue task format, validation-only intake, lease/claim lifecycle and task handoff artifacts.
4. **Provider-neutral dispatch (PR #35 and follow-ups):** explicit trusted adapter registry and fixture-only local dispatch. Fixture dispatch is not a live model invocation.
5. **Local patch artifact store (PR #38):** content-addressed SHA-256 patch storage and fail-closed validation.
6. **Live patch-review authorization gate (PR #39):** validates task, Issue, lease, pinned base and workspace observations; success means review readiness only.
7. **Read-only live patch-review command (PR #40):** obtains current GitHub/lease observations and local Git state before invoking the gate.
8. **Provider-result ingestion (PR #41):** accepts local provider-neutral result JSON and exact patch bytes, validates them, and writes a task-local result without applying the patch.
9. **Integration coverage:** PR #42 connects fixture dispatch to ingestion; PR #43 covers the live review command; PR #44 connects provider-result ingestion directly to the live review command.

PRs #38, #39, #40, #41, #42, #43 and #44 are merged. PR #44's head was `af5fc704f61fd8a656966b35ddbe9450630d8c1f`; its squash merge commit is `f682c56331bfb7c07bc4c5be26fddc33a3043969`.

## 2. What the integrated path proves

The tested local path is:

`validated task envelope → provider-neutral result + exact patch bytes → ingestion and SHA-256 artifact storage → live Issue/lease/workspace checks → ready_for_human_review`

The resulting review state explicitly keeps `applied: false`. The PR #44 integration test uses mocked GitHub and lease observations. It proves that the local data contracts and command handoff connect; it does **not** prove that a live model generated a patch or that a real provider sandbox ran code.

## 3. What is not implemented or authorized

- No live coding model is invoked by the end-to-end orchestrator path.
- The local fixture provider is test infrastructure, not an autonomous coding agent.
- No approved isolated runtime is connected to the dispatcher.
- No agent patch is automatically applied to a task branch by the provider-result ingestion or patch-review command.
- No provider source upload, private repository upload, API key creation, paid account, sandbox provisioning, model execution, or spend is authorized.
- No production release, deployment, bot/payment/backend/server change is part of this workflow.
- The existing hosted CI runner is not an approved untrusted-code sandbox. A benign Bubblewrap self-test is not proof of isolation.
- The PR guard validates task PRs, but repository branch protection has not been verified to require that check. Do not claim the guard alone blocks every merge.

## 4. Next engineering milestone

The next meaningful milestone is **a sandbox acceptance and execution-boundary pilot**, not enabling a live provider immediately.

Before any real provider or private source is introduced, the design must demonstrate, with evidence from the exact configured runtime:

- an explicitly selected VM/microVM boundary rather than a shared-kernel container;
- outbound networking disabled by default, including DNS and non-HTTP paths;
- no credentials, GitHub token, signing material or production secrets inside the worker;
- bounded CPU, memory, process count, wall-clock time, file count and output size;
- reliable cancellation of the process tree and destruction of the worker after success, failure, timeout and interrupted control-plane calls;
- bounded export of a synthetic artifact only, followed by independent digest/path/scope validation;
- auditable lifecycle metadata and fail-closed behavior when any control cannot be verified.

The current candidate evaluation names E2B as the first candidate and Daytona Linux VM as the alternative. This is a **candidate selection only**, not an account approval or a passed security assessment. The pilot must use synthetic fixtures, no model provider, no credentials, no GitHub write access and no private JET VPN source. Verify current region, DPA, subprocessors, retention/deletion terms and actual pricing before any provisioning or data transfer.

## 5. Approval boundary

A separate explicit approval is required before creating a vendor account/project, entering or creating credentials, accepting paid terms, provisioning a sandbox, uploading any private source, invoking a live model, or incurring any cost. Until then, work may continue on local contracts, deterministic fixtures, documentation and tests that do not imply runtime isolation.

## 6. Reporting language

Use these distinctions in all status reports:

- `fixture-tested`: deterministic local test adapter only.
- `ingested`: structured result and exact patch bytes passed local contract/artifact validation.
- `ready_for_human_review`: live authorization observations passed; patch remains unapplied.
- `sandbox-accepted`: only after the exact configured runtime passes the full synthetic acceptance suite with retained evidence.
- `provider-executed`: only after an actual configured provider invocation is independently evidenced.

Never describe the current system as a live autonomous coding agent until the final two states are genuinely achieved.
