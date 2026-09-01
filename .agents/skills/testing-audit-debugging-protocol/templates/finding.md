# Finding Record Template

Use this template for every finding. Keep it in sync with `.audit/memory/findings.jsonl` (schema: `finding.schema.json`) and `audit-log.md`.

```
FINDING: F-###

Severity: <P0 | P1 | P2 | P3>
Confidence: <INSUFFICIENT | LOW | MEDIUM | HIGH | VERY HIGH>
Root cause status: <CONFIRMED | LIKELY | SUSPECTED>

Observed: <what actually happened>
Expected: <what should have happened>

Reproduction steps:
1. ...
2. ...

Evidence: [E-###, E-###]  (each must trace to a producer execution record)

Affected files: [path/to/file1.ts, path/to/file2.tsx]

Cluster: <CL-### or null>

Status: <OPEN | APPROVED | FIXED | VERIFIED | REJECTED | WONT-FIX>

Gate 1 approved: <y/n>
Gate 2 approved: <y/n>

Timestamp: <ISO 8601>
```

A finding without at least one evidence reference (`E-###`) is `INSUFFICIENT` confidence and must not be reported as confirmed.