# JET VPN — Task Execution Record

Use this template for every non-trivial code, tooling, architecture, CI, or project-maintenance task. It is a working record, not a form that must be fully populated for trivial questions. Mark irrelevant sections as `Not applicable` and explain why. Carry the completed record into the pull request description or append it to `docs/DEVELOPMENT_LOG.md`.

## 1. User goal and priority

- **Requested outcome:**
- **Priority test:** «آیا این کار ما را به داشتن یک همکار برنامه‌نویس مستقل، دقیق و دارای حافظه پروژه نزدیک‌تر می‌کند؟»
- **Answer and reason:**
- **Capability improved:** project understanding / source navigation / implementation / verification / durable memory / safe maintenance
- **Explicitly deferred or excluded work:**

## 2. Repository context loaded

- [ ] `AGENTS.md`
- [ ] `docs/PROJECT_CONTEXT.md`
- [ ] `docs/CURRENT_STATUS.md`
- [ ] `docs/NEXT_STEPS.md`
- [ ] Relevant `docs/DEVELOPMENT_LOG.md` entries
- [ ] Relevant architecture, API, storage, issue, decision, and test documents
- **Repository:**
- **Target base branch:**
- **Verified base commit SHA:**

## 3. Source-of-truth verification

- **Working branch and current head SHA:**
- **Relevant source paths and symbols:**
- **Verified source/blob SHAs:**
- **Callers, state, persistence, APIs, native boundaries, and workflows traced:**
- **Facts classified as verified / inferred / unknown:**

## 4. Plan before editing

- **Expected behavior or deliverable:**
- **Invariants that must remain true:**
- **Failure modes and edge cases:**
- **Intended files to change:**
- **Impact and risks:**
- **Assumptions and external dependencies:**
- **Why this is the smallest complete scope:**

## 5. Implementation record

- **Isolated branch:**
- **Commit(s):**
- **Changed files:**
- **Important implementation decisions:**
- **Unexpected findings or deviations from plan:**

## 6. Diff and verification

- [ ] Complete diff inspected
- [ ] Changed-file list matches intended scope
- [ ] Formatting checked where relevant
- [ ] Static analysis executed
- [ ] Automated tests executed
- [ ] Build executed where relevant
- [ ] Project-memory/index freshness checked where required
- [ ] Secrets and sensitive data excluded from logs and commits

| Check | Exact command or CI run | Result | Evidence / limitation |
|---|---|---|---|
| Format | | passed / failed / skipped / not run | |
| Analyze | | passed / failed / skipped / not run | |
| Tests | | passed / failed / skipped / not run | |
| Build | | passed / failed / skipped / not run | |
| Device/runtime | | passed / failed / skipped / not run | |
| Memory audit | | passed / failed / skipped / not run | |

Do not describe a skipped or unavailable check as passed. A successful build is not a device test; static analysis is not runtime verification.

## 7. Durable memory and review handoff

- **Documents updated:** CURRENT_STATUS / NEXT_STEPS / KNOWN_ISSUES / DECISIONS / DEVELOPMENT_LOG / other
- **Generated indexes or artifacts refreshed:**
- **Pull request URL and base branch:**
- **PR state:** draft / ready for review / closed / merged
- **Remaining risks and unverified behavior:**
- **Next action and its priority reason:**

## 8. Approval boundary

- [ ] No direct commit to `main`
- [ ] No merge performed without explicit user approval
- [ ] No production release, tag, or deployment triggered
- [ ] Any destructive, financial, or production action is separately authorized

**Final result:** What is now proven, what is only inferred, and what remains unverified?
