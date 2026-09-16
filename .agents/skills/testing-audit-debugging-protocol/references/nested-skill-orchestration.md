# Nested Skill Orchestration

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever discovery, selection, planning, or invocation touches a **nested skill** (a specialist living under `./nested-skills/`). It extends, and does not replace, `skill-discovery.md`, `skill-selection.md`, `capability-registry.md`, and `tool-orchestration.md`.

**The core rule:** this skill's `SKILL.md` has zero hard-coded knowledge of which nested skills exist. Everything below is discovered from `./nested-skills/` per `nested-skills.config.json`. Adding, replacing, or removing a nested skill is a filesystem/config change — never an edit to `SKILL.md` or this reference.

---

## 1. Discovery (extends `skill-discovery.md`)

Nested skills are a fourth discovery source, checked **first**:

```
1.0 Nested skills   — ./nested-skills/<id>/SKILL.md (+ optional manifest.json)
1.1 Global skills    — as in skill-discovery.md §1.1
1.2 Project-local skills — as in skill-discovery.md §1.2
1.3 Project tools    — as in skill-discovery.md §1.3
```

At the start of any task, before building the capability shortlist:

```
READ nested-skills.config.json
SCAN nested-skills.root (default ./nested-skills), recursive if configured
FOR EACH candidate directory:
  SKILL.md present?      NO  → skip
                          YES → manifest.json present?
                                  YES → validate against schemas/nested-skill-manifest.schema.json
                                          invalid → log a discovery warning, do NOT register, continue
                                          valid   → register with full capability metadata
                                  NO  → derive minimal metadata from SKILL.md frontmatter
                                          (capabilities unknown until declared or observed)
BUILD capability index: capability → [nested skill ids]
```

Ignore `_template-skill/` and anything matched by `nested-skills.config.json`'s `discovery.ignore`.

**Change detection.** Compare each skill's source hash / manifest version against
`.audit/memory/nested-skill-registry.json`. If different, log:

```
NESTED SKILL UPDATE DETECTED
Skill: <id>   Previous: <x>  →  Current: <y>
Action: re-register, rebuild capability index
Impact: <note if an in-progress Nested Skill Plan needs revalidation>
```

A skill that fails validation is not silently dropped — record it:

```
NESTED SKILL DISCOVERY WARNING
Path: ./nested-skills/<dir>/
Problem: <what failed>
Status: NOT REGISTERED
```

---

## 2. Registration (extends `capability-registry.md`)

Register each discovered nested skill in the same capability registry as any other candidate, with `source: "nested skill"` and these additional fields drawn from its manifest:

| Field | From |
|---|---|
| `capabilities` | `manifest.json.capabilities` |
| `read_only_safe` / `change_capable` | `manifest.json.mutation.readOnly` / `.changeCapable` |
| `requires_gate_2` | `manifest.json.mutation.requiresGate2` |
| `may_create_scripts` | `manifest.json.scripts.mayCreate` |
| `may_delegate` | `manifest.json.delegation.mayInvokeNestedSkills` |
| `version` / `source_hash` | discovery-time provenance |

Reputation accrues exactly as in `capability-registry.md` §3 — nested skills are not exempt from earning or losing reputation through their own execution history.

---

## 3. Planning & the Level-A gate (see `SKILL.md` §4a)

Before invoking *any* nested skill — read-only or change-making — present the **Nested Skill Execution Plan** (`SKILL.md` §4a, `templates/nested-skill-plan.md`). This is the one place nested skills are held to a stricter bar than ordinary read-only tool use: normal project tools may run read-only without prior approval per `tool-orchestration.md`, but a nested skill's *first* invocation on a given finding always gets a named, justified plan first. This is deliberate — nested skills are your controlled specialist library and the user should always see the roster in play before it runs, not just in the log afterward.

Exception: if the user has a **declared mapping** (`skill-mapping.md`) or gave a standing instruction earlier in this session covering this exact kind of finding, follow it and proceed without re-presenting the plan — but still record the invocation normally.

