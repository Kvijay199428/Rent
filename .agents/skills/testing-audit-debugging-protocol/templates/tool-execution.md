# Tool Execution Record Template

Use this template for every tool invocation (project test runner, linter, build, shell, connector, etc.). Keep it in sync with `.audit/memory/tool-usage.jsonl` (schema: `tool-execution.schema.json`) and mirror into `skill-usage-log.md`.

```
EXECUTION: TU-###

Tool: <name>
Call type: <command | script | connector | api>
Type: <read-only | change-making>
Approval gate: <none | Gate 1 | Gate 2>
Command: <exact command or API call>

Inputs:
{ "args": [...], "env": {...} }

Outputs:
{ "stdout": "...", "stderr": "...", "exit_code": 0, "files": ["path/to/file.ts"] }

Evidence produced: [E-###, E-###]

Outcome: <success | error | inconclusive>
Error details: <if any>

Duration: ### ms
Timestamp: <ISO 8601>
```

Append a row to `skill-usage-log.md` and a JSONL line to `.audit/memory/tool-usage.jsonl`.