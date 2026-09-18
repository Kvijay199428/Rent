#!/usr/bin/env bash
# github_inspect.sh — read-only remote GitHub state dump via `gh`.
# Never modifies anything. Requires `gh auth login` to already be done;
# this script does not attempt to authenticate.
set -uo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is not installed. Install it (https://cli.github.com) or ask the user how they'd like to inspect the GitHub-side state instead."
  exit 1
fi

echo "=== gh auth status ==="
gh auth status 2>&1

echo -e "\n=== Repo view ==="
gh repo view --json owner,name,url,visibility,defaultBranchRef,isFork,isArchived 2>&1

echo -e "\n=== Open pull requests ==="
gh pr list --state open --json number,title,headRefName,baseRefName,isDraft,mergeable,reviewDecision 2>&1

echo -e "\n=== Recent workflow runs ==="
gh run list --limit 10 2>&1

echo -e "\n=== Releases ==="
gh release list --limit 10 2>&1

echo -e "\n=== Branch protection (default branch) ==="
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null)
if [ -n "${DEFAULT_BRANCH:-}" ]; then
  gh api "repos/{owner}/{repo}/branches/${DEFAULT_BRANCH}/protection" 2>&1 \
    || echo "(no protection configured on '${DEFAULT_BRANCH}', or insufficient permissions to view it)"
else
  echo "(could not determine default branch)"
fi

echo -e "\n=== Rulesets ==="
gh api repos/{owner}/{repo}/rulesets 2>&1 || echo "(none, or insufficient permissions)"