Every proposed script is change-making (see `tool-orchestration.md` §1.2 — creating a file is a mutation) and needs Gate 2 in addition to appearing in the plan. Use `templates/nested-skill-plan.md` for the plan and reference each script by an id (e.g. `SC-001`) with: path, purpose, why existing tooling/tests can't answer this, expected output, and lifecycle status (`PROPOSED → JUSTIFIED → APPROVED → CREATED → EXECUTED → EVIDENCE CAPTURED → RETAINED | REMOVED`). Record removals with a reason, e.g. "converted into permanent regression test `tests/x`."

---

## 4. Delegation limits (no recursive chaos)

* A nested skill is a **leaf specialist by default**. It may not invoke another nested skill unless its own `manifest.json` sets `delegation.mayInvokeNestedSkills: true` with an explicit `allowedChildren` list.
* `nested-skills.config.json`'s `execution.maxDelegationDepth` (default 2) is a hard ceiling enforced regardless of manifest declarations.
* A nested skill never decides on its own to modify the project. It returns findings/evidence/recommendations to this orchestrator; the orchestrator runs any fix through Gate 1 then Gate 2 before invoking a change-making capability with a named, narrow scope.
* If a nested skill discovers mid-execution that it needs to touch a file outside an approved Gate 2 scope, it stops; the orchestrator requests a fresh Gate 2 approval for the expanded scope rather than proceeding.

## 5. Resolution priority & capability gaps

```
1. User-directed nested skill   (obey — don't re-derive criteria)
2. Matching nested skill        (from the registry)
3. Project-local capability
4. External/global skill
5. Generic tool
```

**Overlap between two nested skills.** If more than one nested skill plausibly covers a
finding, don't pick silently and don't re-ask every time it comes up. Ask the user once which
one should own that domain, then **write the answer into `skill-mapping.md`** as a declared
mapping (per `skill-selection.md` §5) so it's a `User Directed` selection from then on. An
ambiguity resolved once and not persisted just resurfaces at the next similar finding —
persisting it is what actually fixes the overlap.

If step 4 or 5 is reached, this is a **capability gap** and must be surfaced, not used silently:

```
CAPABILITY GAP
No nested skill provides: <capability>
External candidate: <skill, if any>
Reason it's needed: <specific>
Approval: required — fold into the Nested Skill Execution Plan, don't invoke separately
```

## 6. Execution records (extends the `SU-###` format)

```
EXECUTION: SU-###
Parent Skill:        testing-audit-debugging-protocol
Child Skill:         <nested skill id>
Child Skill Version: <version>
Invocation Type:     nested-skill
Parent Selection:    SS-###
Child Selection:     NS-###
Purpose:
Scope:
Type:                read-only | change-making
Approval:            none | nested-skill-plan | Gate 1 | Gate 2
Tools/Scripts Used:
Evidence Produced:   E-###, ...
Findings:            F-###, ...
Outcome:             success | partial | failed
```

Append to `.audit/memory/skill-usage.jsonl` per `skill-execution.schema.json`, plus these dedicated nested-skill logs:

```
.audit/memory/nested-skill-registry.json     (generated at each discovery pass — never hand-edit)
.audit/memory/nested-skill-selection.jsonl
.audit/memory/nested-skill-usage.jsonl
.audit/memory/nested-skill-updates.jsonl
.audit/memory/script-plans.jsonl
```

Version every execution record with `skillId@version` and its source hash at the time it ran, so old audits stay reproducible even after a nested skill is later updated.

## 7. Regression must use the same specialist

If `<nested-skill-x>` found or fixed an issue, close it out by re-invoking `<nested-skill-x>` in its read-only/review mode to confirm the specific issue is resolved — don't rely on the general test suite alone.

## 8. Nested skills must stay leaf specialists, not re-implementations

A nested skill owns its domain analysis only. It must **not** re-implement approval gates, the deployment gate, discovery, correlation, or audit memory — those stay owned by this orchestrator. If a nested skill's `SKILL.md` starts describing its own approval flow, that's a sign it was copied in wholesale rather than adapted — trim it down to domain knowledge plus what it hands back to the parent.
