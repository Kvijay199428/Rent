# Audit Memory

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever you create, update, or read the project's persistent audit state.

Audit memory is the **durable, project-scoped store** of everything the orchestrator learned and did. It makes the audit replayable, queryable, and cross-session consistent.

---

## 1. Location — Project-Side, Not Global

Audit memory lives in **`.audit/`** inside the project being audited — **not** inside the global skill directory.

```
<project>/.audit/
├── memory/
│   ├── capability-registry.json      (optional persisted registry)
│   ├── skill-usage.jsonl             (append-only skill execution records)
│   ├── tool-usage.jsonl              (append-only tool execution records)
│   ├── findings.jsonl                (append-only findings with evidence + confidence)
│   ├── correlation.json              (finding clusters / X-not-Y records)
│   └── reputation.json               (derived reputation scores)
├── evidence/                         (raw evidence blobs: logs, screenshots, captures)
```

**Design rule:** *Global skill = methodology; Project memory = experience.* Never write experience into the global skill directory.

---

## 2. Relationship to the Markdown Deliverables

The human-readable deliverables remain:

```
test-audit-task.md
audit-plan.md
audit-log.md
bucket-list.md
skill-usage-log.md
skill-mapping.md   (only if declared)
```

The `.audit/memory/` JSON/JSONL stores are the **machine-readable view** of the same records. Keep the two in sync:

* Every `skill-usage-log.md` row ↔ one `skill-usage.jsonl` record.
* Every `audit-log.md` finding ↔ one `findings.jsonl` record.
* Every proposed change / approval ↔ one `approval` record (and, for audit trail, the matching row in `bucket-list.md`).

Both are documentation / project memory — updating them never requires approval.

---

## 3. Stores and Schemas

| Store | Format | Schema | Contents |
|-------|--------|--------|----------|
| capability-registry.json | JSON | `capability-registry.schema.json` | registered capabilities + reputation |
| skill-usage.jsonl | JSONL | `skill-execution.schema.json` | one skill execution record per line |
| tool-usage.jsonl | JSONL | `tool-execution.schema.json` | one tool execution record per line |
| findings.jsonl | JSONL | `finding.schema.json` + `evidence.schema.json` | one finding (with evidence refs) per line |
| correlation.json | JSON | `finding-correlation.schema.json` | clusters + X-not-Y relations |
| reputation.json | JSON | (derived) | per-capability reputation bands |

JSONL is append-only: never rewrite history, only append. This preserves a truthful chronological trail and makes replay correct.

---

## 4. Finding & Evidence Records

A finding (see `schemas/finding.schema.json` and `templates/finding.md`) must carry:

* id, severity (P0–P3)
* confidence (INSUFFICIENT/LOW/MEDIUM/HIGH/VERY HIGH — see SKILL.md thresholds)
* root-cause status (CONFIRMED / LIKELY / SUSPECTED)
* observed vs expected, reproduction steps
* evidence references (each pointing to a raw evidence item with its producer)
* correlation cluster id (if any)
* status (OPEN / APPROVED / FIXED / VERIFIED / REJECTED / WONT-FIX)

An evidence item (see `schemas/evidence.schema.json`) must carry:

* id, captured-at
* kind (log / screenshot / capture / test output / DB result / manual observation)
* producer (the execution record id of the skill/tool that produced it)
* location (file path or `.audit/evidence/` blob)
* content/pointer, and hash for integrity where useful

---

## 5. Rules

* Audit memory is **append-only and permanent** for the duration of the audit — do not delete or rewrite history (honest documentation; see `deployment-gate.md`).
* Audit memory is **documentation / project memory** — updating it never requires approval.
* Keep it **in sync** with the human-readable deliverables; both agree.
* Never store secrets in audit memory (sandbox logs, truncate keys/tokens).
* Memory is project experience — it may inform reputation and selection, but it never authorizes a change on its own.
