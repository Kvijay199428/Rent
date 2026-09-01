# Dual Approval Gates

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever a finding requires a change and you must present the approval request.

The original skill used a single "fix it" gate. The orchestrator splits it into **two explicit gates** so the user can approve *the analysis/plan* separately from *applying the change*.

---

## 1. The Two Gates

### GATE 1 — Analysis Approval ("plan before action")
Present the `ANALYSIS` block: root cause, confidence, proposed fix, affected files, skill/tool selections with `WHY THIS SKILL?`, change budget, regression risk. Ask: *"Is this analysis and fix plan approved?"* **No code changes.**

Approving Gate 1 authorizes the **conclusions and the fix plan only** — not the execution of any edit.

### GATE 2 — Code Modification Approval ("act on the approved plan")
Present the `CODE MODIFICATION` block: the exact files to modify, the change-making skill(s)/tool(s) to invoke (with execution record references), and the change budget. Ask: *"May I apply this change?"* This authorizes **exactly** the named files and change-making skill(s)/tool(s).

---

## 2. Approval Semantics

* "proceed / fix it / yes, apply" after a Gate‑1 block authorizes the **analysis and plan only**. A separate explicit authorization is required to modify code.
* The user may grant **combined** approval ("audit and fix it", or a pre-granted "go ahead and fix") that covers both gates at once — but both gates must still be recorded.
* Approval covers **exactly** the files and skills/tools named. A different file or a different skill/tool discovered later needs its own Gate‑2 approval.
* If investigation reveals an extra file/skill/tool is required, stop and ask again (change budget).
* A "change budget" accompanies every proposed change: *"I will modify these N files and no others, using these M skill(s)/tool(s) and no others."*

---

## 3. Canonical Blocks

### Gate 1 block

```text
ANALYSIS

Issue ID:
Severity:
Confidence (of root cause):
Affected Feature:
Affected Files:
Observed Behavior:
Expected Behavior:
Reproduction Steps:
Evidence (with producer skill/tool + evidence-graph ref):
Root Cause / Suspected Root Cause:
Impact:
Proposed Fix:
Files I intend to modify (change budget: N files, no others):
Skill/Tool Selection (for the fix):
  Skill(s)/Tool(s) proposed:
  WHY THIS SKILL?:
  WHY NOT <altX>?:   (per rejected alternative)
  Selection mode:
  Source:
  Scope of invocation:
  Execution record (will log as):   SU-###
  Reputation:  Low / Medium / High / Trusted
Potential Regression Risk:
Tests I will run after the fix:

ANALYSIS APPROVAL REQUIRED  (GATE 1)
```

### Gate 2 block

```text
CODE MODIFICATION

Issue ID:
Approved by Analysis Gate 1:   (id / confirmation)
Files I will modify now (exactly these N, no others):
  - <path>  (reason)
Change-making skill(s)/tool(s) I will invoke now (exactly these M, no others):
  - <capability>  (execution record SU-###, approval scope)
Change budget:  "I will modify these N files and no others, using these M
skill(s)/tool(s) and no others."

CODE MODIFICATION APPROVAL REQUIRED  (GATE 2)
```

If no skill/tool beyond direct editing is needed, write "None — direct edit only."

See `templates/approval.md` and `schemas/approval.schema.json`.

---

## 4. Recording Approvals

Each gate approval/decision is recorded as an `approval` record (schema `approval.schema.json`) with fields: `gate` (1 or 2), `finding_id`, `decision` (granted / declined / pending / combined), `granted_by` (user), `scope` (files + skills/tools authorized), `timestamp`, and the change budget. The audit trail of what was approved and what actually changed is thus complete and replayable.

---

## 5. Rules

* Both gates are explicit and separate; record both even on combined approval.
* Never modify code or run a change-making skill/tool without a recorded Gate‑2 approval.
* Never let Gate‑1 approval authorize a change; never let Gate‑2 approval authorize an unlisted file/skill/tool.
* If a change is declined, record it and stop; do not retry a declined change without new user direction.
