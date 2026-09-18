# Merge / pull request workflow

## Default route: pull request, not direct merge

Prefer `gh pr create` over a local `git merge` + push, even for solo projects, so GitHub's own required-checks/review/status protections apply consistently. Reserve direct merge for genuinely trivial, unprotected-branch, solo-project cases the user explicitly prefers.

## Precheck (always run and show before asking to merge)

```
Merge precheck
--------------
Source: developer            Target: production
Working tree:        clean
Source pushed:        yes
Target in sync:        yes
Tests:              passed
CI:                 passed
Conflicts:           none
Target protected:      yes (PR + 1 review required)
Open PR:             none yet
```

Gather this with:
```bash
git status --short
git log origin/<source>..<source>       # unpushed local commits, should be empty
git log <target>..<source> --oneline     # what would merge
git merge-tree $(git merge-base <target> <source>) <target> <source>   # conflict check (or `git merge --no-commit --no-ff` on a scratch check, aborted after)
gh pr checks <number>                    # once a PR exists
gh api repos/{owner}/{repo}/branches/<target>/protection
```

If anything above is red (dirty tree, unpushed commits, failing tests, conflicts), report it and stop — don't ask "merge anyway?" until the blocking issue is resolved or the user explicitly wants to override it (and an override of a failed-test or conflict state should be its own explicit confirmation, not folded into the merge yes/no).

## Ask

```
Merge developer → production?
  1. Create pull request (recommended)
  2. Direct merge
  3. Squash merge
  4. Rebase merge
  5. Don't merge yet
```

## After approval

- **PR route:** `gh pr create --base <target> --head <source> --title "..." --body "..."`. Generate title/body from the commit log since the merge-base, not a generic placeholder. Then stop — actually merging the PR (once checks/reviews pass) is a *separate* ask, especially if required reviews are pending:
  ```
  PR #142 opened: developer → production.
  Status checks: pending. Reviews required: 1, received: 0.
  I'll wait — let me know when you want me to check status or merge it.
  ```
- **Direct merge route:** confirm strategy (merge/squash/rebase) if not already specified, then perform it and verify the target's new HEAD afterward.

## Record

Append to `.github-manager/merges/index.jsonl`:
```json
{"merge_id":"merge-2026-09-18-001","source_branch":"developer","target_branch":"production","pull_request":142,"strategy":"squash","tests":"passed","status":"merged","merged_at":"2026-09-18T12:30:00+05:30"}
```

## State reconciliation (local vs remote)

Before pushing or merging, if local and remote have diverged on the same branch name, report the mismatch explicitly and don't push:
```
STATE MISMATCH
Local developer:  abc123
Remote developer: def456  (local is behind)
No push performed. Pull/reconcile first, or tell me how to proceed.
```
