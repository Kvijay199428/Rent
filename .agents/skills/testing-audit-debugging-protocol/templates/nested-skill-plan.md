# Nested Skill Execution Plan Template

Use this before invoking any nested skill (from `./nested-skills/`) — read-only or change-making. This precedes Gate 1/Gate 2, which still apply to any actual fix.

```
NESTED SKILL EXECUTION PLAN

Audit/Issue ID: <AUD-### / F-###>
Objective: <one or two sentences>

NESTED SKILL: NS-###
  Skill:              <nested skill id>
  Capability:         <capability from its manifest.json>
  Purpose:            <what it will concretely do>
  Why necessary:      <specific evidence gap this fills>
  Expected output:    <evidence/findings it should produce>
  Scripts proposed:   <SC-### id(s), or "none">
  Files touched:      <list, or "none">
  Mutation status:    <READ-ONLY | CHANGE-MAKING>

(repeat NESTED SKILL block for each specialist being proposed together)

APPROVAL STATUS: waiting for user approval — nothing invoked yet.
```

Fill in and append to `skill-usage-log.md`, plus a JSONL record to `.audit/memory/nested-skill-selection.jsonl` per `schemas/nested-skill-plan.schema.json`. If a script is proposed, also fill in `templates/script-plan.md` for it and remember it needs Gate 2 in addition to appearing here.

If the user has a declared mapping or standing instruction covering this exact kind of finding, note that instead of re-presenting the full plan, and proceed per its scope limits.
