# Schema Design Process

This reference is part of the **database-schema-architect** skill. Load it when moving from
requirements to a concrete table/collection/index design, for any engine.

## 1. Identify the entity and its shape

* What real-world thing or event does this represent?
* Is it mutable state (a `users` row that gets updated) or an immutable event/fact (an
  `orderPlaced` event, a tick, a log line)? This affects almost everything downstream — mutable
  state favors normalization and update-in-place; immutable events favor append-only, time- or
  id-ordered storage and often a time-series or log-oriented engine rather than a relational
  table.

## 2. Choose columns/fields and types

* Use the narrowest correct type available on the target engine (don't default to `TEXT`/
  `VARCHAR(255)` for everything, or `string` for a MongoDB field that's actually always numeric).
* Every table/collection gets an explicit primary identifier — an engine-native id type where
  one exists (`UUID`, `ObjectId`, `SERIAL`/`BIGSERIAL`, engine-specific auto-id) unless there's a
  concrete reason to use a natural key.
* Timestamps: store in UTC, use the engine's native timestamp/datetime type (not a string), and
  name them consistently — `createdAt`, `updatedAt`, `deletedAt` (if soft-deleting) across the
  whole project, not a different pair of names per table.
* Nullability is a decision, not a default — state explicitly which fields are required.

## 3. Define relationships / access patterns

* **Relational (SQL):** define foreign keys explicitly, with an explicit `ON DELETE`/
  `ON UPDATE` behavior (don't leave it as the engine default without deciding it's actually
  what you want).
* **Document (MongoDB, etc.):** the access pattern decides embed vs. reference — embed data
  that's always read together and doesn't grow unboundedly; reference data that's large, shared
  across many parents, or updated independently. State which was chosen and why in the proposal.
* **Time-series:** decide the measurement/hypertable, which fields are tags (indexed,
  low-cardinality, used for filtering) vs. fields (the actual measured values), and the
  retention/downsampling policy up front — retrofitting cardinality decisions later is expensive.
* **Vector:** decide the embedding dimension, distance metric (cosine/dot/euclidean), and
  whether metadata filtering is needed alongside the vector search — these are structural
  decisions, not query-time details, on most engines.

## 4. Design indexes deliberately, not reflexively

* Index the columns/fields that the stated access patterns actually filter, join, or sort on —
  don't index everything "just in case," and don't design a table with zero indexes beyond the
  primary key when the stated access pattern clearly needs one.
* For composite indexes, column order matters — put the equality-filtered column(s) before the
  range-filtered/sorted one(s), matching how the query will actually use it.
* Every index proposed gets checked for uniqueness/functional-duplication per
  `references/uniqueness-and-conflict-checking.md` before it's included in the final proposal.

## 5. Apply naming

Every schema/table/column/index name from steps 1–4 goes through
`references/naming-conventions.md` before the proposal is written up.

## 6. Write the proposal

Use `templates/schema-design-proposal.md`. Include the reasoning from steps 1–4 (briefly) so the
approval isn't just "yes/no" on a bare DDL block — the person approving should see *why* each
choice was made.
