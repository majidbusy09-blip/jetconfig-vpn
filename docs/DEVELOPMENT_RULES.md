# JET VPN — Development Rules

## Before every task

1. Apply `AGENTS.md` and load the relevant project-memory documents.
2. Verify the target branch and latest commit SHA.
3. Re-fetch relevant source; do not rely on line numbers from an older snapshot.
4. Trace callers, state, persistence, callbacks, network/API requests, native integration, and build workflow.
5. Identify expected behavior, invariants, failure modes, and test plan before editing.

## Branching and approval

- Create one isolated branch per coherent task, based on the latest appropriate base.
- Never commit directly to `main`.
- Never merge, tag, publish a Release, or deploy without explicit user approval.
- Remember that merging to `main` currently triggers the production build/release workflow.

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
