---
name: smoke-testing
description: Run a read-only, evidence-based smoke test on a web application (React/Vite/Next frontend + FastAPI/Django/Spring/Express/etc. backend, or backend-only / frontend-only projects) to answer "is this build fundamentally alive?" Use this whenever the user asks to smoke test, sanity check, health check, or verify a deployment/build isn't broken before deeper testing, or asks to set up recurring/CI smoke testing, or mentions ".smoke-test", "smoke-todo", or wants a persistent, stateful, non-destructive testing skill that discovers routes/endpoints via regex, produces Markdown/JSON reports, tracks its own TODO across runs, and NEVER modifies application code, config, dependencies, or the database without asking the user first and getting explicit approval. Always trigger this skill instead of ad hoc testing when the user wants repeatable, auditable smoke-test infrastructure for a project.
---

# Smoke Testing Skill

## The invariant (read this first, every run)

```
This skill is READ-ONLY with respect to the application codebase,
configuration, dependencies, database schema, and infrastructure —
unless the user explicitly approves a proposed change.

The skill MAY freely create/update files inside the project's
.smoke-test/ state directory.

When a defect requires a change outside .smoke-test/, the skill MUST
stop, explain the defect + evidence + root cause, propose the exact
change, explain why it's needed and what the risk is, and ASK.

Silence, a prior approval, "it looks safe", or general instructions
NEVER count as approval. Each change request is approved individually.
```

Everything below exists to enforce this invariant while still being useful. Read `references/rules.md` in full before the first run in any project — it is short and non-negotiable.

## What this skill does

Given a project, it:
1. **Discovers** the stack (frontend framework, backend framework, routes, endpoints, DB technology) via regex + file inspection — see `references/discovery.md` and `references/regex-patterns.md`.
2. **Builds/updates a persistent TODO** of smoke-test items (`.smoke-test/smoke-todo.json`) scoped to backend / frontend / integration — see `references/state-management.md`.
3. **Executes** read-only checks (HTTP calls, `curl`, running an existing test runner, loading pages) against each TODO item, following the question bank in `references/questioning-engine.md`.
4. **Records evidence** for every check and writes a Markdown + JSON report — see `references/reporting.md`.
5. **Classifies failures** and, if a fix requires touching source/config/DB, opens a change request and **stops to ask the user** — see `references/change-control.md`.
6. **Logs every action** to an append-only audit trail — see `references/audit.md`.
7. On the next run, **reloads state**, re-checks fingerprints, and continues from wherever the TODO left off instead of starting over.

## First run in a project

1. Check whether `.smoke-test/` exists at the project root.
2. If not, create it and copy the starter templates from this skill's `assets/` folder (see the mapping table in `references/state-management.md`) — `smoke-config.json`, `smoke-state.json`, `smoke-todo.json` (empty/seed), `audit.jsonl` (empty), `patterns/*.json`, `questions/*.md`, `reports/`, `evidence/`.
3. Ask the user (once, briefly) anything `smoke-config.json` needs that can't be discovered: base URLs if not obvious, whether writes/destructive ops are allowed in this environment, and whether a dedicated smoke-test account/tenant exists. Don't ask about things you can discover yourself (framework, routes, ports found in config files).
4. Proceed to discovery (`references/discovery.md`).

## Every subsequent run

1. Read `.smoke-test/smoke-state.json` and `.smoke-test/smoke-todo.json`.
2. Re-fingerprint the project (see `references/discovery.md` §Fingerprinting). Invalidate (mark stale, not delete) any TODO items whose watched files changed.
3. Re-run only what's `pending`, `stale`, or `awaiting_user` with a fresh answer from the user; skip items that are `passed` and unchanged, but say so in the report so the user knows they weren't re-verified.
4. Execute in dependency order (see `references/state-management.md` §Dependency-aware execution): a `FAIL`/`BLOCKED` upstream item blocks downstream items instead of silently re-testing them.
5. Update TODO statuses as you go — mark items complete the moment their check finishes, don't batch it to the end.
6. Write the report and audit log, then summarize for the user in chat (short — the file has the detail).

## Levels (run in this order, stop early on fundamental failure)

```
LEVEL 0  Discovery        — detect stack, routes, DB, build the/update TODO
LEVEL 1  Backend smoke     — health, readiness, DB connectivity, auth, core API, error handling
LEVEL 2  Frontend smoke    — app loads, routes render, critical UI elements exist, no console errors
LEVEL 3  Integration smoke — real frontend → real backend → real DB, one critical workflow
LEVEL 4  Critical E2E      — the 1-3 workflows the user says matter most (login→core action→logout)
```

If Level 1 backend health fails outright, don't burn time on Levels 3-4 (mark them `BLOCKED`, not `FAIL`) — but Level 2 frontend-only checks can still run against a mocked/static load if configured. See `references/discovery.md` for the full decision tree and `references/reporting.md` for how `FAIL` vs `BLOCKED` must be reported.

## Safety boundaries (summary — full detail in references/rules.md)

**Always allowed, no approval needed:** reading files, running `grep`/regex over the codebase, making HTTP requests to configured dev/test URLs, running the project's *existing* test commands, reading logs, read-only DB queries, writing/updating anything under `.smoke-test/`.

**Never do automatically, no exceptions:** edit or delete source files, change `package.json`/`requirements.txt`/dependency files, change env files, change Docker/CI/nginx config, run DB migrations, run destructive/write operations against data that isn't explicitly marked as a disposable smoke-test fixture in `smoke-config.json`.

**Gray area → always ask:** anything not clearly in the two lists above. When unsure, treat it as requiring approval.

## Nested-skill orchestrator compatibility

This skill ships `manifest.json` at `skills/smoke-testing/manifest.json` so a config-driven parent orchestrator (e.g. a `testing-audit-debugging-protocol` controller that only invokes nested skills after its own audit report is approved) can auto-discover it, see its levels, invariant, and hard constraints without parsing this whole file, and know what it will create in the project. When invoked that way, read the parent's approved audit report first, run only what it asked for, and still write to `.smoke-test/` and `audit.jsonl` in the standard shape — don't invent a bespoke output format just because you were called by another skill instead of the user directly.

## Reference files (load as needed — don't load all of them up front)

| File | Read when |
|---|---|
| `references/rules.md` | Start of every project's first run; whenever unsure if an action needs approval |
| `references/discovery.md` | Level 0, and at the start of every subsequent run (fingerprinting) |
| `references/regex-patterns.md` | During discovery, to detect stack/routes/DB technology/errors |
| `references/questioning-engine.md` | Building/updating the TODO, deciding what each check verifies |
| `references/state-management.md` | Reading/writing `.smoke-test/*.json`, TODO lifecycle, dependency handling, change-request storage |
| `references/reporting.md` | Writing `reports/latest.md` and `reports/latest.json` |
| `references/change-control.md` | Any time a fix would require touching code/config/DB |
| `references/audit.md` | Logging actions to `audit.jsonl` |

Executable helpers, used directly rather than read as prose: `assets/scripts/health_probe.sh` (Level 1 health/readiness gate) and `assets/scripts/compute_fingerprint.py` (staleness detection in `references/discovery.md`).

## Report + TODO location (always tell the user where to look)

```
PROJECT_ROOT/.smoke-test/reports/latest.md      ← human-readable, read this first
PROJECT_ROOT/.smoke-test/reports/latest.json    ← machine-readable
PROJECT_ROOT/.smoke-test/smoke-todo.json        ← persistent TODO, survives across runs
PROJECT_ROOT/.smoke-test/audit.jsonl            ← append-only action log
```
