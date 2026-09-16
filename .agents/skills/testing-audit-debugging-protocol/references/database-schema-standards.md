# Database Schema, Table & Index Standards

This reference is part of the **testing-audit-debugging-protocol** skill. Load it whenever any
database is in scope for an audit — relational (SQLite, PostgreSQL, CockroachDB, MySQL, ...),
document (MongoDB, ...), time-series (InfluxDB, TimescaleDB, ...), vector (Pinecone, Milvus,
Weaviate, Qdrant, pgvector, ...), key-value, graph, or anything else. It is invoked from:

* `references/testing-strategies.md` §6 (Data Integrity Testing)
* `references/audit-documents.md` — the `## Database` section of `bucket-list.md`

It does not change the core rule in `SKILL.md` §1: *"Do NOT modify database schemas on your
own."* Everything below is a **read-only verification + audit-record standard** run during
AUDIT. If it surfaces a naming violation or a conflict, that becomes a normal finding and goes
through ANALYSIS → Gate 1 → Gate 2 like any other proposed change — it is never auto-fixed.

---

## 1. Naming Convention — camelCase, everywhere, engine-aware

Every schema / namespace / keyspace / database-group name, and every table / collection /
measurement / index name inside it, is expected to be **camelCase**
(`tradingSignals`, `userAccounts`, `marketTicksV2`, `idxUserEmail`) unless the project already
has an established, consistently-applied convention of its own.

* If the project has no consistent convention yet → camelCase is the target; recommend it.
* If the project already has a different but *consistent* convention (e.g. `snake_case`
  throughout) → do not silently rename existing objects. Flag the mismatch as a finding
  ("no camelCase convention in place; project consistently uses X") and let the user decide
  whether to adopt camelCase going forward or keep the existing standard. A rename is
  change-making → Gate 2, never automatic.
* If the project has **inconsistent** naming (some camelCase, some snake_case, some ad hoc) →
  this is itself a finding regardless of which convention wins.

### Engine-specific caveats — record these, don't paper over them

These affect whether camelCase actually survives round-trips on a given engine. State the
relevant caveat in the finding/audit record whenever it applies — do not assume camelCase
"just works" without checking the engine's identifier-folding behavior first.

| Engine | Behavior | Implication |
|---|---|---|
| PostgreSQL / CockroachDB | Unquoted identifiers are folded to lowercase | camelCase names must be double-quoted (`"userAccounts"`) in every DDL/DML statement and ORM mapping, or they silently become `useraccounts` and stop matching |
| MySQL / MariaDB | Table-name case sensitivity depends on the OS/filesystem and `lower_case_table_names` setting | camelCase table names may or may not be case-preserved depending on server config — verify the setting before relying on case, and use backticks consistently |
| MongoDB | Collection and field names are case-sensitive by default | camelCase applies cleanly, no quoting concerns |
| SQLite | Preserves case as written; keyword matching is case-insensitive but identifiers are not folded | camelCase is preserved, but don't assume a case-insensitive lookup will find it |
| Time-series (InfluxDB, TimescaleDB, etc.) | Measurement/hypertable names and tag/field keys generally preserve case | camelCase applies; TimescaleDB inherits the PostgreSQL quoting caveat above since it runs on Postgres |
| Vector DBs (Pinecone, Milvus, Weaviate, Qdrant, ...) | Index/collection/class names are generally case-sensitive strings with engine-specific charset restrictions | camelCase applies where the charset allows it — check the engine's allowed-character set before naming (some restrict to lowercase+hyphen only, in which case log the restriction as a documented exception, not a violation) |
| pgvector (vector index on Postgres) | Runs on Postgres | Both the Postgres quoting caveat and normal camelCase rule apply |

If an engine's own constraints make camelCase impossible or impractical (e.g. a vector DB that
only accepts lowercase-and-hyphen names), record that as a **documented exception**, not a
violation — the goal is consistency and traceability, not fighting the engine.

---

## 2. Uniqueness & Conflict Check — run every audit, at three layers

Before any schema/table/index is proposed, and again before the audit concludes, run and log a
conflict check:

### a. Schema-level
No two schemas/namespaces/keyspaces in the same audited database instance/cluster share a name.
Compare **case-insensitively even on case-sensitive engines** — a case-only collision
(`userAccounts` vs `useraccounts`) is confusing regardless of whether the engine technically
allows it, and is a finding either way.

### b. Table/collection-level
Within each schema: no two tables/collections/measurements share a name (case-insensitive
compare, same reasoning as above). Across different schemas: a same-name table is not
necessarily wrong (e.g. per-tenant schemas each with a `users` table is often intentional) —
note it for visibility rather than flagging it as a conflict.

### c. Index-level
Within each table/collection:
* No two indexes share a name.
* No two indexes are **functionally identical** — same columns/fields, same order, same
  type/uniqueness constraint. A functional duplicate is a finding even when the names differ:
  it costs write throughput and storage for zero additional query benefit.

Re-run this check any time the audit proposes creating, renaming, or altering a schema, table,
or index — not only once at the start of the audit.

---

## 3. Schema/Index Audit Record

Maintain `.audit/memory/schema-registry.json` — a generated/updated store, never hand-edited,
one entry per audited database instance, each with its schemas, each schema with its
tables/collections, each table with its indexes. Structure: `schemas/schema-registry.schema.json`.

Every time a database is inspected during an audit (read-only inspection is sufficient — this
never requires Gate 2 on its own), append one line to
`.audit/memory/schema-registry-checks.jsonl`. Structure: `schemas/schema-registry-check.schema.json`.
Minimum fields:

* `checkId` (e.g. `SR-001`)
* `timestamp`
* `engineType` — name the actual engine, not just the category (`postgresql`, `mongodb`,
  `cockroachdb`, `sqlite`, `timeseries:influxdb`, `vector:qdrant`, etc.)
* `connectionRef` — however the project identifies this instance; **never log credentials or
  full connection strings**
* `schemasFound`, `tablesFound`, `indexesFound` — counts
* `namingViolations` — list (empty if none), each citing the offending object and which rule
  in §1 it breaks
* `duplicateOrConflicting` — list (empty if none), each citing the two objects involved and
  which layer in §2 caught it
* `relatedExecutionRecord` — the `SU-###` this check was performed under (see
  `references/audit-memory.md`)

A naming violation or an unresolved conflict found this way is a normal finding
(`schemas/finding.schema.json`) and goes through the same ANALYSIS → Gate 1 → Gate 2 flow as
any other proposed change — this reference only standardizes how it's *detected and recorded*,
never how it's *fixed*.

`scripts/validate_audit_memory.py` (see `references/verification-and-drift-detection.md`)
should also check `schema-registry-checks.jsonl` for internal consistency: any line with a
non-empty `namingViolations` or `duplicateOrConflicting` must have a matching entry in
`findings.jsonl`, or the validator flags it as a silent-omission gap the same way it flags a
missing Gate 2 record.

---

## 4. Where this plugs into the existing protocol

* `references/testing-strategies.md` §6 (Data Integrity Testing) — before concluding
  data-integrity testing for any database-backed finding, run the §1 naming check and the §2
  conflict check against every database touched, and log both per §3.
* `references/audit-documents.md` — every entry under the `## Database` section of
  `bucket-list.md` states the engine type, and for any proposed new/renamed schema, table, or
  index: its camelCase name and the result of the §2 conflict check.
* `references/audit-memory.md` — add `schema-registry.json` and `schema-registry-checks.jsonl`
  to the audit-memory store table (see wiring notes).

