# Uniqueness & Conflict Checking

This reference is part of the **database-schema-architect** skill. Run this check **every
time**, before any schema, table/collection, or index is created or renamed — not just once at
the start of a project. It applies to every engine this skill covers.

## Why before, not after

This skill designs and builds, so the check happens *before* creation — catching a conflict
here means the conflict never ships. (Compare: an audit skill checking an existing database
finds conflicts that already happened. This skill's job is to make sure that never happens in
the first place.)

## The three layers

### a. Schema-level
Before creating a new schema/namespace/keyspace: confirm no existing schema in the same
database instance/cluster has the same name, comparing **case-insensitively even on
case-sensitive engines** — `userAccounts` and `useraccounts` are a collision worth flagging even
where the engine would technically allow both to exist.

### b. Table/collection-level
Before creating a new table/collection/measurement: confirm no other object in the *same*
schema has the same name (case-insensitive compare). A same-named table in a *different* schema
is not automatically a problem (e.g. per-tenant schemas each with a `users` table is often
intentional) — note it, don't block on it.

### c. Index-level
Before creating a new index: confirm both that
* no other index on the same table/collection has the same name, and
* no other index on the same table/collection is **functionally identical** — same
  columns/fields, same order, same uniqueness constraint. A functional duplicate under a
  different name is still a problem: it costs write throughput and storage for zero additional
  query benefit, and it should be flagged even when the names don't collide.

## How to run it

1. Read `.dbdesign/registry/schema-registry.json` (see `references/audit-record.md`). If it
   doesn't exist yet or looks stale relative to the live database, say so and offer to
   bootstrap/refresh it first — a check against a stale registry is worse than no check, since
   it gives false confidence.
2. Compare the proposed name(s) against every existing entry at the relevant layer.
3. Compare the proposed index's column set (in order) against every existing index on that
   table for a functional duplicate, not just a name match.
4. Record the result — clean or not — per `references/audit-record.md` §3, *before* moving on
   to generating DDL/migration code.

## What a conflict means

A caught conflict is not an error to hide or silently rename around — surface it in the
proposal (`templates/schema-design-proposal.md`) and let the user decide: rename the new object,
or confirm the collision is intentional (e.g. deliberately mirroring an existing name in a
different schema) and proceed anyway. Either way, the decision and its reasoning gets recorded,
not just the final name.
