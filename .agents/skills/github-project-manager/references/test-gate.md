# Test gate

## Discover, don't guess

Determine the test command from actual repo evidence rather than always running the same thing:

| Evidence in repo | Likely command |
|---|---|
| `pytest.ini`, `pyproject.toml` with `[tool.pytest]`, `tests/` + `*.py` | `pytest` |
| `package.json` with a `test` script | `npm test` (or `yarn test` / `pnpm test` — match the lockfile present) |
| `package.json` + a React/Vite/Next build script | also consider `npm run build` as part of the gate |
| `pom.xml` | `mvn test` |
| `build.gradle` / `build.gradle.kts` | `gradle test` (or `./gradlew test` if the wrapper is present) |
| `Cargo.toml` | `cargo test` |
| `go.mod` | `go test ./...` |
| `Gemfile` | `bundle exec rspec` or `rake test`, whichever the repo already uses |
| `Dockerfile` / `docker-compose.yml` present alongside the above | `docker compose config` / `docker compose build` as an additional sanity check before merge, not a replacement for the unit tests |

If none of these match, ask the user what the test command is rather than skipping the gate silently or inventing one.

## Result states

```
NOT_RUN | RUNNING | PASSED | FAILED | PARTIAL | BLOCKED | SKIPPED_WITH_APPROVAL
```

## Rules

- A production merge (see `references/merge-workflow.md`) normally requires `PASSED`. Anything else requires an **explicit override**, asked for on its own — never bundle "tests failed, should I merge anyway and commit?" into one yes/no.
- On `FAILED`, report what failed (test names, expected vs actual where available) and stop. Offer options, but do not act on any of them without the user picking:
  ```
  1. I'll look at fixing it
  2. Hand off to a debugging session
  3. Record the failure and stop here
  4. Merge anyway (requires separate confirmation)
  ```
- **Never edit code to make a failing test pass without being asked to fix it.** Reporting the failure is this skill's job; fixing it is a separate, explicit request.
- Don't run an unrelated stack's tests "just in case" — if a repo has both a Python backend and a JS frontend, scope the test run to what actually changed unless the user wants a full suite run.
