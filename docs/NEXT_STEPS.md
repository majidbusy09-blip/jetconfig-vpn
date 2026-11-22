# JET VPN — Prioritized Next Steps

## Latest verified state — 2026-11-22

- `main` HEAD: `eae477a89816a5cfd475c596e166d5cb2575884a`.
- PR #16 merged at `c4f7f4743b3c6ffc64d34a0efb0c19f41b236f1e`.
- PR #17 merged at `eae477a89816a5cfd475c596e166d5cb2575884a`.
- Post-merge project-memory audit [#45029689706](https://github.com/majidbusy09-blip/jetconfig-vpn/actions/runs/45029689706) passed on the current main SHA.
- Active `main-protection` ruleset verified through GitHub API. It requires PRs and the memory-audit status check, blocks deletion and force pushes, allows Squash only, and has an empty bypass list.
- App version remains `2.4.5+284`; no production release or deployment was performed.

Priority is measured against the goal of a reliable, independent programming collaborator with durable project memory and safe execution. Every task must pass the criterion in `AGENTS.md`.

## P0 — Repair authoritative project memory

- Refresh stale current-state snapshots after PR #16 and #17.
- Keep current branch/commit, app version, source blob fingerprints, active ruleset and latest CI evidence synchronized.
- Preserve historical decisions and work logs; do not rewrite history as if older statements were never true.
- Add a memory-consistency check where practical so a merged PR cannot leave the top-level operational snapshot contradicting GitHub's actual state.

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
