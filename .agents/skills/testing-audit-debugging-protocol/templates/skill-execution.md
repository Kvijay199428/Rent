# Skill Execution Record Template

Use this template for every skill invocation. Keep it in sync with `.audit/memory/skill-usage.jsonl` (schema: `skill-execution.schema.json`).

```
EXECUTION: SU-###

Selection: SS-###
Skill: <name>
Source: <global skill | project-local skill | project tool | built-in tool | connector>
Type: <read-only | change-making>
Approval gate: <none | Gate 1 | Gate 2>
Scope: <what this invocation covers, e.g. "read receipt calculation file", "apply fix to file3.ts">

Inputs:
{ "file": "path/to/file.ts", "args": [...] }

Outputs:
{ "result": "...", "findings": ["F-###"] }

Evidence produced: [E-###, E-###]

Outcome: <success | error | inconclusive>
Error details: <if any>

Duration: ### ms
Timestamp: <ISO 8601>
```

Append a row to `skill-usage-log.md` (markdown) and a JSONL line to `.audit/memory/skill-usage.jsonl`.