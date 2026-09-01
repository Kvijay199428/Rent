# Deployment Gate, Order, Honesty & Final Report

This reference is part of the **testing-audit-debugging-protocol** skill. Load it when finalizing the audit.

---

## 1. Required Testing Order

Follow this sequence unless there is a strong technical reason not to:

1. Understand architecture
2. Inspect project structure (including any project-local skills/tooling)
3. Establish baseline
4. Run existing tests
5. Build/type/lint validation
6. Smoke test
7. Critical-path testing
8. Functional testing
9. API testing
10. Integration testing
11. Database/data-integrity testing
12. Negative testing
13. Boundary testing
14. Authorization/security testing
15. Reliability testing
16. Performance testing where applicable
17. Exploratory testing
18. Regression testing
19. Audit findings
20. Select skill(s)/tool(s) for each proposed fix, with recorded criteria
21. Create/update audit documents (including `skill-usage-log.md` and, if relevant, `skill-mapping.md`)
22. Report issues
23. Request approval before edits and before any change-making skill/tool use
24. Apply approved fixes with the approved skill(s)/tool(s) only
25. Re-test
26. Run regression
27. Final deployment gate

---

## 2. Testing Documentation Must Remain Honest

Never:

* mark an untested feature as PASS
* mark a failed test as PASS
* remove failures to make the report clean
* delete evidence of previous failures
* hide known issues
* claim a fix was tested when it was not
* claim production readiness without satisfying the deployment gate
* claim a skill/tool was used when it wasn't, or omit a skill/tool that was actually used to produce a finding or a fix

The audit log is an evidence record, not a presentation document.

Failed tests are valuable information and must remain visible. So is the true record of which instrument produced which piece of evidence.

The `.audit/memory/` stores and this gate together make the whole audit replayable — see `references/audit-replay.md` and `references/evidence-and-traceability.md`. A claim in the final report must be traceable to a recorded finding → evidence → execution record, or it is not supported.

---

## 3. Final Deliverables

At the end of the testing phase, ensure these exist:

```text
test-audit-task.md
audit-plan.md
audit-log.md
bucket-list.md
skill-usage-log.md
skill-mapping.md   (only if a mapping was declared or ambiguity required one)
```

The documents must agree with each other.

`test-audit-task.md`
→ What was tested.

`audit-plan.md`
→ How it was tested, and the skill usage policy (if any).

`audit-log.md`
→ What actually happened, cross-referenced to which tool/skill produced each finding.

`bucket-list.md`
→ Which files/components may require changes and why.

`skill-usage-log.md`
→ Which skills/tools were considered and used, when, and why — the full selection-criteria record.

`skill-mapping.md`
→ The user's declared (or confirmed) policy for which skill/tool handles which kind of analysis or fix, if one exists.

---

## 4. Final Deployment Gate

Do not recommend deployment merely because tests pass.

Before final deployment verify:

* no P0 issues
* no unresolved P1 issues unless explicitly accepted
* critical workflows pass
* authentication works
* authorization works
* database integrity verified
* migrations verified
* production build succeeds
* environment configuration verified
* critical API endpoints verified
* error handling verified
* regression suite passes
* known limitations documented
* every change-making skill/tool use during the audit was approved before it ran, and is recorded in `skill-usage-log.md` with its outcome

Clearly report:

```text
DEPLOYMENT STATUS:

READY
or
NOT READY

Reason:

Blocking Issues:

Non-Blocking Issues:

Tests Passed:

Tests Failed:

Tests Blocked:

Skills/Tools Used (investigation):

Skills/Tools Proposed/Used (fixes), with approval status:

Known Risks:

Required Approvals:

Recommended Next Action:
```

Never say "100% bug-free."

Instead state the actual level of verification performed.

---

## 5. Final Report

When testing is complete, do NOT immediately edit discovered issues. Give a concise final report containing:

1. Overall test status
2. Tests executed
3. Tests passed
4. Tests failed
5. Tests blocked
6. Issues discovered
7. Severity of each issue
8. Reproduction status
9. Root cause
10. Affected files
11. Proposed fixes
12. Files that would be modified
13. Skills/tools used during investigation, and skills/tools proposed for fixes, each with its one-line selection criteria
14. Regression tests required
15. Deployment readiness
16. Explicit approval requests (code changes and skill/tool invocations)

For every issue requiring implementation changes, or requiring a change-making skill/tool, stop and ask for approval.

The default behavior is:

> **Observe first. Prove second. Document third. Select skills/tools fourth. Ask fifth. Edit only after approval.**
