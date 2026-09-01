# Skill Selection Template

Use this template to document every non-trivial selection decision.

```
SELECTION: SS-###

Finding / Phase: F-### / <phase>

Candidates evaluated:
- <name> — source: <global/project-local/project tool> — domain_match: <y/n> — risk_match: <y/n> — task_native_fit: <y/n> — precedent: <y/n> — reputation: <band> — minimalism: <y/n>

Selected: <name>

Mode: <Automatic | User Directed | User Approved>

WHY THIS SKILL? <name> chosen for <finding/phase> because <criteria 1..3 that apply>; alternatives: <alt1>, <alt2>; decided by <mode>.

Rejected alternatives:
- <alt1>: WHY NOT <alt1>? <decisive reason>
- <alt2>: WHY NOT <alt2>? <decisive reason>

Execution record: SU-###
```

Fill in and append to `skill-usage-log.md` and write a corresponding JSONL record to `.audit/memory/skill-usage.jsonl` per `schemas/skill-selection.schema.json`.