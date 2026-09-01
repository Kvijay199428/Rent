# Root Cause, Severity & Approval — Investigating a Defect

This reference is part of the **testing-audit-debugging-protocol** skill. Load it when investigating a defect.

---

## 1. Root Cause Analysis

For every significant defect determine:

### Symptom

What the user sees.

### Trigger

What action causes it.

### Failure point

Where the system actually fails.

### Root cause

Why it fails.

### Impact

What functionality/data/users are affected.

### Scope

Whether other areas are likely affected.

### Proposed solution

The smallest safe change — and the smallest safe set of skills/tools needed to make it (see `references/skill-selection.md` and `references/approval-gates.md`).

### Regression risk

What could break because of the proposed change.

Do not confuse symptom with root cause.

Example:

Bad:

> "The button doesn't work."

Better:

> "The button sends a valid request, but the backend rejects `additionalPersons` because the validator expects an integer while the frontend serializes the value as a decimal string."

---

## 2. Severity Classification

Use consistent severity.

### P0 — Critical

Examples:

* data loss
* security breach
* application cannot start
* production deployment blocker
* corruption of critical records

### P1 — High

Examples:

* major feature unusable
* incorrect financial calculation
* authorization bypass
* important workflow broken

### P2 — Medium

Examples:

* significant edge case
* recoverable workflow problem
* incorrect non-critical behavior

### P3 — Low

Examples:

* cosmetic issue
* minor UX issue
* low-impact inconsistency

Do not classify everything as critical.

---

## 3. Separate Facts From Hypotheses

Clearly distinguish:

### CONFIRMED

Directly observed and reproduced (confidence HIGH or above).

### LIKELY

Strong evidence but not fully proven (confidence MEDIUM or above).

### SUSPECTED

Possible cause requiring further investigation (confidence LOW or above).

Never present a hypothesis as a confirmed root cause.

Findings are never asserted without a confidence label (see the confidence thresholds in SKILL.md, Section on Orchestration: INSUFFICIENT 0–49, LOW 50–69, MEDIUM 70–84, HIGH 85–94, VERY HIGH 95–100). A hypothesis below INSUFFICIENT is not reportable as a finding without more evidence.

---

## 4. Do Not Modify Tests to Hide Failures

If an existing test fails:

Do NOT immediately change the test.

First determine:

1. Is the application wrong?
2. Is the test wrong?
3. Has the intended behavior changed?
4. Is the environment incorrect?
5. Is the test flaky?

Only modify the test after determining why it is wrong and receiving approval when the change affects application behavior or expected requirements.

---

## 5. Avoid Scope Creep

If you discover unrelated problems:

Document them.

Do not fix them automatically. Do not reach for another skill/tool to fix them automatically either.

Add them to the audit log and, where appropriate, the bucket list.

Example:

> "During receipt testing, an unrelated authentication timeout issue was discovered. It is outside the current audit scope. No implementation changes were made, and no skill/tool was invoked against it."

---

## 6. Change Approval Protocol

When a defect is found, stop before implementation and report the canonical block defined in the master SKILL.md:

* Issue ID
* Severity
* Affected Feature
* Affected Files
* Observed Behavior
* Expected Behavior
* Reproduction Steps
* **Evidence (with producer skill/tool + evidence-graph ref)** — see `references/evidence-and-traceability.md`
* Root Cause / Suspected Root Cause
* Impact
* Proposed Fix
* Files I intend to modify
* Why these files need modification
* **Skill/Tool Selection** — skill(s)/tool(s) proposed, selection criteria, source (global/project-local/built-in), scope, alternatives considered, and the `skill-usage-log.md` / execution-record reference (see `references/skill-selection.md` and `references/approval-gates.md`)
* Potential Regression Risk
* Tests I will run after the fix
* **ANALYSIS APPROVAL REQUIRED (GATE 1)**, then **CODE MODIFICATION APPROVAL REQUIRED (GATE 2)** — see `references/approval-gates.md`

Wait for explicit approval at each gate (e.g., "fix it", "proceed"). The Gate‑1 approval covers the analysis and fix plan only; the Gate‑2 approval covers exactly the files and the skill(s)/tool(s) named in the block — not a substitute skill/tool discovered afterward, which needs its own Gate‑2 approval.

Require a "change budget": *"I will modify these N files and no others, using these skill(s)/tool(s) and no others."* If investigation later reveals another file, skill, or tool is required, stop and ask again.

---

## 7. Minimal Change Principle

Once approval is received:

* modify only necessary files
* make the smallest safe change
* use only the approved skill(s)/tool(s), in the approved scope
* avoid unrelated refactoring
* do not change APIs unnecessarily
* do not change database schema unnecessarily
* do not upgrade dependencies unnecessarily
* do not rewrite working code without reason
* do not chain in an additional skill/tool "while you're at it"

After editing, report exactly what changed, and update `skill-usage-log.md` with the outcome of any skill/tool that was invoked.

---

## 8. Post-Fix Verification

For every approved fix:

### A. Targeted test

Verify the exact defect.

### B. Unit test

Where applicable.

### C. Integration test

Verify affected integration.

### D. Regression test

Verify related functionality.

### E. Full relevant test suite

Verify broader behavior.

### F. Build

Verify production build.

### G. Final manual verification

Repeat the original user workflow.

Record which tool/skill ran each of these in `skill-usage-log.md`, cross-referenced to the issue ID.

---

## 9. Regression Testing

Every discovered bug should eventually have a regression test where practical.

The regression sequence should be:

1. Reproduce original bug.
2. Document it.
3. Identify the right skill(s)/tool(s), and obtain approval for both the fix and their use.
4. Apply fix.
5. Run targeted regression test.
6. Run related tests.
7. Run broader regression suite.
8. Re-test the original reproduction scenario.
9. Verify that unrelated functionality was not broken.

Never declare a bug fixed simply because the changed line looks correct.
