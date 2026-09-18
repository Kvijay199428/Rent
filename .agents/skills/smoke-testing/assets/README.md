# .smoke-test/

This directory is the working state for the `smoke-testing` skill. It is
owned by the skill: files here are created and updated automatically.

- `smoke-config.json` — project settings (base URLs, what's allowed)
- `smoke-state.json`  — discovery + fingerprint cache + the authoritative change-request log
- `smoke-todo.json`   — persistent TODO, survives across runs
- `audit.jsonl`        — append-only action log
- `reports/`           — latest.md / latest.json + dated history
- `evidence/`          — raw evidence backing every PASS/FAIL
- `patterns/`          — regex patterns: backend, frontend, database, configuration, errors (editable per project)
- `questions/`         — question bank: backend, frontend, integration (covers both Level 3 integration and Level 4 critical E2E — see SKILL.md)

The skill never modifies application code, config, dependencies, or the
database from here without asking first. See the skill's
`references/rules.md` for the full ground rules.
