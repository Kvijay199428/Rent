# Verification & Drift Detection (Mechanical, Not Honor-System)

This reference is part of the **testing-audit-debugging-protocol** skill. Load it before the
final deployment gate, and any time you want to sanity-check that the audit trail actually
matches what the protocol requires — not just what was claimed in the final report.

## Why this exists

Every other reference in this skill describes rules the model is *instructed* to follow —
write an execution record, get Gate 2 before mutating, justify a script. None of that is
mechanically checked anywhere else. Over a long session, instruction-following can drift: a
gate gets summarized instead of shown, a log write gets skipped under time pressure, a script
gets created "just this once" without the paperwork. This step exists to catch that
*mechanically*, from the artifacts a session actually produced, rather than trusting the
session's own narration of itself.

## What it checks

Run `scripts/validate_audit_memory.py --project-root <project>` against the project's
`.audit/memory/` directory. It checks, without needing an LLM in the loop:

1. Every id (`SU-###`, `SS-###`, `F-###`, `E-###`, `NS-###`, `SC-###`) matches its expected
   pattern — a malformed id usually means a hand-typed record rather than one generated
   consistently.
2. **No change-making execution record has `approval_gate` of `none`.** This is the single
   most important check — it's the mechanical version of "no unauthorized edits."
3. Every nested-skill execution record carries its parent/child linkage fields (`parent_skill`,
   `child_skill_version`, `parent_selection_id`, `child_selection_id`).
4. Every script that reached `CREATED` or later in its lifecycle shows `approval: "Gate 2
   required"` — catches a script that got created without going through the plan.
5. Every `REMOVED` script records a `removal_reason` — catches silent deletions.
6. A nested-skill plan entry marked `CHANGE-MAKING` and `approved` has a linked execution
   record that actually shows `Gate 2` — catches the plan/execution getting out of sync.
7. Findings marked `FIXED`/`VERIFIED` cite execution or evidence ids (warning, not blocking —
   some projects track evidence differently).
8. No duplicate ids in the nested-skill registry.
9. Any `schema-registry-checks.jsonl` line with a non-empty `namingViolations` or
   `duplicateOrConflicting` carries a matching `relatedFindingId` — a database check that
   found a naming violation or conflict but has no corresponding entry in `findings.jsonl` is a
   silent-omission gap, the same class of problem as an unlogged Gate 2. See
   `references/database-schema-standards.md` §3.

## When to run it

* **Mandatory, blocking, before the final deployment gate** (`deployment-gate.md` §4) — a
  non-zero exit code is itself a P1+ finding and must be resolved or explicitly accepted before
  recommending `READY`.
* Optionally at the end of any individual fix, if you want tighter feedback than waiting for
  the final gate.

## What a violation means

A violation is evidence the protocol wasn't actually followed on that record, not just a
cosmetic issue. Treat it as a real audit finding:

```text
FINDING
Severity: P1 (protocol integrity)
Observed: validate_audit_memory.py reported <violation text>
Expected: every change-making execution shows Gate 2 approval
Root cause: <investigate — was the gate actually shown and just not logged, or genuinely skipped?>
```

Don't paper over a violation by editing the log record to make it pass — that defeats the
point. Fix the underlying process (get the missing approval retroactively and document that
it was retroactive, or acknowledge the record was wrong and say so) rather than silently
correcting history.

## Limits (be honest about what this doesn't do)

This validates the *shape and internal consistency* of what got logged. It cannot verify that
a logged Gate 2 approval was actually shown to the user and actually approved — it can only
tell you the record *claims* one happened. It also can't catch a case where nothing was logged
at all (an execution that never made it into `skill-usage.jsonl`). Real assurance against that
still depends on faithful instruction-following plus the user noticing an unexplained change.
This script narrows the honor-system gap; it doesn't close it entirely.
