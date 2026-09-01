# Testing Strategies — Executing the Audit

This reference is part of the **testing-audit-debugging-protocol** skill. Load it when executing tests.

---

## 1. Test Using the Professional Test Pyramid

Do not rely exclusively on end-to-end testing.

Use multiple levels.

### Level 1 — Static Validation

Check:

* syntax
* type errors
* lint
* imports
* dead references
* obvious unsafe patterns
* build configuration

---

### Level 2 — Unit Testing

Test isolated business logic.

Focus particularly on:

* calculations
* transformations
* validators
* parsers
* state transitions
* utility functions
* permission checks

Test:

### Normal cases

Valid expected inputs.

### Boundary cases

Examples:

* 0
* 1
* maximum allowed value
* minimum allowed value
* empty string
* null
* undefined
* negative values
* decimals
* very large numbers

### Invalid cases

Malformed or unsupported input.

### Combination cases

Multiple optional fields interacting with each other.

---

## 2. Integration Testing

Verify components working together.

Test:

* frontend → API
* API → service
* service → database
* authentication → authorization
* file upload → storage
* database → API response
* API → frontend rendering

Do not assume that individually passing components will work correctly together.

---

## 3. API Testing

For every important endpoint test:

### Happy path

Valid request.

### Missing fields

Required field omitted.

### Invalid types

String instead of number, etc.

### Null values

Explicit null.

### Empty values

Empty string/list/object.

### Boundary values

Minimum/maximum.

### Unauthorized request

No authentication.

### Authenticated but unauthorized request

Valid user with insufficient permissions.

### Wrong resource ownership

Attempt to access another user's/resource's data.

### Duplicate request

Send the same request repeatedly.

### Malformed request

Invalid JSON or unsupported structure.

### Unexpected additional fields

Ensure server-side validation behaves correctly.

### Concurrency

Where relevant, send simultaneous requests.

Record the actual HTTP status and response.

---

## 4. UI Testing

For every important screen verify:

* initial loading
* loading state
* empty state
* success state
* error state
* validation errors
* disabled controls
* keyboard interaction
* form submission
* cancel behavior
* navigation
* back navigation
* refresh behavior
* duplicate submission
* stale data
* responsive layout
* long text
* missing data
* large numbers
* slow network
* failed API
* session expiration

Do not test only the ideal user journey.

---

## 5. Negative Testing

Actively try to make the application fail.

Examples:

* invalid input
* missing input
* unexpected input
* extremely large input
* zero
* negative numbers
* duplicate submission
* expired session
* revoked permission
* deleted resource
* stale page
* interrupted request
* network failure
* API failure
* database failure
* invalid ID
* nonexistent resource
* malformed URL
* direct access to protected routes

The objective is to determine whether the application fails **safely and predictably**.

---

## 6. Data Integrity Testing

This is especially important for applications containing persistent business data.

Verify:

* database values
* API values
* displayed values
* calculated values
* stored values
* edited values
* deleted values
* relationships
* foreign keys
* uniqueness
* nullability
* transaction behavior

After an operation, verify the database rather than trusting only the UI.

For example:

**UI says saved → API says success → database actually contains correct value**

All three should agree. (Differential verification.)

---

## 7. Security Testing

At minimum inspect:

* authentication
* authorization
* session handling
* access control
* IDOR/resource ownership
* input validation
* injection risks
* sensitive data exposure
* secrets in source code
* insecure configuration
* file upload handling
* path traversal
* unsafe redirects
* excessive permissions
* error message leakage
* logging of sensitive information

Do not exploit beyond what is necessary to safely demonstrate the issue.

If a security issue is discovered:

**STOP before implementing a fix and request approval — including approval for any security-focused skill/tool you'd want to use to confirm or fix it.**

---

## 8. Performance Testing

Identify critical operations and measure:

* response time
* database query behavior
* repeated requests
* large datasets
* large payloads
* concurrent requests
* frontend rendering
* memory usage where measurable

Do not optimize based solely on assumptions.

First establish evidence.

---

## 9. Reliability Testing

Test failure scenarios:

* API unavailable
* database unavailable
* storage unavailable
* timeout
* partial response
* retry
* duplicate request
* interrupted request
* browser refresh
* application restart

The application should fail predictably and recover where designed to do so.

---

## 10. Exploratory Testing

After scripted testing, perform exploratory testing.

Do not blindly click around.

Choose a feature and deliberately vary:

* input
* order of actions
* timing
* navigation
* permissions
* state
* data volume
* browser refresh
* repeated actions

Look for unexpected state transitions.

---

## 11. Use Risk-Based Testing

Prioritize testing according to:

**Impact × Probability × Complexity × Change Surface**

Test the highest-risk functionality first.

Do not spend the majority of testing time on cosmetic details while critical business logic remains unverified.

---

## 12. Test Evidence Requirements

A test result should be reproducible.

Whenever possible capture:

* exact command
* exact input
* endpoint
* request
* response
* status code
* error
* log output
* database result
* screenshot if UI-related
* relevant file/line
* environment
* timestamp
* **which tool or skill produced this evidence** (project-local test runner, a global skill, a connector, etc.) — cross-reference the row in `skill-usage-log.md` (see `references/evidence-and-traceability.md`)

A statement such as:

> "It seems broken"

is not sufficient evidence.
