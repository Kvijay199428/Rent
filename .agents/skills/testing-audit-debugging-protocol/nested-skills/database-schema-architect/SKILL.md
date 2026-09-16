---
name: database-schema-architect
description: Use this skill whenever a backend developer is designing or modifying a database — creating schemas, tables, columns, indexes, or writing queries against them — on SQLite, PostgreSQL, MySQL/MariaDB, CockroachDB, MongoDB, a time-series engine (InfluxDB, TimescaleDB, ...), a vector engine (Pinecone, Milvus, Weaviate, Qdrant, pgvector, ...), or any other database. Trigger on requests like "create a table for X", "design a schema for Y", "add an index on Z", "what columns should this collection have", "write a query to find...", "add a migration", or "review this schema before we ship it." Enforces camelCase naming by default, a mandatory uniqueness/conflict check before any schema/table/index is created, and a persistent audit record of every schema/table/index in the project so every subsequent design decision and query is made against ground truth, not assumption.
---

# Database Schema Architect

A design-and-build skill for database work: schemas, tables, columns, indexes, and queries.
It is engine-agnostic — relational, document, time-series, vector, key-value, graph — and
applies the same naming and uniqueness discipline regardless of which one is in play.

## Critical rules (never skip these)

1. **camelCase is the default naming convention** for every schema/namespace, table/collection/
   measurement, column/field, and index — unless the project already has its own established,
   *consistently applied* convention, in which case that convention wins and you say so rather
   than silently overriding it. See `references/naming-conventions.md`.
2. **Never create a schema, table, or index without first running the uniqueness/conflict
   check** in `references/uniqueness-and-conflict-checking.md` against the project's registry.
   A collision is caught before it happens, not discovered after.
3. **Never guess a column/field name or type when writing a query.** Read the registry
   (`.dbdesign/registry/schema-registry.json`) or the live schema first. If neither is
   available, say so and ask — a fabricated column name that happens to compile against an ORM
   but doesn't exist in the database is worse than asking.
4. **Every schema/table/index that gets created is recorded** in the registry and the audit
   log before the task is considered done. See `references/audit-record.md`.
5. **Generating DDL/migration files or model code is fine to do directly.** Actually *running*
   a migration or DDL statement against a live, connected database is a mutating action —
   confirm with the user first, the same as any other send/modify/delete action.
6. **Every usage-based schema object gets its own separate file** — one table/collection/index
   group per `.sql` (or engine-equivalent) file, under `database/sql/` (or the project's existing
   equivalent), never combined into one large dump file. See
   `references/file-organization.md`.

## Workflow

```
DISCOVER → GATHER REQUIREMENTS → DESIGN → NAMING CHECK → CONFLICT CHECK
   → PRESENT PROPOSAL → (approval) → GENERATE → RECORD → (ongoing) QUERY ASSISTANCE
```

### 1. DISCOVER
Before designing anything new, find out what already exists:
* Look for `.dbdesign/registry/schema-registry.json` in the project. If present, read it — it's
  the source of truth for what schemas/tables/indexes already exist and how they're named.
* If it's missing but the project has existing migrations, ORM models, or a live schema,
  offer to bootstrap the registry from those (read-only inspection) before proceeding —
  otherwise every conflict check runs blind. See `references/audit-record.md` §2.
* If there's truly nothing yet (greenfield project), start the registry fresh.

### 2. GATHER REQUIREMENTS
Don't design in a vacuum. Before proposing a schema, get (ask if not already given, but don't
block on exhaustive detail — reasonable defaults are fine for a first draft):
* What entity/entities this represents and their relationships to existing ones
* Which engine this targets (if the project already has one in use, assume that unless told
  otherwise)
* The access patterns that matter — for document/time-series/vector engines especially, the
  *query pattern* should drive the design far more than it does in a relational schema (see
  `references/engine-playbook.md`)
* Expected scale/cardinality if it plausibly affects the index or partitioning strategy

### 3. DESIGN
Propose columns/fields, types, primary/foreign keys or their engine-equivalent, and indexes,
following `references/schema-design-process.md` and the engine-specific guidance in
`references/engine-playbook.md`.

### 4. NAMING CHECK
Run every proposed name through `references/naming-conventions.md`. Note any engine-specific
caveat (e.g. Postgres folding unquoted identifiers to lowercase) that would break camelCase if
not handled — don't silently assume it'll work.

### 5. CONFLICT CHECK
Run the three-layer check in `references/uniqueness-and-conflict-checking.md` against the
registry: no schema name collides with an existing one, no table/collection name collides
within its schema, no index name or *functional* duplicate exists on the target table.

### 6. PRESENT PROPOSAL
Show the proposed design using `templates/schema-design-proposal.md` — names, types, keys,
indexes, the naming-check result, and the conflict-check result — and wait for approval before
generating files or touching a live database. This is the one required checkpoint in the
workflow; everything upstream of it is investigation and design, not commitment.

### 7. GENERATE
Once approved, generate the actual DDL, migration file, or ORM model code per
`templates/ddl-output.md`, writing each usage-based schema object to its own file per
`references/file-organization.md` (default: `database/sql/<objectName>.sql`, or
`database/sql/<schemaName>/<objectName>.sql` for multi-schema projects). Running it against a
live database is a separate, explicit confirmation (see Critical Rule 5).

### 8. RECORD
Update `.dbdesign/registry/schema-registry.json` with the new/changed objects, append one line
to `.dbdesign/registry/schema-registry-checks.jsonl` for the check that was run, and append an
entry to `.dbdesign/registry/design-log.md`. See `references/audit-record.md`.

### 9. QUERY ASSISTANCE (ongoing, not a one-time phase)
When asked to write or review a query, always check it against the registry (or live schema)
for correct names/types, and check whether the columns used in `WHERE`/`JOIN`/`ORDER BY`/
equivalent are actually covered by an index — see `references/query-writing.md`. If they
aren't, say so; don't silently write a query that will full-scan a large table or collection.

## Reference index

| File | Load it for |
|---|---|
| `references/naming-conventions.md` | camelCase rules and per-engine casing/charset caveats |
| `references/uniqueness-and-conflict-checking.md` | the mandatory pre-creation conflict check |
| `references/schema-design-process.md` | how to go from requirements to a concrete design |
| `references/engine-playbook.md` | modeling differences across relational/document/time-series/vector/graph/key-value |
| `references/query-writing.md` | writing and reviewing queries safely and with index-awareness |
| `references/file-organization.md` | one file per usage-based schema object, and where it lives on disk |
| `references/audit-record.md` | the `.dbdesign/registry/` store, its schemas, and how to bootstrap it |
| `schemas/schema-registry.schema.json` | structure of `schema-registry.json` |
| `schemas/schema-registry-check.schema.json` | structure of one line of `schema-registry-checks.jsonl` |
| `schemas/table-design-proposal.schema.json` | structure of a design proposal before approval |
| `templates/schema-design-proposal.md` | the human-readable proposal shown for approval |
| `templates/ddl-output.md` | how to present generated DDL/migration/model code + its audit entry |

## Compatibility note

If this project also uses the `testing-audit-debugging-protocol` skill, this skill can be
dropped into that protocol's `nested-skills/` directory as a specialist with
`mutation.readOnly: false` (design/build) — its registry format
(`schema-registry.json` / `schema-registry-checks.jsonl`) is the same one that protocol's
`references/database-schema-standards.md` expects during audits, so the two share state without
any translation step.
