#!/usr/bin/env bash
# secret_scan.sh — scan staged changes for likely secrets before commit.
# Read-only: reports matches, never modifies or unstages anything.
# Exit code 0 = clean, 1 = possible secret(s) found, 2 = not a git repo.
set -uo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Not a git repository."
  exit 2
fi

FOUND=0

echo "=== Sensitive filenames staged ==="
PATTERNS_FILES='\.env($|\.[^/]*$)|\.pem$|\.key$|id_rsa|credentials\.json$|service-account.*\.json$|\.p12$|\.pfx$'
MATCHES_FILES=$(git diff --cached --name-only | grep -E -i "$PATTERNS_FILES" || true)
if [ -n "$MATCHES_FILES" ]; then
  echo "$MATCHES_FILES"
  FOUND=1
else
  echo "(none)"
fi

echo -e "\n=== Likely secret patterns in staged diff content ==="
# Broad, intentionally conservative pattern set — false positives are cheap,
# a leaked token is not. Report line context, never the full file.
PATTERNS_CONTENT='(AKIA[0-9A-Z]{16})|(ghp_[A-Za-z0-9]{36})|(github_pat_[A-Za-z0-9_]{20,})|(-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)|(xox[baprs]-[0-9A-Za-z-]{10,})|(AIza[0-9A-Za-z_-]{35})|((api|secret|access)[_-]?key\s*[:=]\s*["\x27][^"\x27]{16,}["\x27])|(password\s*[:=]\s*["\x27][^"\x27]{6,}["\x27])'
MATCHES_CONTENT=$(git diff --cached -U0 2>/dev/null | grep -E -i "$PATTERNS_CONTENT" || true)
if [ -n "$MATCHES_CONTENT" ]; then
  echo "$MATCHES_CONTENT"
  FOUND=1
else
  echo "(none)"
fi

echo -e "\n=== Result ==="
if [ "$FOUND" -eq 1 ]; then
  echo "POSSIBLE SECRET DETECTED — do not commit until the user has reviewed the matches above and confirmed how to proceed (remove, .gitignore, or explicitly override)."
  exit 1
else
  echo "Clean — no obvious secrets in staged changes."
  exit 0
fi
