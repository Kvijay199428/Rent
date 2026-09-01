# Approval Template — Dual Gates

## GATE 1 — ANALYSIS APPROVAL

```
ANALYSIS

Issue ID: F-###
Severity: <P0|P1|P2|P3>
Confidence: <INSUFFICIENT|LOW|MEDIUM|HIGH|VERY HIGH>
Affected Feature: <name>
Affected Files: [path/to/file1.ts, ...]
Observed Behavior: ...
Expected Behavior: ...
Reproduction Steps: ...
Evidence (with producer skill/tool + evidence-graph ref): E-### (SU-### / TU-###)
Root Cause / Suspected Root Cause: ...
Impact: ...
Proposed Fix: ...
Files I intend to modify (change budget: N files, no others):
  - path/to/file1.ts (reason)
Skill/Tool Selection (for the fix):
  Skill(s)/Tool(s) proposed: <name>
  WHY THIS SKILL?: ...
  WHY NOT <altX>?: ...
  Selection mode: <Automatic|User Directed|User Approved>
  Source: <global|project-local|built-in>
  Scope of invocation: <what it will do>
  Execution record (will log as): SU-###
  Reputation: <Low|Medium|High|Trusted>
Potential Regression Risk: ...
Tests I will run after the fix: ...

ANALYSIS APPROVAL REQUIRED (GATE 1)
```

## GATE 2 — CODE MODIFICATION APPROVAL

```
CODE MODIFICATION

Issue ID: F-###
Approved by Analysis Gate 1: <AP-### / confirmation>
Files I will modify now (exactly these N, no others):
  - path/to/file1.ts (reason)
Change-making skill(s)/tool(s) I will invoke now (exactly these M, no others):
  - <capability> (execution record SU-###, approval scope)
Change budget: "I will modify these N files and no others, using these M skill(s)/tool(s) and no others."

CODE MODIFICATION APPROVAL REQUIRED (GATE 2)
```

If no skill/tool beyond direct editing is needed:
```
Change-making skill(s)/tool(s): None — direct edit only.
```

Record each gate decision in `.audit/memory/` as JSON per `schemas/approval.schema.json` (AP-###). A "combined" approval covers both gates but both must be recorded.