# Script Plan Template

Use this any time a nested skill (or the orchestrator itself) proposes creating a diagnostic/throwaway script. Creating a script is a mutation — it needs Gate 2 in addition to appearing in the Nested Skill Execution Plan.

```
SCRIPT: SC-###

Path:             scripts/<name>
Purpose:          <what it does>
Reason:           <why existing tooling/tests can't answer this>
Input:            <what it consumes>
Expected output:  <what it produces>
Created by:       <nested skill id, or "orchestrator">
Mutation:         Creates a new diagnostic script.
Approval:         Gate 2 required
Lifecycle:        PROPOSED
```

Append a JSONL record to `.audit/memory/script-plans.jsonl` per `schemas/script-plan.schema.json`. Update `Lifecycle` as it progresses: `PROPOSED → JUSTIFIED → APPROVED → CREATED → EXECUTED → EVIDENCE_CAPTURED → RETAINED | REMOVED`. If removed, record why and what replaced it:

```
SC-###
Status: REMOVED
Reason: <e.g. "temporary diagnostic script; converted into a permanent regression test">
Replacement: <e.g. tests/authentication-regression.test.ts>
```
