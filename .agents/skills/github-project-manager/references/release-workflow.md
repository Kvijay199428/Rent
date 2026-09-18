# Tag / release workflow

## Never automatic

A production merge does not by itself trigger a tag or release — always ask afterward, separately from the merge approval:

```
Production updated (now at abc1234).
Create a release tag?
  1. v2.4.0
  2. v2.4.1
  3. Custom
  4. No tag
```

## Version suggestion (semantic versioning default)

Look at the commit messages merged since the last tag (conventional-commit prefixes if the repo uses them) to suggest a bump, and say *why*:

- **PATCH** (`v2.4.0 → v2.4.1`): only `fix:`/bugfix-type changes since last tag
- **MINOR** (`v2.4.0 → v2.5.0`): any `feat:`/backward-compatible additions
- **MAJOR** (`v2.4.0 → v3.0.0`): anything indicating a breaking change (explicit `BREAKING CHANGE` note, or the user says so)

If the repo has no prior tags, ask whether to start at `v0.1.0` or `v1.0.0` rather than assuming.

## Creating the tag and release

```bash
git tag -a v2.4.0 -m "v2.4.0"
git push origin v2.4.0
gh release create v2.4.0 --generate-notes     # or with a hand-written body if the user wants one
```

Only run these after the user has picked a specific version — don't tag first and ask "is this version okay?" after the fact.

## Record

Append to `.github-manager/tags/index.jsonl`:
```json
{"tag":"v2.4.0","commit":"abc1234","branch":"production","type":"release","pushed":true,"release_created":true,"created_at":"2026-09-18T12:40:00+05:30"}
```
