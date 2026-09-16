# Schema Design Proposal Template

Fill this in and present it before generating DDL/migration code or touching a live database.
Corresponds to `schemas/table-design-proposal.schema.json`.

```markdown
## Proposal: <objectName> (<engineType>, schema: <schemaName>)

**Purpose:** <one or two sentences — what this represents and why>

**File:** `database/sql/<objectName>.sql` (or `database/sql/<schemaName>/<objectName>.sql` for
multi-schema projects) — see `references/file-organization.md`

**Access patterns this was designed for:**
- <pattern 1>
- <pattern 2>

**Columns / fields:**

| Name | Type | Nullable | Notes |
|---|---|---|---|
| <name> | <type> | <yes/no> | <PK / FK to X / etc.> |

**Indexes:**

| Name | Columns | Unique | Type | Why |
|---|---|---|---|---|
| <indexName> | <col1, col2> | <yes/no> | <btree/hash/hnsw/etc.> | <which access pattern this serves> |

**Naming check:** <clean / violation flagged: ... / documented exception: ...>

**Conflict check:** <clean / conflict flagged: <object A> vs <object B> at <layer>>

**Open questions / trade-offs for you to decide:**
- <anything not fully determined by the requirements — e.g. retention policy, embed-vs-reference choice>
```

## Notes on filling it in

* Keep the "why" for each index — an approver should be able to tell which stated access
  pattern justifies each one, not just see a bare column list.
* If the naming or conflict check found something, state it plainly here rather than only in
  the audit log — the proposal is where the person actually makes the call.
* If this proposal supersedes or alters an existing object (rather than creating a new one),
  say so explicitly and note what changes for any existing queries/code that reference it.
