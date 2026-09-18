# Backend question bank

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
- Can the single most important business operation complete end-to-end?
