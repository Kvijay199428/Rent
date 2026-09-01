# Skill & Tool Discovery

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it at the start of a task and again whenever you reach a decision point where new capabilities might matter.

Discovery is the **read-only enumeration of what is available** to you for this audit. It never modifies anything. Its output is a **capability shortlist** that you then register (see `capability-registry.md`) and select from (see `skill-selection.md`).

---

## 1. What Counts as "Available"

Discover from three sources, in this order:

### 1.1 Global skills
Skills installed for the environment (available to every project):
* Public skills (document/spreadsheet/PDF generation, frontend design, data analysis, security, web/performance, product self-knowledge, etc.)
* Private or org-provided skills
* Example/community skills
* Any skill visible in your current skills listing, regardless of source

### 1.2 Project-local skills
Skills shipped inside the repository or project being audited:
* A `skills/`, `.agents/skills/`, or `.claude/skills/` directory
* A committed `SKILL.md` or skill manifest
* Org-provided project skills
* Any skill defined by the project that a global install does not provide

### 1.3 Project tools
Test runners, linters, build scripts, migration tools, connectors, and any binary/script the repository declares:
* `package.json` scripts, `Makefile` targets, `justfile`, `Earthfile`
* CI config (GitHub Actions, GitLab CI, etc.)
* `tsconfig`/`eslint`/typecheck tooling
* Database migration tools, seed scripts
* Any project-specific harness documented in the repo

These count as "local tools" even if not packaged as a formal skill — and per the selection criteria, a project's own tool is usually the best fit for a task-native analysis.

---

## 2. Discovery Steps

1. **Enumerate** each source above and produce a flat list of candidate capabilities.
2. **Annotate** each candidate with a one-line *what it's good for*, its *source*, and an initial guess at *read-only safety*.
3. **Record** the shortlist in `skill-usage-log.md` and/or the capability registry (`.audit/memory/capability-registry.json`). Discovery itself is logged (read-only, no approval).
4. **Refresh** the shortlist whenever the task changes phase or a new finding widens the domain (a security finding may surface a security skill you did not initially list).

---

## 3. Discovery Logging

Each discovery pass should be recorded. Minimal record per candidate:

| Field | Example |
| --- | --- |
| capability | `web-perf` |
| source | global skill |
| category | performance / web |
| good_for | measure Core Web Vitals, LCP/INP/CLS |
| read_only_safe | yes |
| initial_relevance | MEDIUM (only if a perf question arises) |

Record the discovery action itself (e.g. `SU-001 | DISCOVERY | enumerate global + project skills | read-only | produced 14 candidates`).

---

## 4. Discovery Rules

* Discovery is **read-only** — never invoke a candidate to "test" it during discovery unless it is genuinely needed for analysis.
* Do **not** register every skill in the world — only those plausibly relevant to this audit. Narrow by domain as the audit narrows.
* A candidate you identify but do not use is still **recorded as a rejected/considered alternative**, so `WHY NOT X?` can be answered later (see `skill-selection.md`).
* Never turn discovery into a change. Finding a useful skill is **not** permission to invoke it against the project.
