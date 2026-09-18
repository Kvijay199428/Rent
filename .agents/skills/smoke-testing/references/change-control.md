# Change control

This is the protocol that fires whenever a smoke test finds a real defect and fixing it would mean touching Zone B (see `references/rules.md` §2).

## Root-cause analysis chain (do all of these before proposing anything)

```
Symptom              → what the check actually observed
Evidence             → the saved response/log/screenshot
Reproduce            → confirm it's not a fluke (re-run the check once)
Locate                → which file/config/table is implicated
Likely cause          → your best read-only-confirmed hypothesis
Confirm via read-only inspection → actually open the implicated file/schema, don't guess
Propose               → the exact change, nothing vaguer
```

Never skip from "500 error" straight to "I'll edit `billing_service.py`" — walk the chain and show your work in the change request.

## Change request shape

**Source of truth: `.smoke-test/smoke-state.json`'s `change_requests` array.** This is the one place a change request's full record lives across runs — `smoke-todo.json`'s failing item only carries a `change_request_id` pointer into it, and `reports/latest.json` mirrors the current run's open ones for convenience, but `latest.json` gets overwritten every run so it must never be the only copy of an unresolved request.

```json
{
  "change_request_id": "CR-004",
  "status": "approval_required",
  "linked_todo_id": "E2E-002",
  "files": ["backend/services/billing_service.py"],
  "problem": "POST /api/bills returns HTTP 500",
  "evidence": ".smoke-test/evidence/backend/E2E-002.txt",
  "root_cause": "Database schema is missing the tenant_id column the application code expects.",
  "proposed_change": "Add a migration that adds tenant_id to the bills table.",
  "why_required": "Without it, bill creation cannot succeed for any tenant.",
  "risk": "Schema migration on the active database — should run against a backup/staging copy first if one exists.",
  "validation_after_change": "Re-run E2E-002 and the full backend smoke suite.",
  "created_at": "2026-09-17T08:30:00+05:30",
  "resolved_at": null
}
```

## What you say to the user (always ask, in this shape)

```
I found the following defect.

Problem: <what failed>
Evidence: <where the proof is saved>
Root cause: <your finding, from the chain above>
Proposed change: <exact change>
Files affected: <list>
Why the change is required: <plain reasoning>
Risk: <what could go wrong / what you can't verify without touching Zone B>
Validation after change: <what you'll re-run to confirm it worked>

Shall I apply this change?
```

Then stop and wait. Do not continue implementing it in the same turn.

## Approval states

`approval_required` → `approval_granted` | `approval_denied` | `approval_expired` (if the project or context has moved on and you should re-ask rather than assume it's still valid)

## If approved

```
approval_granted
   → apply exactly the proposed change (no scope creep — if you notice something
     else worth fixing while you're in there, that's a NEW change request, not
     an addition to this one)
   → record the modified files in the audit log (action: MODIFY)
   → re-run the specific failing check
   → re-run the smoke items that depend on it
   → set resolved_at on the change request in smoke-state.json
   → update the report
```

## If declined

```
approval_denied
   → record the denial and reason (if given) on the change request, set resolved_at
   → create/keep a TODO item for it (don't lose the finding)
   → continue with whatever else in the suite doesn't depend on this fix
   → keep reporting it every run until it's resolved one way or the other
```

## Special case: destructive or production-adjacent changes

Migrations, deletions, and anything touching what might be production data get an extra explicit confirmation of environment ("this is the dev/staging database, correct?") before you even draft the change request — don't let "the user already said yes to the concept" cover "the user knows exactly which database this will run against."
