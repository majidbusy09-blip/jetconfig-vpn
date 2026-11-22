# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-23

- `main` HEAD: `abdff3a59b89419e869c98d7dbb4ac91512fe950`; PR #19 is merged.
- PR #16, #17, and #19 are merged. PR #18 is the documentation-memory refresh currently being updated.
- PR #19's final-head Project Memory Audit [#45065541236](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541236) and Non-production PR Validation [#45065541255](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45065541255) both succeeded.
- App version remains `2.4.5+284`; app source and production release workflow were not changed by PR #19.
- Active `main-protection` ruleset remains in force; no bypass or direct-main write.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution. Every task must pass the criterion in `AGENTS.md`.

## P0 — Complete and validate authoritative project memory

- Update every current-state reference from pre-PR-19 main to `abdff3a59b89419e869c98d7dbb4ac91512fe950`.
- Record PR #19 scope and exact successful CI evidence.
- Ensure the file map and test plan include the Android validation parity tool and its tests.
- Preserve superseded snapshots and append, rather than rewrite, development history.
- Run both required CI workflows on the final PR #18 head and inspect the complete diff.

## P1 — Design the task execution orchestrator

After the memory refresh is reviewed and merged, design (before implementing) a small, auditable task protocol that:
1. loads mandatory project context and a task template;
2. records target repository, branch, base SHA, source fingerprints and scope;
3. discovers relevant symbols and dependency/critical-path impact;
4. produces a risk and test plan before edits;
5. executes only on a dedicated branch;
6. runs exact checks and records pass/fail/not-run evidence;
7. reviews the full diff and unexpected paths;
8. updates durable memory and opens a PR;
9. leaves merge/release/deployment under explicit user approval.

Prefer extending existing semantic indexers, task template and workflows over building duplicate infrastructure.

## P2 — Cross-repository project memory

- Perform a read-only architecture and workflow inventory of `jetconfig-vpn-tv` and `hesabgar_man`.
- Establish repository-specific agent instructions and a shared project map only after verifying each repository's current source.
- Keep JET VPN Android as the primary development priority.

## Deferred by user

- Telegram bot, payment, backend and server changes: currently working; defer absent a concrete issue.
- Product features, marketing and visual redesigns: lower priority than collaborator reliability and verification.

## Approval and safety boundary

- Do not commit directly to `main`.
- Do not merge PRs without explicit user approval.
- Do not publish releases, create production tags, deploy, or dispatch the production workflow without explicit approval.
- Do not change app version, signing, production package identity, bot/payment/backend/server behavior as part of memory/orchestrator work.
