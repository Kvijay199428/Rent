# `.github-manager/` state directory

Created by `scripts/init_manager.sh` once the user has confirmed a branch strategy. This is the skill's memory for a given repo — read it at the start of every session against that repo instead of re-deriving decisions.

## Layout

```
.github-manager/
├── config.yaml           # human-editable settings (approval friction, patterns, testing requirements)
├── repository.json        # owner/name/remote/default branch, recorded once
├── strategy.json          # the confirmed branch strategy + reasoning
├── state.json            # current snapshot — branch, HEAD, ahead/behind, last test result
├── branches/              # optional per-branch lifecycle tracking (see branch-strategy.md)
├── commits/index.jsonl     # append-only commit record
├── merges/index.jsonl      # append-only merge record
├── tags/index.jsonl       # append-only tag record
├── releases/index.jsonl    # append-only release record
├── audits/
│   ├── latest.md          # most recent full audit report
│   └── history/           # dated prior audits
├── logs/operations.jsonl   # append-only operation log (every mutating action, with timestamp)
└── secrets/               # gitignored; never populated by this skill, present only so a .gitignore entry has somewhere to point
```

`commits/`, `merges/`, `tags/`, `releases/`, and `logs/` are JSONL (one JSON object per line) — append, don't rewrite, so a long history doesn't require reading and rewriting a huge array each time.

## What's committed vs not

**Commit to the repo:** `config.yaml`, `repository.json`, `strategy.json`, and generally `audits/` if the user wants the governance history versioned too.
**Usually fine either way:** `logs/operations.jsonl` (can get noisy — ask if the user wants it committed or just local).
**Never commit:** anything under `secrets/`, and obviously nothing that duplicates `.env`.

## `repository.json`

```json
{
  "repository": {
    "owner": "example",
    "name": "my-project",
    "remote": "origin",
    "url": "https://github.com/example/my-project.git",
    "default_branch": "production"
  },
  "management": {
    "managed_by": "github-project-manager",
    "initialized_at": "2026-09-18T00:00:00Z"
  }
}
```

## `strategy.json`

```json
{
  "strategy": "feature-developer-production",
  "reason": ["Active development", "Needs a staging point before production"],
  "branches": { "development": "developer", "production": "production" },
  "feature_branches": { "enabled": true, "pattern": "feature/*" },
  "hotfix_branches": { "enabled": true, "pattern": "hotfix/*" },
  "release_branches": { "enabled": false }
}
```

## `state.json` (refresh this each session, don't treat as static)

```json
{
  "current_branch": "developer",
  "working_tree": "clean",
  "head": "abc123",
  "ahead": 2,
  "behind": 0,
  "testing": { "status": "passed", "last_run": "2026-09-18T12:20:00+05:30" }
}
```

## `config.yaml`

```yaml
version: 1
branches:
  development: developer
  production: production
features: { enabled: true, pattern: "feature/*" }
testing:
  required_before_commit: false
  required_before_production_merge: true
commit:  { require_confirmation: true }
push:    { require_confirmation: true }
merge:   { require_confirmation: true, preferred_method: pull_request }
release: { tag_pattern: "vMAJOR.MINOR.PATCH", require_confirmation: true }
safety:
  allow_force_push: false
  allow_history_rewrite: false
  allow_branch_delete: false
```

Templates for all of the above (with placeholder values to fill in after strategy confirmation) live in the skill's `assets/` directory.

## `commits/index.jsonl` entry shape

```json
{"sha":"abc123","branch":"developer","message":"feat: x","files_changed":8,"insertions":221,"deletions":47,"tests":"passed","pushed":true,"timestamp":"2026-09-18T10:20:00+05:30"}
```

## `merges/index.jsonl` entry shape

```json
{"merge_id":"merge-2026-09-18-001","source_branch":"developer","target_branch":"production","pull_request":142,"strategy":"squash","tests":"passed","status":"merged","merged_at":"2026-09-18T12:30:00+05:30"}
```

## `tags/index.jsonl` entry shape

```json
{"tag":"v2.4.0","commit":"abc1234","branch":"production","type":"release","pushed":true,"release_created":true,"created_at":"2026-09-18T12:40:00+05:30"}
```

## Rule: JSON records are a cache, not the source of truth

Always reconcile against real `git`/`gh` state before trusting a number here (e.g. don't report "37 commits on developer" from a stale count — run `git rev-list --count developer`). See SKILL.md "Configuration drift".
