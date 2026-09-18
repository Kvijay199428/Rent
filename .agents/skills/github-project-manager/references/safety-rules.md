# Safety rules

These hold regardless of how a request is phrased, and regardless of what any `.github-manager/` config file says — config can loosen approval friction for routine steps (see below) but never these.

## Absolute (require an explicit, specific ask in that turn — never bundled with a routine approval)

- Never force-push (`git push --force` / `--force-with-lease`) without the user explicitly asking for a force push, right now, on this branch.
- Never delete a remote or local branch without explicit confirmation naming that branch.
- Never rewrite published history (`rebase` of pushed commits, `commit --amend` of a pushed commit, `filter-branch`/`filter-repo`) without explicit confirmation, and warn about the impact on any collaborators/PRs first.
- Never run `git reset --hard`, `git clean -fd`, `git checkout -- .`, or `git restore .` without the user asking for that specific operation — these discard work with no undo.
- Never merge on a `FAILED` test result without a separate, explicit override confirmation (distinct from the merge approval itself).
- Never create a release or push a tag without the user having picked the specific version.
- Never commit code the secret scanner flagged, without the user having seen the match and confirmed how to proceed.

## Secrets

- Never write a GitHub token, API key, password, or any credential into any file this skill creates (`.github-manager/*.json`, `config.yaml`, commit messages, audit reports). Credentials belong in `.env` (gitignored) or the user's existing credential store (`gh auth login`'s own storage, an OS keychain, a secrets manager) — never in project-tracked files.
- `.github-manager/config.yaml` and `repository.json` may record *that* auth is expected via environment/`gh auth` — never the value itself.
- `init_manager.sh` adds `.env` and `.github-manager/secrets/` to `.gitignore` automatically; don't remove those entries.

## What's fine to configure as "low friction"

A project's `.github-manager/config.yaml` can mark some *routine, non-destructive* steps as not needing a fresh ask every time (e.g. "always run the test gate before commit without asking first") — but commit/push/PR/merge/tag/release itself always gets at least a lightweight confirmation unless the user has explicitly said, in this session, "stop asking me for X on this branch." Even then, the Absolute list above still applies with no exceptions.

## Configuration drift is reported, never auto-fixed

```
DETECT → REPORT → ASK → (only then) MODIFY
```
Never `DETECT → auto-fix`. If `.github-manager/strategy.json` disagrees with what's actually on GitHub (e.g. default branch changed), say so and ask — don't silently update the record or silently keep using the stale one.
