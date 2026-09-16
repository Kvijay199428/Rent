# Audit Record — `.dbdesign/registry/`

This reference is part of the **database-schema-architect** skill. Load it whenever you create,
update, or bootstrap the project's persistent schema registry.

## 1. Location

Lives inside the project being worked on, not the global skill directory:

```
<project>/.dbdesign/
├── registry/
│   ├── schema-registry.json          (current schemas/tables/indexes, all engines in the project)
│   ├── schema-registry-checks.jsonl  (append-only log of naming/conflict checks)
│   └── design-log.md                 (human-readable running log of design decisions)
```

**Design rule:** the registry describes what actually exists (or has been proposed and
approved) — never write a speculative or rejected design into it.

## 2. Bootstrapping when it doesn't exist yet

If `.dbdesign/registry/schema-registry.json` is missing but the project has existing migrations,
ORM model definitions, or a reachable live database:

1. Say what you're about to do (read-only inspection) before doing it.
2. Enumerate existing schemas/tables/collections/indexes from whichever source is available
   (migration files are usually most reliable; a live introspection query is the ground truth
   if reachable).
3. Write the result as the initial `schema-registry.json`, and note in `design-log.md` that it
   was bootstrapped from inspection on this date, and from what source — future conflict checks
   depend on this being accurate, so the provenance matters if something looks off later.
4. If existing naming is inconsistent, note that in `design-log.md` as a baseline observation,
   not as something to silently normalize.

## 3. `schema-registry.json`

Structure: `schemas/schema-registry.schema.json`. One entry per database instance/connection,
each with its schemas, each schema with its tables/collections, each table with its indexes
and its `filePath` — the dedicated file this object's schema lives in on disk (see
`references/file-organization.md`). Update it every time something is created, renamed, or
dropped — never let it drift from reality, since every future conflict check trusts it.

## 4. `schema-registry-checks.jsonl`

Structure: `schemas/schema-registry-check.schema.json`. Append one line every time the
uniqueness/conflict check (`references/uniqueness-and-conflict-checking.md`) runs, whether or
not it found anything — a clean check is still worth a line, so the log shows the check
actually happened rather than being silently skipped.

## 5. `design-log.md`

A human-readable, append-only running log — one entry per design decision, in plain language:
what was proposed, why, what the naming/conflict check found, whether it was approved as
proposed or changed, and what was ultimately created. This is the file a new developer (or a
future session) reads to understand *why* the schema looks the way it does, not just what it
looks like.

Example entry:

```markdown
## 2026-09-08 — orderHistory table (PostgreSQL, `tradingSignals` schema)

Proposed to store filled orders for the backtesting engine. Chose to store price/quantity as
`NUMERIC` rather than `FLOAT` to avoid rounding drift over aggregation. Naming check: clean,
camelCase throughout. Conflict check: clean — no existing table or index collided.
Indexes: idxOrderHistorySymbolCreatedAt (symbol, createdAt) to support the backtester's
per-symbol time-range scans. Approved as proposed. File: database/sql/tradingSignals/orderHistory.sql
```

## 6. Interop with `testing-audit-debugging-protocol`

If the project also runs that skill's database audits, both skills read and write the *same*
`schema-registry.json` / `schema-registry-checks.jsonl` structure (see that skill's
`references/database-schema-standards.md`) — an audit run by that skill and a design change made
by this one stay consistent with each other automatically, with no translation step needed.
