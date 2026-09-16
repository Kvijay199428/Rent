# Engine Playbook

This reference is part of the **database-schema-architect** skill. Load it alongside
`references/schema-design-process.md` — that file covers the universal process, this one covers
what differs by engine family.

## Relational (SQLite, PostgreSQL, MySQL/MariaDB, CockroachDB)

* Normalize by default; denormalize deliberately and only when a stated access pattern needs it
  (and note the trade-off — denormalization trades write complexity/consistency risk for read
  speed).
* CockroachDB is wire-compatible with PostgreSQL but is a distributed engine underneath —
  watch for hotspots on sequential primary keys (a monotonically increasing `SERIAL`/`BIGSERIAL`
  concentrates writes on one range); prefer `UUID` or a hash-sharded index when write throughput
  matters.
* SQLite has no true concurrent-writer story — fine for embedded/local/single-writer use, not
  for a multi-writer service backend; flag this if it's being proposed for that role.

## Document (MongoDB, etc.)

* The access pattern decides the shape, not "what feels normalized." Design around the queries
  the application will actually run, not around avoiding duplication for its own sake.
* Embed when: the sub-document is always read with its parent, doesn't grow unboundedly, and
  isn't queried independently.
* Reference when: the sub-document is large, shared across many parents, updated independently
  of the parent, or queried on its own.
* MongoDB has no cross-collection foreign-key enforcement — if referential integrity matters,
  say so explicitly in the proposal, since it has to be enforced in application code or via
  schema validation rules, not the database itself.

## Time-series (InfluxDB, TimescaleDB, etc.)

* Separate **tags** (indexed, low-cardinality, used to filter/group — e.g. `symbol`, `exchange`)
  from **fields** (the actual measured values — e.g. `price`, `volume`). Putting a
  high-cardinality value in a tag (e.g. a raw order id) can blow up the index size on some
  engines — flag this if proposed.
* Decide a retention/downsampling policy as part of the initial design, not as an afterthought —
  what raw resolution is kept for how long, and what aggregate rolls up after that.
* TimescaleDB is Postgres underneath (hypertables), so the relational caveats above (quoting,
  hotspots on sequential keys for the partitioning column) still apply.

## Vector (Pinecone, Milvus, Weaviate, Qdrant, pgvector, ...)

* Decide embedding dimension and distance metric (cosine / dot product / Euclidean) up front —
  changing either later usually means re-embedding and reindexing everything.
* Decide the index type where the engine exposes one (HNSW vs. IVF, etc.) based on the
  recall/latency/build-time trade-off the use case needs — don't leave it at whatever the
  client library defaults to without checking it's appropriate for the expected scale.
* If metadata filtering alongside vector search is needed (e.g. "similar items, but only in
  category X"), design the metadata schema explicitly — it's a first-class design decision on
  most of these engines, not a bolt-on.
* pgvector inherits every Postgres caveat above, since it's a Postgres extension.

## Key-value / wide-column (Redis, DynamoDB, Cassandra-family, etc.)

* The primary/partition key design *is* the schema design — get the access pattern right before
  picking it, since these engines generally don't support ad hoc secondary queries the way a
  relational engine does.
* For Cassandra-family wide-column stores, design one table per query pattern rather than one
  table per entity — denormalization across multiple purpose-built tables is the normal,
  expected design here, not a smell.

## Graph (Neo4j, etc.)

* Model the entities that matter as nodes and the relationships that matter as edges — don't
  reflexively translate a relational many-to-many join table into a node; it's usually just an
  edge with properties.
* Index the properties actually used to look up starting nodes for traversals; a graph engine's
  performance is dominated by how traversals start, not by scanning.
