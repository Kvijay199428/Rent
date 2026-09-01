# Capability Registry

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it after discovery and whenever you need the structured inventory of what is available.

The registry is the **structured inventory** of every skill/tool the orchestrator knows about, with metadata that makes selection mechanical rather than guessed.

---

## 1. What is Registered

Each registered capability carries:

| Field | Description |
| --- | --- |
| name | identifier |
| source | global skill / project-local skill / project tool / built-in tool / connector |
| domain | expertise area (test execution, security, UI design, spreadsheet, PDF, data analysis, performance, web, ...) |
| good_for | one-line capability |
| read_only_safe | can it run without mutating the project? (yes/no/unknown) |
| change_capable | is it able to write/edit/deploy? (yes/no/unknown) |
| reputation | Low / Medium / High / Trusted (see § 3) |
| declared_mapping | user-declared category→instrument, if any |
| history | recent uses + outcomes (derived from audit memory) |

---

## 2. Storage

The registry may be:

* **Decorated in memory (default)** — the orchestrator holds it for the session, seeded from discovery, and persists it as audit memory.
* **Persisted as a project registry** — an optional `.audit/registry/` (or `.audit/memory/capability-registry.json`) the project owns and reuses across sessions.

**Design rule:** *Global skill = methodology; Project memory = experience.* The registry's persistent, project-specific learning lives in the project's `.audit/` directory, never inside the global skill directory.

---

## 3. Reputation Score

Reputation is derived from the execution history in audit memory:

* **+1** per successful (evidence-producing, no-error) use
* **−1** per failed use (error, wrong result, dropped evidence)
* **0** for a neutral / recorded-but-inconclusive use
* Recent uses weighted higher than old (decaying window)

Score is normalized to a printable band:

| Band | Meaning |
|------|---------|
| Low | poor or absent track record |
| Medium | some uses, mixed results |
| High | consistent successful use |
| Trusted | many successful uses, domain-proven |

Reputation informs selection (Criterion 6 in `skill-selection.md`) but **never overrides a user-declared mapping.** It is reported to the user (in the Gate‑1 block) so they can weigh it.

Reputation state is stored in `.audit/memory/reputation.json`.

---

## 4. Registry Rules

* Register only candidates **plausibly relevant** to this audit, not every skill in existence.
* Keep the registry in sync with discovery and with the execution history (each invocation updates the capability's last-used/outcome).
* The registry is documentation / project memory — updating it never requires approval.
* Never let registry presence imply permission: a registered capability still needs a selection reason to be *used*, and a change-making use still needs Gate 2.
