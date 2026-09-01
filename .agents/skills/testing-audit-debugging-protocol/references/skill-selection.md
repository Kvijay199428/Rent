# Skill Selection Engine

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever you are about to **select** how a given audit question or finding will be handled, and whenever you need to express **why** a skill/tool was (or was not) chosen.

Selection answers: *"For this audit question / this finding, which skill or tool should I use, and why?"*

---

## 1. Selection Modes

Choose the mode (defaulting as noted) and record it:

| Mode | Behavior | When to use |
|------|----------|-------------|
| **Automatic** | Pick the top-ranked candidate per the Selection Criteria and proceed (read-only) or propose (change-making). | Trusted/established domains; user pre-approved the mode. |
| **User Directed** | The user's declared mapping (in `skill-mapping.md` or conversation) wins outright. | User has stated a preference. |
| **User Approved** | Score candidates, but present the final pick for confirmation before use. | High-stakes, ambiguous, or first-time selections. |

Record the mode in the execution record (`selection_mode` field).

---

## 2. Selection Criteria (weighed, in order)

1. **User-declared mapping wins.** Check `skill-mapping.md` and the conversation. Honor it without re-deriving criteria.
2. **Domain / file-type match.** Does the artifact match the candidate's stated domain? (`.docx` → docx skill; broken formula in `.xlsx` → spreadsheet skill; UI defect → frontend-design skill; security finding → security skill; perf question → web-perf skill.)
3. **Risk-area match.** Security findings → security-focused instrument; data-integrity findings → differential-verification / data-analysis instrument.
4. **Task-native fit.** Prefer the project's own declared tooling (its test runner, its linter, its build script) over a generic substitute.
5. **Precedent.** A skill/tool already used successfully for a similar issue in this project (from audit memory) beats an unproven substitute.
6. **Reputation.** Prefer higher reputation (see `capability-registry.md`) when other criteria are equal.
7. **Minimalism.** If the task can be done with what already exists, do not reach for an extra skill/tool. Orchestration is for when a specialist genuinely improves accuracy, evidence quality, or the fix.

If two or more candidates tie and neither mapping nor precedent resolves it, **ask the user** rather than guessing (or present options if your environment supports it).

---

## 3. Explainable Reason — `WHY THIS SKILL?`

Every non-trivial selection must be expressed as a one-line reason:

> **`WHY THIS SKILL?`** `<capability>` chosen for `<finding/phase>` because `<criteria 1..3 that apply>`; alternatives: `<alt1>, <alt2>`; decided by `<mode>`.

It must be specific enough for a user to approve or redirect confidently.

---

## 4. Rejection Reason — `WHY NOT skill X?`

When a plausible alternative was considered and rejected, record a short **`WHY NOT <X>?`** line with the decisive reason:

* weaker domain match (e.g. "X is a design skill, not a data-integrity skill")
* lower reputation / no precedent in this project
* change-making when read-only was preferred
* project's own tool beats the generic substitute (task-native fit)
* user mapping declared a different instrument

This makes rejections auditable too. A rejected candidate is still recorded in `skill-usage-log.md` as *considered*, with `WHY NOT X?` noted.

---

## 5. User-Directed Mapping (`skill-mapping.md`)

Optional durable policy. Create it as soon as the user states a preference, or when two-or-more skills/tools genuinely tie and the user resolves it. A declared mapping **always overrides auto-selection** (Criterion 1).

### Schema

```text
# Skill Usage Policy

## Declared Mappings
- Category: <kind of analysis or fix, e.g. "spreadsheet formula bugs">
  Skill/Tool: <name>
  Declared by: user (quote/paraphrase) / inferred from precedent
  Notes: <scope limits, e.g. "read-only inspection only" or "use version 2">

- Category: <e.g. "Word/report generation defects">
  Skill/Tool: <name>
  Declared by: user
  Notes:

## Default (no mapping declared)
Follow the Selection Criteria above; ask the user when multiple candidates are plausible.
```

Update it whenever the user states a new preference so future phases (and future audits of the same project) don't re-ask.

---

## 6. Selection Output

For each selected instrument, produce a `skill-selection` record (see `schemas/skill-selection.schema.json` and `templates/skill-selection.md`) containing: candidate, selected-by (mode), score/rank, `WHY THIS SKILL?`, rejected alternatives with `WHY NOT X?`, and relevance to the finding/phase. Reference it from the execution record and from the `ANALYSIS` / Gate-1 block.
