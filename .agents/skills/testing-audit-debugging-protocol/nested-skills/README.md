# nested-skills/

Drop one folder per specialist skill here. The parent orchestrator (`../SKILL.md`, guided by
`../references/nested-skill-orchestration.md`) auto-discovers everything in this directory per
`../nested-skills.config.json` — you never edit the parent to add, replace, or remove a skill.

## Add a skill
1. Copy `_template-skill/` to a new folder named after your skill's id, e.g. `security-audit/`.
2. Fill in `SKILL.md` (required) and `manifest.json` (optional, but without it the orchestrator
   can only guess your capabilities from prose — strongly recommended).
3. Add any `references/`, `schemas/`, `templates/`, `scripts/`, or `data/` it needs inside its
   own folder.
4. Next audit, the orchestrator discovers, validates, and registers it automatically.

## Update a skill
Edit its files (or bump `manifest.json`'s `version`). The orchestrator detects the change via
version + source hash and re-registers it; past audit records keep pointing at whichever
version they actually ran against.

## Remove a skill
Delete its folder. It drops out of the registry on the next discovery pass; historical audit
records that used it are untouched.

## Rules every nested skill must follow
- **Leaf specialist by default.** It doesn't call other nested skills unless its own
  `manifest.json` sets `delegation.mayInvokeNestedSkills: true` with an explicit
  `allowedChildren` list — and even then `maxDelegationDepth` in the config caps it.
- **Never decides to modify the project on its own.** It reports findings/evidence back to the
  parent; the parent runs any fix through Gate 1 → Gate 2 before invoking a change-making
  capability with a named, narrow scope.
- **Change-capable manifests need Gate 2** on every mutating invocation, no matter what the
  Nested Skill Execution Plan approved at the planning stage.
- **Scripts are never created silently.** Every proposed script gets its own entry per
  `../references/script-planning.md`-equivalent rules in
  `../references/nested-skill-orchestration.md` §3, and needs Gate 2.
- **Own your domain, not the orchestrator's job.** Don't re-implement approval gates,
  discovery, correlation, or audit memory inside a nested skill — that's the parent's job.

See `_template-skill/` for the exact shape to copy.
