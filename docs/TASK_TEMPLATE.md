# JET VPN — Task Template

Use this template for every non-trivial engineering task. Keep the task scoped and preserve the completed record in the PR description or development log.

## 1. Goal and priority

- **Requested outcome:**
- **Collaborator-priority test:** Does this make the assistant a more independent, accurate, project-memory-aware programming collaborator? **Yes / No**
- **Capability improved:** project understanding / source navigation / implementation / verification / durable memory / safe maintenance
- **Why this is the highest-value next step:**

## 2. Context loaded

- [ ] `AGENTS.md`
- [ ] `docs/PROJECT_CONTEXT.md`
- [ ] `docs/CURRENT_STATUS.md`
- [ ] `docs/NEXT_STEPS.md`
- [ ] Relevant `docs/DEVELOPMENT_LOG.md` entries
- [ ] Relevant architecture/API/data/payment/issue/decision/test docs
- [ ] Current source re-fetched and checked against the target SHA

## 3. Baseline

- **Repository:**
- **Target branch:**
- **Base commit SHA:**
- **App version:**
- **Relevant source paths and symbols:**
- **Verified facts:**
- **Unknowns / assumptions:**

## 4. Scope and risk

- **Files expected to change:**
- **Files explicitly out of scope:**
- **Behavior/invariants to preserve:**
- **Risk level:** low / medium / high
- **Failure modes and rollback plan:**
- **Approval required before proceeding?**

## 5. Implementation

- **Working branch:**
- **Changes made:**
- **Complete diff reviewed:** yes / no
- **Unexpected files or side effects:** none / describe

## 6. Verification evidence

| Check | Exact command or workflow | Result |
|---|---|---|
| Format | | not run / passed / failed |
| Static analysis | | not run / passed / failed |
| Unit/regression tests | | not run / passed / failed |
| Build | | not run / passed / failed |
| Device/runtime test | | not run / passed / failed |
| Memory/index audit | | not run / passed / failed |

Distinguish static analysis, unit tests, build success, and real device/runtime evidence. Never treat one as a substitute for another.

## 7. Durable memory and handoff

- **Docs updated:** CURRENT_STATUS / NEXT_STEPS / DEVELOPMENT_LOG / other
- **Generated indexes/artifacts refreshed:**
- **PR link:**
- **CI run links and artifact IDs:**
- **Remaining risks and unknowns:**
- **Exact next action:**
- **User action required:** none / specify precisely

## 8. Approval boundary

- [ ] No direct commit to `main`
- [ ] No merge without explicit approval
- [ ] No production release/tag/deployment without explicit approval
- [ ] No production install/update until package ID and signing compatibility are verified
