# Audit log

`.smoke-test/audit.jsonl` — append-only, one JSON object per line, never rewritten or truncated.

## Action categories

```
DISCOVER            — scanning the project structure
READ                 — reading a file
SEARCH               — regex/grep scan
RUN                  — running a command (test runner, build, existing scripts)
HTTP                 — an HTTP request made during a check
DATABASE_READ        — a read-only DB query
CREATE_ARTIFACT       — creating a file under .smoke-test/
UPDATE_STATE          — updating smoke-state.json / smoke-todo.json
PROPOSE_CHANGE         — opening a change request
REQUEST_APPROVAL        — asking the user for a decision
APPROVAL_GRANTED         — the user said yes to a specific change request
APPROVAL_DENIED           — the user said no to a specific change request
MODIFY                     — an approved change applied outside .smoke-test/ (requires a prior APPROVAL_GRANTED line for the same change_request_id)
DELETE                      — a file deletion outside .smoke-test/ (requires a prior APPROVAL_GRANTED line for the same change_request_id)
```

`MODIFY` and `DELETE` must never appear in the log without a preceding `REQUEST_APPROVAL` **and** `APPROVAL_GRANTED` line for that same `change_request_id`. If you're ever about to write a `MODIFY`/`DELETE` line without that pair already present earlier in the file, stop — that's not a valid state, go get approval first.

## Line shape

```json
{"time":"2026-09-17T08:01:12+05:30","action":"HTTP","target":"GET /health","result":"200"}
{"time":"2026-09-17T08:01:15+05:30","action":"RUN","target":"pytest tests/smoke","result":"exit 0"}
{"time":"2026-09-17T08:02:00+05:30","action":"CREATE_ARTIFACT","target":".smoke-test/reports/latest.md"}
{"time":"2026-09-17T08:05:00+05:30","action":"PROPOSE_CHANGE","target":"backend/services/billing_service.py","change_request_id":"CR-004"}
{"time":"2026-09-17T08:05:01+05:30","action":"REQUEST_APPROVAL","change_request_id":"CR-004"}
{"time":"2026-09-17T08:07:30+05:30","action":"APPROVAL_GRANTED","change_request_id":"CR-004"}
{"time":"2026-09-17T08:07:45+05:30","action":"MODIFY","target":"backend/services/billing_service.py","change_request_id":"CR-004"}
```

## When to write an audit line

Every discrete action in the run, not just the interesting ones — the point is that the log is a complete, honest trace someone could replay to understand exactly what happened, including all the boring passing checks. Append as you go, not as a batch at the end (so a crashed run still leaves a partial, truthful trail).
