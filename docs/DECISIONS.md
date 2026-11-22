# JET VPN — Technical Decisions

This log records decisions that govern future work. New entries should include date, status, rationale, and consequences. Do not erase superseded decisions.

## D-001 — GitHub source is authoritative for Android client

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Use the current GitHub repository/branch/commit as source of truth for client code; old ZIP archives and chat snippets are historical context only.
- **Rationale:** The user may have newer local changes than old uploaded archives.
- **Consequence:** Fetch latest source and record SHA before each task.

## D-002 — Branch + diff + PR approval workflow

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Work on isolated branches, inspect diff and verification evidence, and request explicit approval before merge/release.
- **Rationale:** Real code changes are allowed but production actions must remain under user control.
- **Consequence:** Never merge or release autonomously.

## D-003 — Project memory is part of the deliverable

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Update source-grounded project documents whenever implementation changes affect architecture, APIs, data, payment, issues, tests, or workflow.
- **Rationale:** A future agent must be able to resume without depending on conversational memory.
- **Consequence:** Every material code PR should include appropriate memory updates.

## D-004 — Release workflow is a protected boundary

- **Date:** 2026-11-22
- **Status:** Accepted; remediation not yet implemented
- **Decision:** Treat merge to `main` as potentially publishing a production Release while `.github/workflows/build.yml` triggers on main push.
- **Rationale:** Workflow has release publishing and signing behavior.
- **Consequence:** Do not merge without explicit release approval; separately propose a release gate.

## D-005 — API docs distinguish client observation from server truth

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Document request fields and response usage from Flutter source as client-observed only until backend source is reviewed.
- **Rationale:** Client behavior cannot prove authorization, validation, idempotency, or payment correctness on the server.
- **Consequence:** Use explicit server-unverified markers and do not make security claims about backend.
