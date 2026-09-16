# Query Writing & Review

This reference is part of the **database-schema-architect** skill. Load it whenever asked to
write, generate, or review a query — SQL, an aggregation pipeline, a vector search call, or
otherwise — against a schema this skill knows about (or should know about).

## 1. Never guess names or types

Before writing a query, check `.dbdesign/registry/schema-registry.json` (or, if it's missing or
looks stale, the live schema/migration files) for the actual column/field names and types. If
neither is available, say so plainly and ask, rather than writing a query against plausible-
looking but unverified names — a query that compiles against an ORM's generated types but
references a column that doesn't actually exist, or exists with a different name, fails at
runtime instead of at review time.

## 2. Check index coverage before finalizing

For every `WHERE`, `JOIN`, `ORDER BY`, or equivalent clause (an aggregation `$match`/`$sort`
stage, a time-series filter, a vector search's metadata filter):

* Confirm an index actually covers it, using the registry.
* If it doesn't, say so explicitly rather than silently shipping a query that will full-scan a
  large table/collection. Either propose the missing index (through the normal design-and-
  approve flow in `SKILL.md`) or flag the trade-off if adding one isn't worth it for a rarely-run
  query.
* For composite indexes, check that the query's filter order actually matches the index's
  column order — a query filtering on the second column of a composite index without the first
  often can't use it at all on some engines.

## 3. Safety

* Always parameterize — never interpolate user-controlled values directly into a query string,
  regardless of engine. This applies equally to SQL, MongoDB query documents built from
  user input, and any other engine's query language.
* For any query that mutates data (`UPDATE`/`DELETE`/equivalent), state what it affects and
  its scope (row/document count, or an estimate) before it's run against a live database —
  running it is a mutating action and follows the same confirm-before-acting rule as schema
  changes.

## 4. Engine-specific notes

* **Relational:** prefer `EXPLAIN`/`EXPLAIN ANALYZE` to confirm the query plan actually uses the
  index you expect, especially for anything non-trivial — don't assume the planner will do what
  seems obvious.
* **MongoDB:** check `.explain()` similarly; a compound index only helps in certain field-order/
  query-shape combinations.
* **Time-series:** be explicit about the time range in every query — an unbounded time-range
  query is usually a bug, not a feature, on these engines.
* **Vector:** state the `k` (number of neighbors) and any metadata filter explicitly; an
  unfiltered top-k query against a large index behaves very differently in latency terms than a
  filtered one, and that's worth surfacing if it's not what was asked for.
