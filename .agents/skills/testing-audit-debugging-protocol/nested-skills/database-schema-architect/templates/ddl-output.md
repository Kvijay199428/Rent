# DDL / Migration Output Template

Use this once a proposal (`templates/schema-design-proposal.md`) has been approved, to present
the generated artifact and the audit-record update together.

```markdown
## Generated: <objectName> (<engineType>)

**File:** `database/sql/<objectName>.sql` (or `database/sql/<schemaName>/<objectName>.sql` for
multi-schema projects) — one file for this object, per `references/file-organization.md`.

\`\`\`sql
-- Proposal: <proposalId>
-- Schema: <schemaName>   Object: <objectName> (<objectKind>)
-- Purpose: <one line>
-- Naming check: <clean/...>   Conflict check: <clean/...>
-- Created: <date>

<generated DDL / model code, including this object's own indexes>
\`\`\`

**Registry updated:** `.dbdesign/registry/schema-registry.json` — added <schemaName>.<objectName>
with <N> indexes.

**Check logged:** `.dbdesign/registry/schema-registry-checks.jsonl` — <checkId>

**Design log entry added:** `.dbdesign/registry/design-log.md` — see entry dated <date>

**Not yet applied to a live database.** Running this migration/DDL against
`<connection/environment>` is a separate step — confirm before I run it, or apply it yourself
through your normal migration tooling.
```

## Notes

* Never claim a migration was "applied" unless it was actually run against a reachable, live
  database in this session with explicit confirmation — generating the file and running it
  are two different, separately-confirmed actions.
* If the generated code uses an ORM's schema-definition syntax rather than raw DDL, make sure
  the ORM's column/table name mapping is also camelCase-consistent (many ORMs default to
  translating between camelCase model attributes and snake_case database columns — decide and
  state which side of that translation the camelCase rule applies to, so there's no silent
  mismatch between the registry and what's actually in the database).
