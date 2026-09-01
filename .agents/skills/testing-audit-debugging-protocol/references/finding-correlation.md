# Finding Correlation

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it when you have two or more findings and must determine how they relate before proposing fixes.

The correlation engine groups related findings and records explicit **X-not-Y** relationships so that fixes are planned correctly and conflicts are surfaced rather than hidden.

---

## 1. Correlation Types

| Type | Meaning | Action |
|------|---------|--------|
| **Same-root-cause cluster** | Multiple symptoms trace to one root cause | Assign a cluster id; findings reference it |
| **Duplicate** | Same defect reported twice | Keep one canonical finding; note the other as dup-of |
| **Related-but-distinct** | Findings share a surface (file/feature) but different causes | Cross-reference; do not merge |
| **CONFLICTS / CONTRADICTS** | Two findings assert incompatible things | Record an explicit `X-not-Y` relation, pending resolution |
| **BLOCKS / BLOCKED-BY** | Ordering dependency between fixes | Record which fix must go first |

---

## 2. The `X-not-Y` Record

When two findings are related (especially when they conflict), record an explicit relationship:

> Finding `F3` **contradicts** `F2` on the validation rule for `waterCharge`. Both are CONFIRMED at the evidence level; the contradiction is unresolved and **masked** (`MASK: {F2, F3}`) until resolved by the user. No fix proceeds on either until the conflict is resolved.

Fields: `x` (finding id), `relation` (contradicts / duplicates / related / blocks / blocked-by / same-cluster), `y` (finding id), `status` (open / resolved / masked), `resolution` (notes).

---

## 3. Why Correlation Matters

* **Avoid double-fixing** the same root cause as two separate bugs.
* **Surface contradictions** before approving a fix — a fix built on one of two conflicting findings may be wrong.
* **Sequence dependencies** (BLOCKS / BLOCKED-BY) so you don't approve out-of-order edits.
* **Cleaner change budget** — a cluster shares one root cause, one fix plan, one approval.

---

## 4. Correlation Process

1. After findings are documented, group by root-cause hypothesis and by affected file/feature.
2. Assign cluster ids to same-root-cause groups.
3. Identify duplicates; mark canonical.
4. Detect conflicts/contradictions; record `X-not-Y` with status, mask affected fixes until resolved.
5. Record dependency ordering (BLOCKS / BLOCKED-BY) for fixes that must be sequenced.
6. Persist in `.audit/memory/correlation.json` (schema: `finding-correlation.schema.json`).
7. Reference cluster/relationship ids from the findings and from the Gate‑1 analysis and change budget.

---

## 5. Rules

* Do **not** silently merge distinct findings — cross-reference instead.
* A **conflict** must be surfaced to the user and resolved **before** a fix on either side is approved.
* Correlation is documentation / project memory — updating it never requires approval.
* Correlation informs but does not replace the per-finding approval gates.
