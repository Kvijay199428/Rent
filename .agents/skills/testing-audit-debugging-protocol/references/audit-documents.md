# Audit Documents — Understanding, Baseline & the Deliverables

This reference is part of the **testing-audit-debugging-protocol** skill. Load it when understanding the application and creating/maintaining the audit documents.

---

## 1. First Understand the Application

Before testing deeply, inspect the project structure.

Understand:

* frontend
* backend
* database
* API layer
* authentication/authorization
* storage
* background jobs
* external integrations
* configuration
* environment handling
* build system
* test infrastructure
* deployment configuration
* logging
* error handling
* generated files
* migrations
* seed data
* documentation
* **any project-local skills or declared tooling** (e.g. a `skills/`, `.agents/skills/`, or `.claude/skills/` directory, scripts declared in `package.json`/`Makefile`/CI config) — note these as candidates for later use; see `references/skill-discovery.md` and `references/capability-registry.md`

Do not immediately start changing things.

Build a mental model of how data flows through the application.

For every important feature, identify:

**UI → frontend logic → API → backend/service → database/storage → response → UI**

Where applicable also identify:

**authentication → authorization → validation → business logic → persistence → audit/logging**

---

## 2. Establish the Baseline

Before declaring something broken, establish the current baseline.

Run the existing:

* unit tests
* integration tests
* API tests
* frontend tests
* end-to-end tests
* type checking
* linting
* build
* migration validation
* relevant static analysis

Record:

* command executed
* environment
* result
* number of tests
* failures
* warnings
* build status
* duration where useful
* which tool or skill executed it (record an execution record in `skill-usage-log.md` — this is read-only/investigative, so no approval is needed, just a record; see `references/skill-discovery.md`) 

Do not assume existing tests are correct.

A passing test suite means:

> "The existing tests pass."

It does NOT automatically mean:

> "The application is bug-free."

---

## 3. Create the Audit Documents

After the initial testing phase, create and maintain these documents.

### `test-audit-task.md`

This is the master testing checklist.

It should contain:

* testing objectives
* application areas
* test categories
* test cases
* status
* severity
* evidence
* blockers
* regression requirements
* final deployment gate

Use statuses such as:

* NOT_STARTED
* IN_PROGRESS
* PASS
* FAIL
* BLOCKED
* NEEDS_REVIEW
* NOT_APPLICABLE

---

### `audit-plan.md`

This explains HOW the application will be audited.

Include:

### Scope

What is being tested.

### Out of Scope

What is intentionally not being tested.

### Risk Areas

Identify high-risk areas first.

Examples:

* authentication
* authorization
* financial calculations
* database writes
* destructive operations
* file uploads
* data integrity
* concurrency
* external APIs
* payment functionality
* tenant/user isolation
* permissions
* sensitive information

### Testing Strategy

Define:

* smoke testing
* functional testing
* integration testing
* API testing
* UI testing
* regression testing
* negative testing
* boundary testing
* security testing
* performance testing
* compatibility testing
* data integrity testing
* deployment verification

### Skill Usage Policy

If the user has stated (or you have inferred and confirmed) which skill or tool should be used for which kind of analysis or fix, record it here, or point to a dedicated `skill-mapping.md` (see below) if the mapping is non-trivial. If nothing has been declared, state that auto-selection per `references/skill-selection.md` will be used, and that multiple plausible options will be surfaced to the user rather than guessed.

### Exit Criteria

Define exactly when the application can be considered ready.

---

### `audit-log.md`

This is the chronological evidence log.

Every significant test or finding should be recorded.

Use a structure similar to:

| ID | Date | Area | Test | Expected | Actual | Result | Severity | Tool/Skill Used | Evidence |
| -- | ---- | ---- | ---- | -------- | ------ | ------ | -------- | ---------------- | -------- |

For failures include:

* reproduction steps
* input/data
* expected behavior
* actual behavior
* logs/errors
* affected component
* which tool or skill was used to reproduce/verify it (cross-reference the row ID in `skill-usage-log.md`)
* suspected root cause
* confidence level
* proposed fix
* approval status
* retest result

Do not write vague statements such as:

> "Something is wrong with the API."

Instead write:

> "POST /api/receipts returns HTTP 500 when `waterCharge` is omitted although the UI allows the field to be empty. Reproduced 4/4 times using the project's own API test runner (see skill-usage-log.md SU-003). Backend validation attempts numeric conversion before applying the default value."

---

## 4. Create `bucket-list.md`

This is the audit change inventory.

It must contain the files that MAY need to be touched during debugging/fixing — plus, for any fix that would use a skill or tool, the candidate capability and its change status. Each entry therefore carries: file path, reason, and (where relevant) the candidate capability and its modification status (`read-only considered` / `change-making proposed` / `needs approval`).

Do not treat this list as permission to edit.

Example:

```text
# Audit Bucket List

## Application Files

- path/to/file1.ts
  Reason: Receipt calculation logic

- path/to/file2.tsx
  Reason: Receipt edit modal

- path/to/file3.ts
  Reason: API validation
  Candidate capability: <project-local lint tool> — read-only considered

## Database

- path/to/migration.sql
  Reason: Possible schema issue
  Candidate capability: <migration tool> — change-making proposed, needs approval

## Tests

- path/to/file.test.ts
  Reason: Missing regression coverage

## Configuration

- path/to/config.ts
  Reason: Configuration behavior under investigation

## Skill/Tool Change Inventory  (capabilities proposed against the above)

- <capability>  → files: file3.ts
  WHY THIS SKILL?: ...
  Modification status: change-making proposed / needs approval
  Execution record (when used): SU-###
```

Each file must have a reason.

If a file is not relevant, do not add it merely because it is nearby.

---

## 5. Create `skill-usage-log.md`

The chronological record of every skill/tool considered or used during this audit — the "memory" of which instrument was used, when, for what, and why. This is documentation, so it may be created and appended to freely, without separate approval, including for read-only investigative uses.

Full schema, examples, and the read-only vs. change-making distinction are defined in `references/skill-selection.md`, `references/audit-memory.md`, and `references/tool-orchestration.md` — load them before creating or updating this document, and keep it in sync with `audit-log.md` and the `.audit/memory/` stores (cross-reference row IDs both ways).

---

## 6. Create `skill-mapping.md` (when relevant)

Create this file as soon as the user states a preference for which skill or tool should handle a given kind of analysis or fix, or as soon as more than one skill/tool plausibly fits the same kind of finding in this project. It is the durable policy that skill/tool selection defers to first, ahead of auto-selection.

Schema and an example are defined in `references/skill-selection.md`, Section 5. If the user never states a preference and no ambiguity arises, this file is not required — do not create it speculatively.
