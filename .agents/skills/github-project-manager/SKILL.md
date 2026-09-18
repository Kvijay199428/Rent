---
name: github-project-manager
description: >
  Repository-governance and Git/GitHub workflow skill for managing any
  project's version control lifecycle — branch strategy, commits, pull
  requests, merges, tags, and releases. Use this whenever the user wants
  help with git or GitHub operations on a real repository — committing
  changes, deciding what to branch, opening a PR, merging to
  production/main, tagging a release, setting up branch protection,
  auditing repository state, or asking things like "what's the status of
  this repo", "should I merge this", or "help me ship this". Also trigger
  when a project has no clear branching workflow yet and the user is about
  to commit or push, when the user asks to set up a git workflow or manage
  a repo, or when destructive-sounding git operations (force push, history
  rewrite, branch delete, hard reset) come up — this skill enforces an
  approval gate before those. Do NOT use for pure code-writing/debugging
  with no git operations involved, and do not use to replace the
  docx/pptx/xlsx/pdf skills for document creation.
---

# GitHub Project Manager

A repository-governance skill. It inspects a repo, proposes a branch strategy, and carries changes through a **developer → test → production** lifecycle — but it never performs a history-changing or publishing operation without explicit user approval. Read-only inspection is automatic; everything that mutates git/GitHub history is a stop-and-ask.

This is not a replacement for GitHub's own protections (branch protection, rulesets, required reviews). Use those as the enforcement layer; this skill is the workflow layer that talks to them via `git` and `gh`.

## The one rule that governs everything else

```
READ / INSPECT / TEST / ANALYZE / RECOMMEND   → automatic, no approval needed
COMMIT / PUSH / PR / MERGE / TAG / RELEASE     → describe the operation, then ask
FORCE PUSH / HISTORY REWRITE / BRANCH DELETE   → explicit high-risk approval,
  / HARD RESET / CLEAN                           never bundled with a routine step
```

Never chain a mutating operation onto an approval for a *different* operation — approving a commit is not approval to also push; approving a push is not approval to also open a PR. Ask at each boundary. When in doubt, ask.

## Lifecycle overview

```
inspect repo → determine/confirm branch strategy → work happens on a branch
   → test gate → commit (ask) → push (ask) → PR (ask) → merge (ask)
   → tag/release (ask) → update .github-manager/ records → audit
```

Full state-transition detail: `references/branch-strategy.md`.

## Step 1 — Discover before doing anything else

Every session against a repo starts with inspection, never assumption. Run:

```bash
bash scripts/git_inspect.sh          # local: branch, status, log, tags, remotes
bash scripts/github_inspect.sh       # remote: gh repo/pr/run/release/ruleset state (needs gh auth)
```

If `.github-manager/` already exists in the repo, read `.github-manager/state.json`, `repository.json`, and `strategy.json` first — that's this skill's own memory of prior decisions for this repo. Don't re-derive a strategy that's already recorded; just reconcile it against current reality (see "Configuration drift" below).

If `.github-manager/` does not exist, this is first contact with the repo. Summarize what was discovered (default branch, existing branches, whether it looks like a solo/personal project or has CI/PRs/protection already) and propose initializing — see `references/branch-strategy.md` for the strategy decision engine and the `.github-manager/` file layout it creates. Always let the user confirm or override the proposed strategy before creating anything.

## Step 2 — Working-tree and branch safety

Before switching branches, check `git status`. If the tree is dirty, do not stash, discard, or switch silently — present the modified files and ask what to do (stay, stash, commit, branch off, abort). Never run `git reset --hard`, `git clean -fd`, `git checkout -- .`, or `git restore .` without the user explicitly asking for that specific operation in that message.

If the repo already has commits/branches in a state that doesn't match what the user's request implies (e.g. they say "commit this" while sitting on `production` directly), stop and ask which branch this should actually land on before doing anything.

## Step 3 — Commit workflow

Full detail: `references/commit-workflow.md`. Summary: inspect diff → scan for secrets (`scripts/secret_scan.sh`) → run the test gate if one exists for this project → show a commit summary (files/insertions/deletions, test result, proposed message) → ask for approval → commit → record it.

**Secret scan is mandatory before every commit**, not optional. If it flags a hit, block the commit and report it — never commit anyway "just this once" without the user seeing and confirming exactly what matched.

## Step 4 — Test gate

Full detail: `references/test-gate.md`. The skill discovers the right test command from repo evidence (don't guess or run a wrong stack's tests) rather than always running the same command. A production merge normally requires a PASSED test result; anything else requires an explicit override, asked for separately from the merge approval itself. This skill never edits code to make a failing test pass on its own — that's the user's call, or handed to a debugging skill/session if one exists.

## Step 5 — Merge / PR workflow

Full detail: `references/merge-workflow.md`. Prefer pull requests over direct merges as the default route so GitHub's own required-checks/review protections apply. Before proposing a merge, check: working tree clean, source pushed, target in sync, tests passed, no conflicts, and whether the target branch is protected. Present that precheck, then ask. `gh pr create` / `gh pr merge` do the actual operation once approved.

## Step 6 — Tag / release workflow

Full detail: `references/release-workflow.md`. Never create a tag automatically just because a merge happened — propose a version (with reasoning: patch/minor/major) and ask.

## Safety rules (absolute, not situational)

See `references/safety-rules.md` for the full list and rationale. The short version: never force-push, delete a branch, rewrite published history, discard uncommitted work, or merge on a failed test, without an explicit, specific ask from the user in that turn. Never store a GitHub token or other secret in any file this skill writes — see `references/safety-rules.md` §Secrets for where credentials belong instead.

## `.github-manager/` — this skill's memory for a repo

This skill keeps a small state directory in the repo so it doesn't re-ask settled questions every session and so there's an audit trail. Schema and file layout: `references/state-schema.md`. Templates to copy when initializing a new repo are in `assets/`. Treat `.github-manager/*.json` as a cache/audit record, never as the source of truth over actual `git`/`gh` state — always reconcile against real state, and if they disagree, report the mismatch and ask rather than silently trusting either one.

## Configuration drift

If `.github-manager/` records something (e.g. "production branch is `production`") that no longer matches reality (e.g. GitHub's default branch is now `main`), report the mismatch plainly and ask what to do. Never auto-correct drift.

## Interaction style

Ask when: branch choice is ambiguous, a switch could affect uncommitted work, or before commit/push/PR/merge/tag/release/anything destructive. Don't ask about things `git`/`gh` can already tell you (current branch, current repo, whether the tree is dirty) — just look. Keep status reports compact and scannable (short labeled blocks), not prose paragraphs, since these are read quickly and often mid-task.

## Reference index

- `references/branch-strategy.md` — discovery inputs, the five branch-strategy patterns (simple / dev-prod / feature-dev-prod / +release / hotfix), and the `.github-manager/` init flow
- `references/commit-workflow.md` — diff inspection, commit message generation, commit records
- `references/test-gate.md` — test-command discovery per stack, result states
- `references/merge-workflow.md` — PR-first merge flow, precheck, protection inspection
- `references/release-workflow.md` — semantic version decision engine, tag/release records
- `references/safety-rules.md` — the full absolute-rules list and secret handling
- `references/state-schema.md` — `.github-manager/` file layout and JSON shapes
- `scripts/git_inspect.sh`, `scripts/github_inspect.sh`, `scripts/secret_scan.sh`, `scripts/init_manager.sh` — deterministic inspection/setup, run rather than reimplemented inline
