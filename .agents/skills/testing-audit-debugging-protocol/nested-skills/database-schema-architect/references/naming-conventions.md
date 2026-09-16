# Naming Conventions

This reference is part of the **database-schema-architect** skill. Load it any time you're
about to name a schema, table, collection, measurement, column, field, or index.

## Default: camelCase, everywhere

Unless the project already has its own established, *consistently applied* convention, name
every:

* schema / namespace / keyspace / database-group → `tradingSignals`, `userAccounts`
* table / collection / measurement / index-class → `orderHistory`, `userSessions`
* column / field / tag / vector-metadata-key → `createdAt`, `userId`, `closePrice`
* index → `idxUserEmail`, `idxOrderCreatedAt`

in **camelCase**. Don't mix conventions within one project. If asked for a single table in a
project that already has a consistent existing convention (e.g. `snake_case` throughout),
follow the existing convention for that table and say so — don't introduce camelCase into an
otherwise-consistent codebase without being asked to. If the project's existing naming is
already *inconsistent*, camelCase is the default going forward; say so and let the user decide
whether to also normalize existing objects (a rename is a separate, approved change — never
silently rename something that already ships).

## Engine-specific caveats — check these before assuming camelCase "just works"

| Engine | Behavior | What to do |
|---|---|---|
| PostgreSQL / CockroachDB | Unquoted identifiers are folded to lowercase | Double-quote every camelCase identifier in DDL, and configure the ORM/migration tool to quote identifiers consistently — otherwise `"userAccounts"` and `useraccounts` silently diverge |
| MySQL / MariaDB | Table-name case sensitivity depends on the OS/filesystem and the `lower_case_table_names` server setting | Check that setting before relying on case; use backticks consistently either way |
| MongoDB | Collection and field names are case-sensitive by default | camelCase applies cleanly, no quoting needed |
| SQLite | Preserves case as written | camelCase is preserved; don't assume a lookup will match case-insensitively |
| Time-series (InfluxDB, TimescaleDB, etc.) | Measurement/hypertable names and tag/field keys generally preserve case | camelCase applies; TimescaleDB inherits the Postgres quoting caveat since it runs on Postgres |
| Vector DBs (Pinecone, Milvus, Weaviate, Qdrant, ...) | Case-sensitive names, but some restrict the allowed character set (lowercase + hyphen only, no camelCase, in a few managed services) | Check the target engine's naming rules before proposing a name; if it can't take camelCase, record that as a documented exception, not a violation, and use the engine's own convention for that one name |
| pgvector (vector index on Postgres) | Runs on Postgres | Both the Postgres quoting caveat and the normal camelCase rule apply |

If an engine's own constraints make camelCase genuinely impossible for a given object, that's a
documented exception (state it in the proposal), not something to silently work around or
pretend isn't happening.

## What NOT to do

* Don't rename existing production objects to "fix" naming as a side effect of an unrelated
  task — a rename is a schema-changing action of its own and needs its own approval.
* Don't apply camelCase to values or literal data — this convention is for schema/structural
  names only.
* Don't guess at whether an engine needs quoting — check `references/engine-playbook.md` or the
  engine's own docs for the specific version in use if there's any doubt.
