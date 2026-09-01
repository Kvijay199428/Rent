# Upgrade Plan — testing-audit-debugging-protocol (v2 Orchestrator)

## Goal

Extend the existing testing/audit/debugging skill into a full **Testing Audit Orchestrator**: a capability that can (a) **discover** the skills and tools available on a machine and in a project, (b) **register** them in a capability registry with metadata, (c) **select** the right instrument for each phase of an audit with a recorded, explainable reason, (d) **execute** those instruments under a read-only audit mode by default, (e) **remember** every selection and invocation in durable audit memory, (f) **correlate** findings into evidence-backed clusters, (g) build an **evidence graph** linking findings → evidence → skill/tool records → files, and (h) gate every change behind **dual approval gates** (Analysis Approval, then Code Modification Approval).

The core discipline of the original skill — **never silently turn discovery into a change** — is preserved and extended to skill/tool invocation, not just code edits. The orchestrator may discover, select, invoke, and coordinate skills and tools during read-only audit mode, but every selection must have an explainable reason, every invocation must produce an execution record, every finding must have evidence, every proposed modification must have a change budget, and **no implementation change may occur without explicit user approval.**

---

## 1. Architecture Overview

The orchestrator operates as a **skill** (your own methodology) that sits **above** other skills and tools. It is not a replacement for them; it is the controller that decides which one fits a given audit question, calls it, records what it did, and reports the result through the same approval-gated pipeline used for code changes.

```
                    ┌─────────────────────────────────────────────┐
                    │        TESTING AUDIT ORCHESTRATOR           │
                    │  (this skill = the constitution)            │
                    └──────┬──────────────────────────┬───────────┘
                           │  discover + register      │  give tasks
                           ▼                          ▼
                 ┌────────────────────┐      ┌────────────────────┐
                 │  CAPABILITY        │      │  EXECUTION ENGINE  │
                 │  REGISTRY          │      │  (invokes skills + │
                 │  (skills + tools)  │      │   tools)           │
                 └────────────────────┘      └─────────┬──────────┘
                        ▲                             │ execution records
                        │ discover                    ▼
                 ┌──────┴──────────┐          ┌────────────────────┐
                 │  GLOBAL SKILLS  │          │  AUDIT MEMORY      │
                 │  PROJECT SKILLS │          │  (.audit/memory/)  │
                 │  PROJECT TOOLS  │          │  findings/evidence │
                 └─────────────────┘          │  correlation/graph │
                                              └────────────────────┘
```

