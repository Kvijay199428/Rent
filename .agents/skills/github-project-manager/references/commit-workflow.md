# Commit workflow

Treat every commit as a small controlled transaction, not a fire-and-forget action.

```
inspect diff → secret scan → test gate (if applicable) → summarize → ask → commit → verify → record
```

## 1. Inspect

```bash
git status
git diff
git diff --cached
```
Understand what's actually changing before writing a message about it. If there are both staged and unstaged changes and it's unclear which the user wants committed, ask rather than guessing.

## 2. Secret scan (mandatory, every time)

Stage the intended changes, then run `scripts/secret_scan.sh`. If it reports a possible match, stop — do not commit. Show the user exactly what matched and where, and let them decide (remove it, add to `.gitignore`, or explicitly confirm it's a false positive). Never silently exclude the flagged file and commit the rest without saying so.

## 3. Test gate

If the project has a discoverable test command (see `references/test-gate.md`) and the target is anything other than a throwaway/WIP commit on a feature branch, run it and include the result in the summary. Tests are not required before every single commit on a feature branch (that would be too heavy for iterative work) — they *are* required before a production merge, per `references/merge-workflow.md`.

## 4. Summarize and ask

```
Commit summary
--------------
Branch: feature/tenant-payment-history
Files changed: 8   Insertions: 221   Deletions: 47
Secret scan: clean
Tests: passed (or: not run — feature branch WIP)

Proposed message:
feat: implement tenant billing history

Create this commit?
  1. Yes
  2. No
  3. Edit the message first
```

Generate the commit message from the actual diff content (conventional-commit style — `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:` — unless the repo's existing history shows a different convention, in which case match that instead). Keep it to a one-line summary plus, if the change is non-trivial, a short body explaining *why*, not just *what*.

## 5. Commit and verify

```bash
git commit -m "<message>"
git rev-parse HEAD   # confirm the resulting SHA
```

## 6. Record (optional, if `.github-manager/` is in use)

Append one line to `.github-manager/commits/index.jsonl`:

```json
{"sha":"abc1234","branch":"feature/tenant-payment-history","message":"feat: implement tenant billing history","files_changed":8,"insertions":221,"deletions":47,"tests":"passed","pushed":false,"timestamp":"2026-09-18T10:20:00+05:30"}
```

Treat this file as an audit log, not authoritative history — `git log` / `git rev-list --count <branch>` are always the source of truth for what actually happened; the JSONL is a convenience record for status reports and audits.

## After commit: push is a separate ask

Committing does not imply pushing. Once the commit is made, ask separately:

```
Commit abc1234 created on feature/tenant-payment-history.
Push to origin?
  1. Yes
  2. Not yet
```
