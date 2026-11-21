# JET VPN — Development Rules

## Branching and approvals

- Base all work on the latest `main` unless the task explicitly targets another branch.
- Create a dedicated branch for every independent task.
- Never write commits directly to `main`.
- Do not merge a PR without explicit user approval.
- Keep the user informed of changed files, rationale, risks, and verification performed.

## Before changing code

1. Read the relevant current source from the target branch.
2. Trace callers, state variables, callbacks, persistence, and native/build integrations affected by the change.
3. Identify behavioral invariants and possible side effects.
4. Prefer the smallest coherent patch; avoid unrelated refactors in a feature fix.
5. Check version declarations and do not bump them without a release reason/approval.

## After changing code

1. Inspect the complete diff.
2. Run formatting and static analysis where the environment permits.
3. Run relevant unit/widget tests.
4. Run the Android build when feasible.
5. Clearly distinguish tests actually run from checks that could not be run.
6. Do not call a build successful based only on a workflow file or a source edit.

## VPN-specific caution

Connection state, user intent to connect, native service status, app lifecycle/background grace periods, and automatic recovery may interact. Before changing connection/recovery logic, map all related fields and call paths. Avoid “simplifying” state logic without understanding its invariants and notification-driven stop behavior.

## CI/release caution

- `.github/workflows/build.yml` runs on pushes to `main`.
- It uses repository Actions secrets for signing; never print, copy, or commit secret values.
- Test changes on a non-main branch. A PR may be used for review, but merging it can trigger a release workflow.
- Explicitly tell the user if a proposed change could alter release behavior.

## Documentation discipline

- Record snapshot date and source branch/commit when updating project maps.
- Separate verified facts, user-provided product context, assumptions, and unresolved questions.
- Update `DEVELOPMENT_LOG.md` for meaningful completed changes.
- Keep sensitive values, tokens, credentials, private keys, and production configuration out of Git.
