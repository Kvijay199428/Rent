# Questioning engine

The core idea: a regex match is not itself a question. It's a trigger that generates a question, which becomes a TODO item, which gets tested for real evidence.

```
Pattern match  →  Question template  →  TODO item  →  Real check  →  Evidence  →  PASS/FAIL/BLOCKED
```

## Question item shape

Each generated question becomes a TODO entry (see `references/state-management.md` for the full JSON schema):

```json
{
  "id": "BE-AUTH-001",
  "category": "backend",
  "pattern_source": "(?i)(/login|/auth/login|authenticate)",
  "question": "Can the authentication endpoint successfully authenticate a valid test account?",
  "severity": "critical",
  "status": "pending"
}
```

## Backend question bank

- Is the backend process running / does it accept connections?
- Does the health endpoint respond with a healthy status?
- Does the readiness endpoint confirm database connectivity?
- Are required migrations applied (schema matches what the code expects)?
- Can authentication succeed with a valid test account?
- Does an authenticated request to a protected endpoint return 2xx?
- Does an unauthenticated request to a protected endpoint return 401/403 (not 200, not 500)?
- Do the core CRUD endpoints for the app's primary resource respond?
- Does invalid/malformed input produce a controlled 4xx, not a 500?
- Does requesting a nonexistent resource return 404, not 500?
- Can the single most important business operation complete end-to-end (see discovery's route map for what that is)?

## Frontend question bank

- Does the application load at all (HTTP 200, no blank screen)?
- Does the root route render without a React/framework error?
- Do the other critical routes render without error, blank page, or unexpected redirect?
- Does the login form render with the expected fields and a submit control?
- Does the primary authenticated view (dashboard/home) render its key sections?
- Can the user interact with the primary form (type, select, submit) without it breaking?
- Does form submission trigger the expected API request (matches discovery's dependency map)?
- Are there uncaught console errors on load or on the primary interaction?
- Are there failed network requests (4xx/5xx or connection errors) on load or on the primary interaction?
- Does logout return the user to a logged-out state?

## Integration / full-stack question bank

- Can a user open the app, log in through the real UI, and reach the real backend?
- Does the backend authenticate the request and hit the real database?
- Does the core business operation (create/read the primary resource) succeed through the full stack?
- Does the result actually render in the UI (not just succeed server-side)?
- Does a page refresh preserve the expected session state?
- Does logout invalidate access (a subsequent protected request fails as expected)?
- Are there any unexpected console, network, or API errors during the whole flow?

## Turning the answer into a check, not just an assertion

Every question needs a concrete, executable check, not a guess:

```
Question: Can the authentication endpoint authenticate a valid test account?
Expected: HTTP 200 + a session/token in the response.
Check:    POST {base_url}/api/auth/login with the configured smoke-test
          credentials from smoke-config.json; inspect status + body.
Evidence: save raw request/response to
          .smoke-test/evidence/backend/BE-AUTH-001.txt
Result:   PASS / FAIL / BLOCKED (see references/reporting.md for the rule)
```

If `smoke-config.json` has no smoke-test credentials configured for a question that needs them, the item's status is `blocked` with reason "no smoke-test account configured" — ask the user for one rather than inventing credentials or trying real user accounts.

## Priority assignment

```
critical — health/readiness/auth/the single most important business operation
high     — core CRUD on the primary resource, main navigation routes
medium   — secondary routes, secondary error-handling checks
low      — cosmetic or rarely-hit paths
```

Run critical → high → medium → low, and stop escalating within a level if something critical fails (see `references/discovery.md` §Decision tree).

## Don't over-generate

Discovery might find 60 backend endpoints. Not all deserve a critical smoke check — pick health/readiness/auth plus the 1-3 endpoints that represent the app's actual core purpose (ask the user if it's not obvious from the domain, e.g. "bills" for a billing app). Everything else can be `medium`/`low` or left out of the smoke suite entirely and noted as "not covered by smoke — candidate for the regression suite."