**Master rule (the user's exact new rule):**

> The orchestrator may discover, select, invoke, and coordinate skills and tools during read-only audit mode, but every selection must have an explainable reason, every invocation must produce an execution record, every finding must have evidence, every proposed modification must have a change budget, and no implementation change may occur without explicit user approval.

---

## 2. Operating Modes

The orchestrator moves through discrete modes. Each mode has a defined entry condition and a defined exit condition. Read-only modes require no approval; change modes require the corresponding approval gate.

| # | Mode | Purpose | Requires approval? | Exit condition |
|---|------|---------|--------------------|----------------|
| 1 | **DISCOVERY** | Enumerate available global skills, project-local skills, and project tools; build the candidate inventory | No (read-only) | Capability shortlist assembled |
| 2 | **AUDIT (read-only, default)** | Understand the app, establish baseline, run existing tests, inspect — all non-mutating | No (read-only) | Findings documented with evidence |
| 3 | **SPECIALIST** | Delegate a sub-analysis to a selected skill/tool (read-only use of a specialist) | No if read-only | Execution record produced |
| 4 | **ROOT-CAUSE** | Analyze findings into root-cause hypotheses with confidence | No (read-only) | Findings classified CONFIRMED/LIKELY/SUSPECTED |
| 5 | **ANALYSIS APPROVAL** | User approves the analysis conclusions and the proposed fix *plan* (gate 1) | **Gate 1 yes** | Fix plan approved |
| 6 | **FIX** | Modify code with an approved skill/tool | **Gate 2 yes** | Change applied within budget |
| 7 | **VERIFICATION** | Re-test, regression, verification per the protocol | No (read-only) | Evidence of fix produced |
| 8 | **DEPLOY GATE** | Final readiness decision | No, but reported | Deployment STATUS delivered |

The two **approval gates** split what the original skill treated as a single "fix it" gate:

* **Gate 1 — Analysis Approval:** approve *what you concluded* (the fix plan: root cause, proposed fix, files, skill/tool selections, change budget) *before any plan is believed.* No code is touched.
* **Gate 2 — Code Modification Approval:** approve *actually running* the change (editing the named files, invoking the named change-making skill/tool) within the already-approved plan.

Both gates are explicit and separate. The same block may request both, but a user saying only "yes, your analysis is right" does **not** authorize code changes, and "yes, go ahead and fix it" presumes gate 1 was already granted.

---

## 3. Discovery Engine

Discovery is the read-only enumeration of what is available. It runs at task start and again at every AUDIT / SPECIALIST / FIX decision point in case new capabilities appeared.

### Discovery sources

1. **Global skills** — skills installed for the environment (e.g. the opencode `skills/` directory, a user-level skills repo). These are available to every project.
2. **Project-local skills** — skills shipped inside the repository or project being audited (a `skills/`, `.agents/skills/`, or `.claude/skills/` directory, a committed `SKILL.md`, org-provided project skills).
3. **Project tools** — test runners, linters, build scripts, migration tools, connectors, and any binary/script the repository declares (in `package.json` scripts, `Makefile`, CI config, `justfile`, etc.). These count as "local tools" even if not packaged as a formal skill.

### Discovery output

Discovery produces a **capability shortlist** — a scored list of `{capability, domain, source, confidence}` entries. This is recorded (in the capability registry or in audit memory) so the audit never rediscovers from scratch and never silently forgets a candidate.

---

## 4. Capability Registry

The registry is the structured inventory of every skill/tool the orchestrator knows about, with metadata that makes selection mechanical rather than guessed.

### What is registered

* Name / identifier
* Source (global skill / project-local skill / project tool / built-in tool / connector)
* Domain of expertise (test execution, security, UI design, spreadsheet, PDF, data analysis, etc.)
* What it is good for (one-line capability)
* Read-only safety (can it run without mutating the project?)
* Change-making capability (is it able to write/edit/deploy?)
* Reputation score (see § 8)
* Declared user mappings (see § 6)
* Last-used / outcome history (derived from audit memory)

### Registry storage

The registry may be:
* **Decorated in memory** — the default: the orchestrator holds it for the session, seeded from discovery, maintained in audit memory JSON.
* **Persisted as a project registry** — an optional `.audit/registry/` store the project owns and reuses across sessions.

The rule: **Global skill = methodology; Project memory = experience.** The registry's persistent, project-specific learning lives in the project's `.audit/` directory, never inside the global skill directory.

### Schema

See `schemas/capability-registry.schema.json`.

---

## 5. Selection Engine

Selection answers: *"For this audit question / this finding, which skill or tool should I use, and why?"*

### Selection modes

The orchestrator supports three selection modes. The mode is chosen by the user (or defaults) and recorded:

| Mode | Behavior | When used |
|------|----------|-----------|
| **Automatic** | The engine picks the top-ranked skill/tool per Selection Criteria and proceeds (read-only) or proposes (change-making). | Trusted, established domains; user pre-approved a mode. |
| **User Directed** | The user declares the mapping up front (`skill-mapping.md` / conversation). The mapping always wins. | User has a known preference. |
| **User Approved** | The engine scores candidates, but the final pick is presented to the user for confirmation before it is used (read-only or change-making). | High-stakes, ambiguous, or first-time selections. |

### Selection Criteria (weighed, in order)

1. **User-declared mapping wins.** Check `skill-mapping.md` and the conversation. Honor it without re-deriving criteria.
2. **Domain / file-type match.** Does the artifact match the skill's stated domain? (`.docx` → docx skill; broken formula in `.xlsx` → spreadsheet skill; UI defect → frontend-design skill; security finding → security skill.)
3. **Risk-area match.** Security findings → security-focused instrument; data-integrity findings → differential-verification / data-analysis instrument.
4. **Task-native fit.** Prefer the project's own declared tooling (its test runner, its linter, its build script) over a generic substitute.
5. **Precedent.** A skill/tool already used successfully for a similar issue in this project (from audit memory) beats an unproven substitute.
6. **Reputation.** Prefer higher reputation score (§ 8) when other criteria are equal.
7. **Minimalism.** If the task can be done with what already exists, do not reach for an extra skill/tool. Orchestration is for when a specialist genuinely improves accuracy, evidence quality, or the fix.

### Explainable reason: `WHY THIS SKILL?`

Every non-trivial selection must be expressed as a one-line reason of the form:

> **`WHY THIS SKILL?`** `<capability>` chosen for `<finding/phase>` because `<criterion 1..3 that apply>`; alternatives considered: `<alt1>, <alt2>`; decided by `<mode>`.

### `WHY NOT skill X?`

When a plausible alternative was considered and rejected, record a short **`WHY NOT <X>?`** line stating the decisive reason (weaker domain match, lower reputation, no precedent, change-making when read-only was preferred, etc.). This makes rejections auditable too.

---

## 6. User-Directed Mapping (`skill-mapping.md`)

Optional durable policy file. Create it as soon as the user states a preference, or when two-or-more skills/tools genuinely tie. A declared mapping **always overrides auto-selection** (Selection Criterion 1).

Schema and example are in `references/skill-selection.md`.

---

## 7. Audit Memory (project-side)

Audit memory is the durable, project-scoped store of everything the orchestrator learned and did. It lives in **`.audit/`** in the project being audited — **not** inside the global skill — so it survives across sessions and is visible/editable by the user like the rest of the audit trail.

```
<project>/.audit/
├── memory/
│   ├── capability-registry.json      (optional persisted registry)
│   ├── skill-usage.jsonl             (append-only execution records; supersedes skill-usage-log.md rows)
│   ├── findings.jsonl                (append-only findings with evidence)
│   ├── correlation.json              (finding clusters / X-not-Y records)
│   └── reputation.json               (derived reputation scores)
├── evidence/                         (raw evidence blobs: logs, screenshots, captures)
└── (side-by-side with the existing markdown deliverables)
```

The existing markdown deliverables (`test-audit-task.md`, `audit-plan.md`, `audit-log.md`, `bucket-list.md`, `skill-usage-log.md`, `skill-mapping.md`) continue to be the human-readable view. The `.audit/memory/` JSON/JSONL stores are the machine-readable, queryable view. They must stay in sync.

**Design rule:** *Global skill = methodology; Project memory = experience.* Never write experience into the global skill directory.

---

## 8. Skill Reputation & Confidence

### Reputation score

Each registered skill/tool carries a reputation derived from its history in audit memory:

* **+1** per successful (evidence-producing, no-error) use
* **−1** per failed use (error, wrong result, dropped evidence)
* **0** for a neutral/recorded-but-inconclusive use
* Recent uses weighted higher than old ones (decaying window).

Score is normalized to a printable band: **Low / Medium / High / Trusted**. It informs selection (Criterion 6) and is reported to the user, but never overrides a user-declared mapping.

### Confidence thresholds

Applied to findings and root-cause hypotheses. Findings are never asserted without a confidence label; confidence below `INSUFFICIENT` is not reportable as a finding without more evidence.

| Range | Label | Meaning |
|-------|-------|---------|
| 0–49 | **INSUFFICIENT** | Needs more evidence; not reportable as a confirmed finding |
| 50–69 | **LOW** | Plausible, weakly supported |
| 70–84 | **MEDIUM** | Reasonably supported, some gaps |
| 85–94 | **HIGH** | Strongly supported, reproducible |
| 95–100 | **VERY HIGH** | Directly observed, fully reproducible, independent confirmation |

`CONFIRMED` findings must sit at HIGH or above. `LIKELY` at MEDIUM or above. `SUSPECTED` may be LOW.

---

## 9. Evidence Graph

The evidence graph links **findings → evidence → execution records → files → skills/tools**. It is the traceability backbone: every finding points to the evidence that supports it, the skill/tool invocation that produced that evidence, and the files involved.

A node for a finding carries: id, severity, confidence, root-cause status, evidence references. An evidence reference points to a raw blob or captured output with a producer (skill/tool execution record). An execution record points to the skill/tool and the files touched.

The graph is materialized in `schemas/evidence-graph.schema.json` and written to `.audit/memory/` (or reconstructed from the `.jsonl` stores). It lets the user (or a future audit) answer: *"How do I know this finding is true?"* by walking finding → evidence → execution record → skill/tool → file.

---

## 10. Finding Correlation

The correlation engine groups related findings and records explicit **X-not-Y** relationships.

### Correlation types

* **Same-root-cause cluster:** multiple symptoms trace to one root cause. Cluster id assigned; findings reference it.
* **Duplicate:** same defect reported twice; keep one canonical, note the other.
* **Related-but-distinct:** findings share a surface (same file/feature) but different causes; cross-reference, do not merge.
* **CONFLICTS / CONTRADICTS:** two findings assert incompatible things (e.g. "field is required" vs "field must be optional"). Recorded explicitly with an `X-not-Y` relation pending resolution.
* **BLOCKS / BLOCKED-BY:** ordering dependency between fixes.

### `X-not-Y` record

> Finding `F3` **contradicts** `F2` on the validation rule for `waterCharge`. Both are CONFIRMED at the evidence level; the contradiction is unresolved and **masked** (`MASK: {F2, F3}`) until resolved by the user. No fix proceeds on either until the conflict is resolved.

Correlation output is `schemas/finding-correlation.schema.json` / `correlation.json`.

---

## 11. Read-Only Audit Mode (default)

The default posture is **read-only**: the orchestrator may invoke skills and tools to *inspect, run existing tests, read, search, view, analyze* without asking permission — but every such invocation still produces an execution record, and anything that writes to the project is change-making and gated.

### Read-only (no approval, must log)

* Running existing test/lint/build/typecheck commands
* Static analysis, reading files, inspecting structure
* Searching docs/specs/web for expected behavior
* A skill used purely to read/inspect an artifact (read a `.docx`, check a spreadsheet formula)
* Viewing screenshots to compare expected vs. actual UI

### Change-making (approval required — Gate 2)

* Any skill/tool invocation that writes, edits, generates, or deletes a file in the project
* Any write-capable connector (ticket creation, deployment, migrations, package installs)
* Any skill whose output is meant to directly become the fix

When unsure which bucket an action belongs in, treat it as change-making and ask.

### Child-skill read-only enforcement

Any child skill/tool invoked by the orchestrator is subject to the same read-only default. If a child appears able to mutate the project, the orchestrator must:
1. Confirm the child is being invoked in read-only scope (or that its mutation is explicitly approved via Gate 2).
2. Record the read-only/change-making classification in the execution record.
3. Refuse to let a child mutate the project outside an approved change budget.

---

## 12. Execution Records

Every skill/tool invocation produces an execution record appended to `.audit/memory/skill-usage.jsonl` (and mirrored into `skill-usage-log.md` for human review). Schema in `schemas/skill-execution.schema.json` and `schemas/tool-execution.schema.json`.

Mandatory fields (match the original `skill-usage-log.md` schema, extended):

| Field | Description |
| --- | --- |
| id | `SU-001`… |
| timestamp | when invoked |
| phase | DISCOVERY / AUDIT / SPECIALIST / ROOT-CAUSE / FIX / VERIFICATION / DEPLOY GATE |
| capability | skill or tool name |
| source | global / project-local / project tool / built-in / connector |
| selection_reason | the `WHY THIS SKILL?` line |
| alternatives_considered | `WHY NOT <X>?` lines |
| selection_mode | Automatic / User Directed / User Approved |
| related_finding | finding id(s) or related issue id |
| purpose | one sentence |
| type | read-only / change-making |
| approval_gate | none (read-only) / pending / gate1_approved / gate2_approved / declined |
| files_touched | files read or modified |
| outcome | evidence produced / fix applied / error |
| reputation_delta | +1 / −1 / 0 |

---

## 13. Dual Approval Gates

### Analysis Approval (Gate 1) — "plan before action"

Present the full `ANALYSIS` block: root cause, confidence, proposed fix, affected files, skill/tool selections with `WHY THIS SKILL?` reasons, change budget, regression risk. Ask: *"Is this analysis and fix plan approved?"* No code changes.

### Code Modification Approval (Gate 2) — "act on the approved plan"

Present the `CODE MODIFICATION` block: the exact files to modify, the change-making skill(s)/tool(s) to invoke (with execution record references), the change budget ("these N files, these M skills/tools, no others"). Ask: *"May I apply this change?"*

Approval semantics:
* "proceed / fix it / yes, apply" after a Gate‑1 block authorizes the **analysis and plan only**. A separate explicit authorization is required to actually modify code (or an explicit combined "analyze and fix it" that grants both).
* Approval covers **exactly** the files and skills/tools named. A different file or a different skill/tool discovered later needs its own Gate‑2 approval.
* If investigation reveals an additional file/skill/tool is required, stop and ask again (change budget).

Simplification for low-risk, user-requested cases: the user may pre-grant "combined" approval ("audit and fix it") that covers both gates at once, but the two-gate structure must still be recorded.

---

## 14. Audit Replay

Because every selection, invocation, finding, correlation, and approval is recorded, the entire audit can be **replayed** — either for the user or in a future session — by walking the `.audit/memory/` stores in order:

1. What was discovered and registered
2. What was selected, and why (`WHY THIS SKILL?`)
3. What was invoked, with what outcome (execution records)
4. What findings were produced, with their evidence and confidence
5. How findings correlate (`X-not-Y`, clusters)
6. What was approved at each gate and what actually changed (audit trail of mutations)

Replay is useful for reviewing an audit after the fact, for on-boarding a fresh session to an in-progress audit, and for regression-style "did we fix what we said we fixed."

---

## 15. Phased Implementation

The upgrade is delivered in 8 phases. Each phase is independently review-able. Fidelity is "full verbatim + references": the core protocol wording is preserved and extended, with deep detail split into `references/`, `schemas/`, and `templates/`.

| Phase | Delivered | Files |
|-------|-----------|-------|
| 1. Discovery | Discovery sources + capability shortlist | `references/skill-discovery.md` |
| 2. Orchestration | Operating modes, registry, selection modes | `SKILL.md`, `references/skill-selection.md`, `references/capability-registry.md` |
| 3. Tool orchestration | Read-only vs change-making for tools, child-skill read-only enforcement | `references/tool-orchestration.md` |
| 4. Memory | `.audit/memory/` JSON/JSONL stores, sync with markdown deliverables | `references/audit-memory.md`, `schemas/*.json` |
| 5. Evidence graph | Findings → evidence → execution records → files link | `references/evidence-and-traceability.md`, `schemas/evidence-graph.schema.json` |
| 6. Correlation | Clusters + `X-not-Y` | `references/finding-correlation.md`, `schemas/finding-correlation.schema.json` |
| 7. Approval | Dual gates (Analysis + Code Modification) | `references/approval-gates.md`, `templates/approval.md` |
| 8. Replay | Walk-through of `.audit/memory/` | `references/audit-replay.md` |

---

## 16. Updated file set

```text
testing-audit-debugging-protocol/
├── SKILL.md                              (orchestrator constitution)
├── UPGRADE-PLAN.md                       (this document)
├── references/
│   ├── skill-discovery.md                (phase 1)
│   ├── skill-selection.md                (phase 2)
│   ├── capability-registry.md            (phase 2)
│   ├── tool-orchestration.md             (phase 3)
│   ├── audit-memory.md                   (phase 4)
│   ├── evidence-and-traceability.md      (phase 5)
│   ├── finding-correlation.md            (phase 6)
│   ├── approval-gates.md                 (phase 7)
│   └── audit-replay.md                   (phase 8)
├── schemas/
│   ├── capability-registry.schema.json
│   ├── skill-selection.schema.json
│   ├── skill-execution.schema.json
│   ├── tool-execution.schema.json
│   ├── finding.schema.json
│   ├── evidence.schema.json
│   ├── evidence-graph.schema.json
│   ├── finding-correlation.schema.json
│   └── approval.schema.json
└── templates/
    ├── skill-selection.md
    ├── skill-execution.md
    ├── tool-execution.md
    ├── finding.md
    ├── approval.md
    └── deployment-gate.md
```

Note: the four protocol references (`audit-documents.md`, `testing-strategies.md`, `root-cause-and-approval.md`, `deployment-gate.md`) remain part of the skill and are extended with cross-references to the new orchestrator references. The original `skill-and-tool-orchestration.md` is superseded and folded into the new split set.

---

## 17. Suggested next steps

1. Read `SKILL.md` and `UPGRADE-PLAN.md` first — they are the constitution and the architecture.
2. Skim the eight `references/` files in phase order (1→8).
3. Try it on a real audit: run DISCOVERY, then AUDIT (read-only), then observe the `WHY THIS SKILL?` reasons, execution records, findings with confidence, correlation, and the two gates.
4. The two most important things to iterate on with real findings: (a) the **dual gate** UX — does Analysis Approval vs Code Modification Approval read clearly? — and (b) the **`WHY THIS SKILL?` / `WHY NOT X?`** reasons — are they enough to let a user approve or redirect confidently?
