# JET VPN — Development Rules

## Before every task

1. Apply `AGENTS.md` and load the relevant project-memory documents.
2. Ask the collaborator-priority question from `AGENTS.md`; defer work that does not improve the independent, accurate, project-memory-aware programming collaborator unless explicitly requested.
3. Verify the target branch and latest commit SHA.
4. Re-fetch relevant source; do not rely on line numbers from an older snapshot.
5. Trace callers, state, persistence, callbacks, network/API requests, native integration, and build workflow.
6. Identify expected behavior, invariants, failure modes, and test plan before editing.

## Branching and approval

- Create one isolated branch per coherent task, based on the latest appropriate base.
- Never commit directly to `main`.
- Never merge, tag, publish a Release, or deploy without explicit user approval.
- The production release workflow is manual-only. It requires `workflow_dispatch`, ref `main`, and explicit `confirm_release=true`; ordinary main pushes and PR merges do not publish a Release.
- Never trigger the production release workflow without separate explicit approval.

## Implementation discipline

- Make the smallest complete change; avoid unrelated refactors.
- Preserve app version/build number unless release work is explicitly approved.
- Do not assume backend behavior from client code.
- Mark unknowns and hypotheses clearly.
- Treat credentials, payment tokens, signing material, and user data as sensitive.
- For VPN work, trace user intent, native stop flags, lifecycle, generation counters, verification, and recovery timing together.

## Verification

- Inspect the complete diff and changed-file list.
- Run formatter/analyzer/tests/build where feasible.
- State exactly which checks ran and which did not.
- A build is not a device test; static analysis is not behavioral verification.
- Do not mark an issue fixed until the relevant regression test or reproducible verification passes.

## Memory updates

Update architecture/API/storage/payment/issue/decision/test/status documents whenever a change affects them. Append to the development log. Each verified fact must be anchored to a source commit and path/line range. If the source commit changes, mark affected maps stale until rechecked.
