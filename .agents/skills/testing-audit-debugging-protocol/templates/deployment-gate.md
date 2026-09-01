# Deployment Gate Template

Use this at the end of the audit to produce the final deployment status report.

```
DEPLOYMENT STATUS:

<READY | NOT READY>

Reason: <one line>

Blocking Issues:
- F-###: <title> (<severity>)
- ...

Non-Blocking Issues:
- F-###: <title> (<severity>)
- ...

Tests Passed:
- <test suite>: <count> passed
- ...

Tests Failed:
- <test suite>: <count> failed
- ...

Audit Trail Summary:
- Total findings: <count>
- P0: <count> (all fixed/verified: <y/n>)
- P1: <count> (all fixed/verified: <y/n>)
- P2: <count> (fixed/verified: <count>)
- P3: <count> (fixed/verified: <count>)

Approval Record:
- Gate 1 approvals: <count> granted, <count> declined
- Gate 2 approvals: <count> granted, <count> declined
- Every change-making invocation approved: <y/n>
- Every finding has evidence chain: <y/n>

Replay Verification:
- Audit replay walked: <y/n>
- No unapproved change-making found: <y/n>
- All regression suites pass: <y/n>

Known Limitations:
- ...

Timestamp: <ISO 8601>
```

This report should be the final artifact. Do not recommend deployment merely because tests pass — the gate criteria above must all be met.