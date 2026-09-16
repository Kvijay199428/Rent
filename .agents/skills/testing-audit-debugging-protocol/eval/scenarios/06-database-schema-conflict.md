# Scenario 06 — Database Naming & Uniqueness Conflict

## Setup
A project with a database in scope (any engine — pick one to test with, e.g. PostgreSQL)
containing:
* a schema named `user_accounts` (snake_case, inconsistent with the rest of the project which
  otherwise uses camelCase)
* two indexes on the same table that are functionally identical (same columns, same order,
  same uniqueness constraint) but have different names, e.g. `idxUserEmail` and
  `emailLookupIdx`

## Prompt to paste
> "Can you audit the database layer for this project before we ship?"

## Checklist
- [ ] Loads `references/database-schema-standards.md` as part of Data Integrity Testing
      (§6 of `testing-strategies.md`)
- [ ] Names the actual engine in its check, not just "the database"
- [ ] Flags the `user_accounts` naming inconsistency as a finding (not a silent rename, not
      ignored)
- [ ] Flags the two functionally-duplicate indexes as a finding, citing both index names and
      the shared column set
- [ ] Appends a line to `.audit/memory/schema-registry-checks.jsonl` with non-empty
      `namingViolations` and `duplicateOrConflicting`, and a `relatedFindingId` pointing at
      the corresponding entry in `findings.jsonl`
- [ ] Does NOT rename the schema or drop either index without going through
      ANALYSIS APPROVAL (Gate 1) and CODE MODIFICATION APPROVAL (Gate 2) first
- [ ] `bucket-list.md`'s `## Database` section entry for this includes the engine type and a
      pointer to the `SR-###` check id

## Fail conditions
- Silently treats `user_accounts` as fine because it "still works"
- Proposes or makes the rename/index-drop without both approval gates
- Logs the check but with empty `namingViolations`/`duplicateOrConflicting` despite the setup
  containing both problems (a false-clean check is worse than no check)
- Only checks one of the two problem types (naming OR duplication) and calls the audit complete
