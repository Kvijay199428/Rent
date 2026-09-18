# State management

## Directory layout created in the target project

```
PROJECT_ROOT/.smoke-test/
├── README.md                 (brief pointer, generated once)
├── smoke-config.json         (user/project settings)
├── smoke-state.json          (discovery + fingerprint cache + change_requests — see below)
├── smoke-todo.json           (persistent TODO — the heart of the skill)
├── audit.jsonl               (append-only action log, see references/audit.md)
├── reports/
│   ├── latest.md
│   ├── latest.json
│   └── history/YYYY-MM-DD_HHMMSS.{md,json}
├── evidence/
│   ├── backend/
│   ├── frontend/
│   └── e2e/
├── patterns/                 (copied from this skill's assets/patterns/, editable per-project)
│   ├── backend.json
│   ├── frontend.json
│   ├── database.json
│   ├── errors.json
│   └── configuration.json
└── questions/                (copied from this skill's assets/questions/, editable per-project)
    ├── backend.md
    ├── frontend.md
    └── integration.md
```

This skill's own folder (`skills/smoke-testing/`) additionally ships `manifest.json` (nested-skill orchestrator contract — see SKILL.md's "Nested-skill orchestrator compatibility") and `assets/scripts/` (`health_probe.sh`, `compute_fingerprint.py` — read-only helpers, not copied into the project; run them directly from the skill folder or the project can vendor them in if it wants them checked into its own repo).

On first run, copy the starter templates from this skill's own `assets/` folder into the above paths (don't hand-author them from scratch each time — reuse the templates, then let the project customize them).

## smoke-config.json

```json
{
  "version": 1,
  "project": { "name": "<discovered or asked>" },
  "mode": { "read_only": true, "require_change_approval": true },
  "components": { "backend": true, "frontend": true, "integration": true },
  "backend": { "base_url": "http://localhost:8000", "health_endpoints": ["/health", "/ready"] },
  "frontend": { "base_url": "http://localhost:5173" },
  "test_environment": {
    "allow_writes": false,
    "allow_destructive_operations": false,
    "smoke_test_account": null,
    "smoke_test_fixture_prefix": "SMOKE_TEST_"
  },
  "reporting": { "retain_history": true, "evidence": true }
}
```

`mode.read_only` and `mode.require_change_approval` must always be `true` unless the user explicitly says otherwise in writing in this project's config — never flip them yourself.

## smoke-state.json

Holds three things, all persistent across runs (never overwritten wholesale — merge into it):

- `discovery.*` — the stack/route/dependency-map cache from Level 0 (see `references/discovery.md`).
- `coarse_fingerprints.{dependencies,infra,database_schema}` — project-wide hashes (over `package.json`/lockfiles, `Dockerfile`/`docker-compose.yml`, and the migrations/schema directory respectively). If one of these changes since last run, invalidate every TODO item in the affected area back to `stale` rather than trying to pinpoint exactly which fine-grained items are impacted — over-invalidating a little is safer than trusting a stale pass.
- `change_requests` — the authoritative list of every change request ever opened for this project, per `references/change-control.md`. `smoke-todo.json` items only hold a `change_request_id` pointer into this array; don't duplicate the full record into the TODO file.

## smoke-todo.json — item schema

```json
{
  "id": "SMK-001",
  "category": "backend | frontend | integration | e2e",
  "title": "Verify authentication endpoint",
  "question": "Can the auth endpoint authenticate a valid test account?",
  "priority": "critical | high | medium | low",
  "status": "pending | in_progress | passed | failed | blocked | skipped | awaiting_user",
  "depends_on": ["SMK-000"],
  "fingerprint": { "files": ["path/a.py"], "hash": "sha256:..." },
  "created_at": "2026-09-17T08:00:00+05:30",
  "completed_at": null,
  "evidence": [".smoke-test/evidence/backend/SMK-001.txt"],
  "change_request_id": null
}
```

Use this controlled status vocabulary only — no "maybe"/"probably"/"looks fine".

## Lifecycle

```
pending → in_progress → passed
pending → in_progress → failed → awaiting_user (if a fix needs a change request)
pending → in_progress → blocked (upstream failure or missing config, no change needed to unblock testing itself)
stale (fingerprint changed) → in_progress → passed/failed/blocked   (re-entry point for previously-passed items)
```

Mark an item complete (`passed`/`failed`/`blocked`) the moment its check finishes — don't batch updates to the end of the run, so a partial/interrupted run still leaves accurate state behind.

## Dependency-aware execution

Give every item a `depends_on` list. Before running an item, check its dependencies:

```
all depends_on == passed  → run it
any depends_on == failed/blocked → mark this item BLOCKED too, don't run it, record why
any depends_on == awaiting_user → mark this item BLOCKED (pending that approval)
```

This is what prevents, e.g., a "create bill" E2E check from being falsely reported as FAILED when it never even ran because login was broken.

## Re-validating "passed" items (staleness)

A `passed` status from a previous run is not permanent. Before trusting it:
1. Recompute the fingerprint hash for its watched files.
2. If unchanged → may be carried forward; say so explicitly in the report ("carried forward, not re-verified this run").
3. If changed → set status to `stale`, then treat it as `pending` for this run.

Also treat backend/frontend framework config changes (`package.json`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, DB schema/migrations, `.env.example`) as global invalidators — this is what `smoke-state.json`'s `coarse_fingerprints` exists for. A change to any of these should mark all backend (or frontend, or all) items `stale`, since they can affect anything.

## Skill vs project separation

The skill definition (this folder, `skills/smoke-testing/`) stays generic and reusable across projects — never write project-specific results into it. All project-specific state lives under that project's `.smoke-test/`. If, while running, you discover a genuinely new capability worth adding to the skill itself (a new framework pattern, a new question type), propose it to the user as a skill enhancement rather than silently editing this skill's files mid-run.
