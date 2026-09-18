#!/usr/bin/env bash
# git_inspect.sh — read-only local Git state dump.
# Never modifies anything. Run from inside the target repo, or pass a path as $1.
set -uo pipefail

REPO_PATH="${1:-.}"
cd "$REPO_PATH" || { echo "Not a valid path: $REPO_PATH"; exit 1; }

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Not a git repository: $(pwd)"
  exit 1
fi

echo "=== Repository root ==="
git rev-parse --show-toplevel

echo -e "\n=== Status (short/branch) ==="
git status --short --branch

echo -e "\n=== Current HEAD ==="
git rev-parse HEAD 2>/dev/null || echo "(no commits yet)"

echo -e "\n=== Remotes ==="
git remote -v

echo -e "\n=== Local + remote branches ==="
git branch -a -vv

echo -e "\n=== Tags (newest first) ==="
git tag --sort=-creatordate | head -20

echo -e "\n=== Recent commit graph (last 20) ==="
git log --oneline --decorate --graph --all -20 2>/dev/null || echo "(no commits yet)"

echo -e "\n=== Ahead/behind vs upstream (current branch) ==="
git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null \
  | awk '{print "ahead: "$1", behind: "$2}' \
  || echo "(no upstream configured for current branch)"

echo -e "\n=== Project-type evidence (files present) ==="
for f in package.json pyproject.toml requirements.txt setup.py Pipfile \
         pom.xml build.gradle build.gradle.kts Dockerfile docker-compose.yml \
         docker-compose.yaml Cargo.toml go.mod Gemfile composer.json \
         .github/workflows README.md .github-manager; do
  [ -e "$f" ] && echo "found: $f"
done

echo -e "\n=== .gitignore present? ==="
[ -f .gitignore ] && echo "yes" || echo "no"
