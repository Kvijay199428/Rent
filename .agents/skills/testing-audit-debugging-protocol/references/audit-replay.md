# Audit Replay

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it when reviewing an audit after the fact, on-boarding a fresh session to an in-progress audit, or verifying that what was approved actually happened.

Because every selection, invocation, finding, correlation, and approval is recorded, the entire audit can be **replayed** by walking the `.audit/memory/` stores in order.

---

## 1. What Replay Answers

* What was discovered and registered (capability registry)
* What was selected, and why (`WHY THIS SKILL?` + `WHY NOT X?`)
* What was invoked, with what outcome (execution records)
* What findings were produced, with evidence and confidence (findings.jsonl)
* How findings correlate (clusters, `X-not-Y`)
* What was approved at each gate, and what actually changed (approval audit trail)

---

## 2. Replay Sequence

Walk the stores in this order to reconstruct the audit:

1. **DISCOVERY / REGISTRY** — `capability-registry.json` + discovery execution records → what was available.
2. **SELECTION** — skill-selection records → what was chosen and why.
3. **INVOCATION** — `skill-usage.jsonl` + `tool-usage.jsonl` → what ran, with outcomes.
4. **FINDINGS** — `findings.jsonl` + `.audit/evidence/` → what was found, with evidence.
5. **CORRELATION** — `correlation.json` → how findings group / conflict.
6. **APPROVAL** — approval records → what was approved at each gate.
7. **CHANGE + VERIFICATION** — the audit trail of what actually changed and the re-test/regression evidence.

---

## 3. Uses

* **Post-audit review** — present the timeline to the user as a readable sequence.
* **Session hand-off** — a fresh session loads `.audit/memory/` and resumes an in-progress audit without losing context.
* **Regression check** — "did we fix what we said we fixed?" is answered by walking finding → approval → change → verification evidence.
* **Compliance / honesty** — verifies no change-making skill/tool ran without an approved Gate 2, and every finding has evidence.

---

## 4. Rules

* Replay is **read-only** — it reconstructs the record, it does not re-run invocations.
* Replay only shows what was recorded; an unrecorded action is invisible and therefore suspect. This is why every invocation must be recorded at the time it happens.
* Replay output should distinguish confirmed evidence from gaps (e.g. a finding with no evidence chain is `INSUFFICIENT`).
