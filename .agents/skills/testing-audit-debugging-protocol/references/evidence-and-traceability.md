# Evidence & Traceability — The Evidence Graph

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever a finding is produced, whenever you need to prove a finding, or whenever you must answer *"how do we know this is true?"*.

The **evidence graph** links **findings → evidence → execution records → files → skills/tools**. It is the traceability backbone of the audit.

---

## 1. What the Graph Connects

```
FINDING  ──has──▶  EVIDENCE  ──produced-by──▶  EXECUTION RECORD ──used──▶  SKILL/TOOL
   │                     │                                                      │
   │                     └──at──▶  FILE / blob location                         └──source (global/project)
   └──touches──▶  FILE(s)
```

* **Finding** → points to the evidence that supports it.
* **Evidence** → points to the execution record (skill/tool) that produced it and to its location.
* **Execution record** → points to the skill/tool and the files touched.
* **Finding** → also points to affected files.

This lets anyone walk *finding → evidence → execution record → skill/tool → file* to confirm or refute a finding.

---

## 2. Why It Matters

* **Accountability:** no finding exists without evidence, and no evidence exists without a recorded producer.
* **Auditable selection:** the skill/tool that produced each piece of evidence is on record with its `WHY THIS SKILL?` reason.
* **Replay:** the graph can be reconstructed from `.audit/memory/` for replay (see `audit-replay.md`).
* **Honest reporting:** a finding without a traceable evidence chain is demoted (confidence `INSUFFICIENT`) until evidence is produced.

---

## 3. Building the Graph

The graph is materialized in `schemas/evidence-graph.schema.json` and can be:
* **Reconstructed on demand** from the `.jsonl` stores (findings → evidence → execution records), or
* **Materialized** in `.audit/memory/` as a graph structure for query.

Each finding update appends/extends its evidence references. Each execution record carries the outcome/evidence it produced, so the link back to findings is direct.

---

## 4. Evidence Quality Rules

Evidence must be:
* **Reproducible** — exact command, input, endpoint, request/response, status, error, screenshot, DB result, file/line, environment, timestamp.
* **Producer-attributed** — which skill/tool execution record produced it.
* **Unmodified** — do not delete or rewrite earlier evidence (honest documentation).
* **Proportional** — security testing does not exploit beyond what is needed to demonstrate the issue.

A statement such as "it seems broken" is **not** evidence. A finding that relies on it is `INSUFFICIENT` and not reportable as a confirmed finding.

---

## 5. Evidence Integrity

Where practical, capture a hash of raw evidence blobs stored in `.audit/evidence/` so later review can confirm they were not altered. Screenshots, logs, and test outputs are the most valuable evidence and should be stored with their timestamps.

---

## 6. Rules

* Every finding must reference at least one piece of evidence.
* Every evidence item must reference its producer execution record.
* Do not report a finding as CONFIRMED without a traceable evidence chain at HIGH/VERY HIGH confidence.
* Keep the evidence graph consistent with `audit-log.md` and `skill-usage-log.md` (cross-reference both ways).
