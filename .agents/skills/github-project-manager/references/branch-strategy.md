# Branch strategy

## Decision inputs

Gather these from `git_inspect.sh` / `github_inspect.sh` output before proposing anything:

- number of existing branches, their names and ages
- commit frequency / number of contributors (from `git log --format='%an'`)
- whether CI (`.github/workflows/`) exists
- whether releases/tags already exist
- whether a deployment setup exists (Dockerfile, docker-compose, hosting config)
- whether branch protection/rulesets already exist on the remote
- existing default branch name

## The five patterns

**A — Simple (single branch)**
```
main
```
Fits: small utility, script, docs, single-developer prototype with no need to stage changes before they're "live". Don't propose more structure than the project needs.

**B — Developer / Production**
```
developer → production
```
Fits: a typical solo or small-team application project where changes need a staging/testing point before being considered final, but feature isolation isn't needed.

**C — Feature / Developer / Production** *(default recommendation for most application repos)*
```
feature/* → developer → production
```
Fits: active development with more than one thing in flight at once.

**D — Feature / Developer / Release / Production**
```
feature/* → developer → release/* → production
```
Fits: projects that need a stabilization window before shipping (e.g. release candidates, QA sign-off). Don't propose this unless the project shows evidence of actually needing it (e.g. existing release branches, a QA process) — it's overhead most personal/small projects don't need.

**E — Hotfix overlay** (applies on top of B, C, or D)
```
production → hotfix/* → production, then back-merged into developer
```
Propose this as an available branch type, not a separate top-level strategy — it's for urgent production fixes that can't wait for the normal flow.

## Proposing a strategy

Never silently create or rename branches. Present findings, then the recommendation with reasoning, then ask:

```
Current branch: main
Existing branches: main, feature/login, feature/payment
No dedicated development branch exists.

Recommended: feature/* → developer → production

Would you like to initialize this structure?
  1. Yes
  2. Keep existing structure as-is
  3. Let me specify branches myself
```

If the repo already has `.github-manager/strategy.json` recorded, don't re-ask this — just reconcile it against current reality (see SKILL.md "Configuration drift") and proceed.

## Initializing `.github-manager/`

Once the user has confirmed a strategy, run `scripts/init_manager.sh <repo_path> <assets_path>` to scaffold the directory (see `references/state-schema.md` for what it creates), then fill in `strategy.json` and `repository.json` with the confirmed details — the copied templates are placeholders, not the recorded decision.

## Branch naming

```
feature/<description>
bugfix/<description>
hotfix/<description>
refactor/<description>
docs/<description>
test/<description>
chore/<description>
release/<version>
```
Short, kebab-case descriptions (`feature/tenant-payment-history`, not `feature/TenantPaymentHistory` or a vague `feature/fixes`).

## Feature-branch lifecycle states

`PROPOSED → CREATED → ACTIVE → TESTING → READY_FOR_MERGE → MERGED → ARCHIVED`

Track this in `.github-manager/branches/<name>.json` per `references/state-schema.md` if the project wants persistent tracking; for lightweight projects it's fine to derive status from `git`/`gh` on demand instead of maintaining per-branch files.
