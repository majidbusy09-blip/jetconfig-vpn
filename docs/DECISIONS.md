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
- **Status:** Accepted; remediation implemented in PR #5
- **Decision:** Production release is manual-only and fail-closed: `workflow_dispatch`, selected ref exactly `main`, and explicit `confirm_release=true`. The release job alone receives `contents: write`.
- **Rationale:** Prevent ordinary pushes and PR merges from unintentionally publishing signed production APKs.
- **Consequence:** Never dispatch a production release without explicit user approval. Current implementation is in `.github/workflows/build.yml` at main commit `f396f57459c9863a325f27e7d438e9456d560e92`.

## D-005 — API docs distinguish client observation from server truth

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Document request fields and response usage from Flutter source as client-observed only until backend source is reviewed.
- **Rationale:** Client behavior cannot prove authorization, validation, idempotency, or payment correctness on the server.
- **Consequence:** Use explicit server-unverified markers and do not make security claims about backend.

## D-006 — Every task must pass the collaborator-priority test

- **Date:** 2026-11-22
- **Status:** Accepted
- **Decision:** Before prioritizing work, ask: «آیا این کار ما را به داشتن یک همکار برنامه‌نویس مستقل، دقیق و دارای حافظه پروژه نزدیک‌تر می‌کند؟» A negative answer means the work is not a priority unless explicitly requested.
- **Rationale:** Keep engineering effort focused on durable project understanding, implementation ability, verification, memory, and safe maintenance rather than unrelated activity.
- **Consequence:** Record the capability improved by each prioritized task; defer unrelated product features, marketing, visual changes, and refactors.


## D-007 — AST call-site map must not overclaim semantic resolution

- **Date:** 2026-11-22
- **Status:** Accepted; tooling merged in PR #16
- **Decision:** Introduce Dart Analyzer AST parsing in an isolated developer-tool package, but label the first call graph as syntactic and candidate-based until analyzer element resolution is implemented.
- **Rationale:** AST structure is more reliable than regex for declaration and invocation locations, but matching identifier names alone cannot prove which declaration a call binds to.
- **Consequence:** Keep ambiguous and unresolved calls explicit; never describe this first graph as a verified semantic call graph or runtime reachability map.


## D-008 — Multi-file analyzer index and curated critical-path report

- **Date:** 2026-11-22
- **Status:** Accepted; tooling merged in PR #16
- **Decision:** Resolve all tracked Dart source files under `lib/` as one application source set, fingerprint each file, and build cross-file edges from analyzer Elements. Define critical workflows through a source-path/owner/kind/name manifest and report static transitive reachability from those curated anchors.
- **Rationale:** A single-file graph cannot show cross-file impact once the app is split; explicit entrypoint anchors make impact analysis useful while remaining auditable.
- **Consequence:** Missing or ambiguous anchors fail closed and are reported. Static reachability is not runtime execution; callbacks, state-field dependencies, dynamic calls, and native Java behavior remain separate evidence boundaries.

## D-009 — Native VPN state is not live connection verification

- **Date:** 2026-11-22
- **Status:** Accepted; implementation merged in PR #16
- **Decision:** The UI may expose a connected state only when the native core reports CONNECTED, a live tunnel verification has succeeded, and no explicit UI-disconnect override is active. Cold restore and app resume must clear stale verification and require a fresh ping check before showing connected.
- **Rationale:** The native core can report CONNECTED before the data path is usable; retaining a stale verification flag or setting it from native state alone can produce a false-positive connected UI.
- **Consequence:** Failed silent verification must not stop the core or preserve a green/connected state. In smart mode, it falls back to the slow health watcher; device-level lifecycle and network tests remain necessary.


## D-010 — Sandbox signature trust is pinned outside the runtime trust domain

- **Date:** 2026-11-24
- **Status:** Accepted; policy adapter implemented in PR under review.
- **Decision:** Trust-store bytes must be canonical and match a SHA-256 digest supplied by protected out-of-band configuration. A protected caller-supplied minimum version must be enforced monotonically. Only unique, active, in-window Ed25519 public keys are eligible; revoked, retired, unknown, expired, not-yet-valid, malformed, or algorithm-mismatched keys fail closed.
- **Rationale:** A provider or guest must not be able to nominate its own verification key or roll back to an older trust policy.
- **Consequence:** `sandbox_trust.py` validates the store and delegates Ed25519 verification to an injected audited backend. It does not persist rollback state, provision keys, or authorize execution. Production integration requires protected deployment of the pinned digest/version floor and an approved cryptographic backend.
