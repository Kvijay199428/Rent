# Rules (non-negotiable)

These override convenience, speed, and "I already know the fix" every time.

## 1. No codebase modification without approval

Never edit, delete, rename, or move a file outside `.smoke-test/` without an explicit, per-change "yes" from the user in this conversation. This includes files that look trivial (a typo in a log message, a missing `.env` var, an off-by-one in a route). If the fix requires touching it, it goes through `references/change-control.md`, not directly.

## 2. Two permission zones

**Zone A — `.smoke-test/` (this project's smoke-test state directory).** Freely create, update, and append here. This is the skill's own workspace: config, state, TODO, reports, evidence, patterns, questions, audit log.

**Zone B — everything else in the project.** Read-only. `grep`/regex scanning, running the project's own pre-existing test/lint commands, and HTTP/API calls against a running dev or test instance are fine (they don't mutate source). Actually changing a Zone B file requires an approved change request.

## 3. Silence is not approval

Never write "I'll proceed unless you object" or act after a period with no reply. If a change needs approval and you don't have it yet, its TODO status is `awaiting_user` and you move on to other items. State this plainly in the report.

## 4. Don't infer approval from a previous approval

Approving change request CR-004 does not pre-approve CR-005, even if CR-005 looks similar or safer. Each change request is its own ask.

## 5. Never mutate data you don't own

Before any write-type check (create/update/delete via the API), confirm `smoke-config.json` has `test_environment.allow_writes: true` AND the operation targets a resource explicitly flagged as a smoke-test fixture (a dedicated test tenant/user/record, named with a recognizable prefix like `SMOKE_TEST_`). If either condition isn't met, the check is `SKIPPED` with reason "would require unapproved write", not silently attempted.

Never run anything against what looks like a production URL/database unless the user has explicitly confirmed that's intended and that writes are safe there.

## 6. FAIL vs BLOCKED are different things — don't conflate them

- `FAIL`: the check ran and the result was wrong.
- `BLOCKED`: the check couldn't meaningfully run because something upstream failed or approval is pending.

Marking a blocked test as `FAIL` (or vice versa) misleads whoever reads the report. See `references/reporting.md`.

## 7. Evidence or it didn't happen

Every `PASS`/`FAIL` needs a saved evidence file under `.smoke-test/evidence/<area>/<id>.txt` (raw response, status code, console log excerpt, screenshot path, etc.), referenced from the report. Don't assert a result you didn't capture.

## 8. Root-cause before proposing a fix

Follow the chain in `references/change-control.md` §Root-cause analysis: symptom → evidence → reproduce → locate → likely cause → confirm via read-only inspection → propose. Don't jump straight from "500 error" to "I'll edit the service file."

## 9. Smoke tests stay shallow

Don't let a smoke-testing run turn into a full regression suite. Cover critical paths only (see SKILL.md's Levels 0-4). If you find yourself writing the 30th edge-case check, stop — that belongs in `integration/` or `regression/`, not `.smoke-test/`.

## 10. State survives across runs — don't restart from zero

Always load `smoke-state.json` and `smoke-todo.json` before doing anything else. A `passed` item from a prior run whose watched files haven't changed (per fingerprint) does not need to be re-executed, but say in the report that it was "carried forward, not re-verified this run" rather than silently re-claiming a fresh PASS.
