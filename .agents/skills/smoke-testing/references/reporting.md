# Reporting

Always produce both a human-readable and a machine-readable report, and never overwrite history.

```
.smoke-test/reports/latest.md            (overwritten each run — always current)
.smoke-test/reports/latest.json          (overwritten each run — always current)
.smoke-test/reports/history/<run_id>.md  (never overwritten)
.smoke-test/reports/history/<run_id>.json
```

`run_id` format: `SMK-YYYYMMDD-HHMMSS`.

## Status vocabulary (use only these — see references/rules.md §6)

`PASS`, `FAIL`, `BLOCKED`, `SKIPPED`, `NOT_APPLICABLE`, `AWAITING_USER`, `WARNING`

## Failure classification (attach to every FAIL)

`ENVIRONMENT`, `CONFIGURATION`, `DEPENDENCY`, `DATABASE`, `BACKEND`, `FRONTEND`, `INTEGRATION`, `AUTHENTICATION`, `AUTHORIZATION`, `BUSINESS_LOGIC`, `NETWORK`, `DEPLOYMENT`, `BUILD`, `TEST_DATA`, `UNKNOWN`

`BUILD` covers a frontend/backend build or dev-server that fails to start at all (dependency drift, broken imports, missing build-time env vars) — distinct from `DEPENDENCY`, which is for a runtime dependency (DB, third-party API) being unreachable once the app is already running. These map directly to the `category` field in `assets/patterns/errors.json`.

## Markdown report template (`reports/latest.md`)

```markdown
# Smoke Test Report

## Execution
- Project: <name>
- Run ID: <SMK-YYYYMMDD-HHMMSS>
- Started / Finished: <timestamps>
- Mode: Read-only
- Skill version: <see smoke-config.json or skill frontmatter>

## Summary
| Area | Result |
|---|---|
| Backend | PASS/FAIL/BLOCKED |
| Frontend | PASS/FAIL/BLOCKED |
| Integration | PASS/FAIL/BLOCKED |
| Overall | PASS/FAIL/BLOCKED |

## Backend
### <ID> <Title>
<PASS/FAIL/BLOCKED>
Expected: ...
Actual: ...
Evidence: `evidence/backend/<ID>.txt`
(if FAIL) Category: <classification>

## Frontend
... same shape ...

## Integration / E2E
... same shape ...

## Root Cause (for each FAIL that needs one)
<symptom → evidence → likely cause, per references/change-control.md>

## Proposed Remediation (for each FAIL that needs a code/config/DB change)
Modification required: YES
Approval: AWAITING USER   ← or "approved" / "declined" once resolved

## Carried-forward results (not re-verified this run)
- <ID>: passed on <date>, watched files unchanged

## TODO
- [x] <ID> — passed
- [ ] <ID> — awaiting user approval (see Proposed Remediation)
- [~] <ID> — blocked (upstream failure)
```

## JSON report shape (`reports/latest.json`)

```json
{
  "run_id": "SMK-20260917-080000",
  "mode": "read_only",
  "summary": { "backend": "PASS", "frontend": "PASS", "integration": "FAIL", "overall": "FAIL" },
  "tests": [
    { "id": "BE-001", "status": "PASS", "duration_ms": 132 },
    { "id": "E2E-002", "status": "FAIL", "category": "DATABASE", "approval_required": true }
  ],
  "change_requests": [ { "id": "CR-001", "status": "approval_required" } ]
}
```

This is what any CI pipeline or automation should consume for its pass/fail gate — never make the CI gate depend on the Markdown file.

## Rules for writing the report

1. Report `BLOCKED` items as blocked, never as `FAIL` — say what blocked them (references/rules.md §6).
2. Every `PASS`/`FAIL` cites its evidence file path.
3. Carried-forward (not re-run) results are called out in their own section, not mixed silently into fresh results.
4. Any open change request is shown with its full "Proposed Remediation" block, even if this is the third run in a row it's been awaiting approval — don't drop it from the report just because it's not new.
5. Keep the summary table at the top; put the detail after so the user can stop reading early if the top line is all they need.
