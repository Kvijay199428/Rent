# File Organization — One File Per Usage-Based Schema

This reference is part of the **database-schema-architect** skill. Load it during GENERATE
(`SKILL.md` step 7) whenever a proposal is being turned into actual `.sql` (or engine-equivalent)
files on disk.

## The rule

Every schema object created for a distinct usage/purpose — a table, a collection's schema
definition, a measurement, a vector index — gets **its own separate file**, named after that
object, rather than being appended into one large combined schema file. A table's own indexes
and constraints live in the same file as the table itself (they're part of that table's usage),
but a different table — even one created in the same session for a related feature — gets its
own file. This is what makes a specific schema findable later without reading through an
unrelated 500-line dump.

## Default location

```
<project root>/database/sql/
```

Use `database/sql/` as the default when the project has neither directory already. If the
project already has a `db/` directory in use for this purpose, follow that instead — check
before creating a new top-level directory that duplicates an existing convention:

* Existing `db/sql/`, `db/schema/`, or similar → use it.
* Existing `database/` (any subfolder pattern) → use it, adding `sql/` underneath if that
  specific subfolder doesn't exist yet.
* Neither exists → create `database/sql/` and say so in the proposal, so the choice is visible
  and not just made silently.
* If the project already uses a migration framework (Flyway, Alembic, golang-migrate, Prisma
  Migrate, Django migrations, etc.) with its **own** required file naming/location (e.g.
  `migrations/0001_create_users.sql`, timestamped filenames, framework-specific folders) —
  that tool's convention wins. Don't fight an existing migration tool's layout; this default
  only applies where no such tool already dictates structure.

## Naming and nesting

* **Single-schema project:** flat files, one per object —
  `database/sql/<objectName>.sql` (e.g. `database/sql/userAccounts.sql`).
* **Multi-schema project:** nest by schema so files with the same object name in different
  schemas don't collide on disk —
  `database/sql/<schemaName>/<objectName>.sql` (e.g. `database/sql/tradingSignals/orderHistory.sql`).
* File name matches the object's camelCase name from `references/naming-conventions.md`, plus
  `.sql` — keep the file name and the actual object name identical so a search for one always
  finds the other.
* Non-relational engines that don't emit literal `.sql` (e.g. a MongoDB schema-validation
  document, a vector index definition): still use the `.sql`-parallel directory
  (`database/sql/` is a project-wide convention name, not a literal SQL-only rule) and give the
  file the engine-appropriate extension instead — `.js`/`.json` for a Mongo validator, whatever
  the vector engine's client library expects for an index definition. Note the extension choice
  in the proposal so it's not a surprise.

## File content

Each file starts with a short header comment recording where it came from, then the DDL itself:

```sql
-- Proposal: DP-014
-- Schema: tradingSignals   Object: orderHistory (table)
-- Purpose: filled orders for the backtesting engine
-- Naming check: clean   Conflict check: clean
-- Created: 2026-09-08

CREATE TABLE "tradingSignals"."orderHistory" (
    ...
);

CREATE INDEX "idxOrderHistorySymbolCreatedAt"
    ON "tradingSignals"."orderHistory" ("symbol", "createdAt");
```

The header isn't decorative — it's how someone opening the file six months from now sees why it
exists without having to cross-reference `design-log.md` first, though that file remains the
fuller record.

## Registering the file path

Once a file is written, its path is part of that object's entry in
`.dbdesign/registry/schema-registry.json` (the `filePath` field — see
`schemas/schema-registry.schema.json`) and in the proposal record
(`schemas/table-design-proposal.schema.json`). This is what makes the registry double as an
index of "where is the schema for X defined" — not just "does X exist."

## What NOT to do

* Don't combine multiple unrelated tables/collections into one "schema.sql" dump file for
  convenience — that's exactly the lack of distinction this convention exists to avoid.
* Don't scatter one table's indexes into a separate file from its `CREATE TABLE` — the table and
  its own indexes are one usage-based unit and stay together.
* Don't silently pick a different base directory than what the project already uses; if
  uncertain which existing convention applies, ask rather than guessing.
