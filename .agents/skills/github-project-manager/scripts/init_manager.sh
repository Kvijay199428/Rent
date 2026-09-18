#!/usr/bin/env bash
# init_manager.sh — scaffold .github-manager/ in the target repo.
# Only run this AFTER the user has confirmed the branch strategy (see
# references/branch-strategy.md). This script creates files but does not
# commit, push, create branches, or touch GitHub in any way.
#
# Usage: bash init_manager.sh /path/to/repo /path/to/this/skill/assets
set -euo pipefail

REPO_PATH="${1:?Usage: init_manager.sh <repo_path> <assets_path>}"
ASSETS_PATH="${2:?Usage: init_manager.sh <repo_path> <assets_path>}"

cd "$REPO_PATH"
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Not a git repository: $REPO_PATH"
  exit 1
fi

if [ -d .github-manager ]; then
  echo ".github-manager/ already exists — not overwriting. Read its existing files instead and reconcile any drift with the user rather than re-initializing."
  exit 1
fi

mkdir -p .github-manager/{branches,commits,merges,tags,releases,audits/history,logs}

cp "$ASSETS_PATH/config.yaml.template"      .github-manager/config.yaml
cp "$ASSETS_PATH/repository.json.template"  .github-manager/repository.json
cp "$ASSETS_PATH/strategy.json.template"    .github-manager/strategy.json
cp "$ASSETS_PATH/state.json.template"       .github-manager/state.json

touch .github-manager/commits/index.jsonl
touch .github-manager/merges/index.jsonl
touch .github-manager/tags/index.jsonl
touch .github-manager/releases/index.jsonl
touch .github-manager/logs/operations.jsonl

# Ensure secrets never land in .github-manager itself and .env stays ignored.
if [ -f .gitignore ]; then
  grep -qxF '.github-manager/secrets/' .gitignore || echo '.github-manager/secrets/' >> .gitignore
  grep -qxF '.env' .gitignore || echo '.env' >> .gitignore
else
  printf '.github-manager/secrets/\n.env\n.env.*\n!.env.example\n' > .gitignore
fi

echo "Scaffolded .github-manager/ in $REPO_PATH."
echo "IMPORTANT: the templates just copied in (config.yaml, repository.json, strategy.json) contain placeholder values — fill them in from the confirmed branch strategy and repo details before treating this as settled state. Nothing has been committed."
