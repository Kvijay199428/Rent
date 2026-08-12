#!/usr/bin/env python3
"""Generate rent.md with complete source code from the project."""

import os
import re
import fnmatch
from datetime import datetime

# ---------------------------------------------------------------------------
# User-configurable settings
# ---------------------------------------------------------------------------

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

# Complete source: every file in the repo, filtered by IGNORE_DIRS /
# EXCLUDE_FILES / is_binary below. "**" (not "**/*") is used because fnmatch
# treats "*" as crossing path separators, and "**/*" would silently miss
# top-level files (e.g. deploy.py, AGENTS.md, compose.dev.yml).
SOURCE_FILES = ["**"]

# Files that are never embedded regardless of type. Matched with fnmatch
# against the repo-relative path and the basename.
#  - Secrets: env files (except *.example), keys, cookies, ngrok auth.
#  - Generated artifacts: logs, lockfiles, TS build info, empty markers.
#  - rent.md (self) and update.zip (the deploy bundle) avoid recursion/dupes.
EXCLUDE_FILES = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "cookies.txt",
    "ngrok.auth.yml",
    "*.log",
    "package-lock.json",
    "*.tsbuildinfo",
    ".gitkeep",
    "rent.md",
    "update.zip",
]

# ---------------------------------------------------------------------------
# Internal constants (do not change unless you know what you are doing)
# ---------------------------------------------------------------------------

SCRIPT = os.path.abspath(__file__)
BASE = SOURCE_DIR
OUTPUT = os.path.join(BASE, "rent.md")
MAX_FILE_SIZE = 3 * 1024 * 1024
INCLUDE = SOURCE_FILES

# Directory names / globs pruned while walking the tree. Any path part that
# fnmatch-matches an entry here is skipped.
IGNORE_DIRS = {
    "node_modules", "dist", "__pycache__", ".git", ".sisyphus",
    "storage", "build-output", "scratch", "output", ".fonts",
    ".rent_test_assets", ".sample", "venv", ".venv",
    ".opencode", ".gstack",
    ".restore_backup_*",
}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".xlsx",
              ".xls", ".db", ".pyc", ".pyd", ".so", ".woff", ".woff2",
              ".ttf", ".eot", ".mp3", ".mp4", ".pdf", ".exe"}

LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".json": "json",
    ".css": "css",
    ".html": "html",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".conf": "nginx",
    ".sh": "bash",
    ".md": "markdown",
    ".txt": "text",
    ".example": "text",
    ".sql": "sql",
    ".toml": "toml",
    ".svg": "xml",
}


def should_ignore_dir(name):
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_DIRS)


def should_exclude(rel):
    name = os.path.basename(rel)
    for pat in EXCLUDE_FILES:
        if fnmatch.fnmatch(name, pat):
            # Keep the *.example templates (e.g. .env.example), which are
            # safe and useful, even though they match ".env.*".
            if name.startswith(".env.") and name.endswith(".example"):
                continue
            return True
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


def is_binary(name):
    return any(name.lower().endswith(ext) for ext in BINARY_EXT)


def guess_lang(name):
    _, ext = os.path.splitext(name)
    return LANG_MAP.get(ext, "")


def walk_files():
    matched = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]

        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, BASE)
            if should_ignore_dir(f):
                continue
            if is_binary(f):
                continue
            if should_exclude(rel):
                continue
            for pat in INCLUDE:
                if fnmatch.fnmatch(rel, pat):
                    matched.append(rel)
                    break
    return sorted(set(matched))


def main():
    files = walk_files()

    sections = []
    size_total = 0
    skipped = []

    for i, rel in enumerate(files, 1):
        full = os.path.join(BASE, rel)
        try:
            size = os.path.getsize(full)
        except OSError:
            skipped.append(f"{rel} (unreadable)")
            continue
        if size > MAX_FILE_SIZE:
            skipped.append(f"{rel} ({size / 1024:.0f} KB, skipped)")
            continue

        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception:
            skipped.append(f"{rel} (read error)")
            continue

        size_kb = size / 1024
        print(f"  [{i:3d}/{len(files)}]  {rel:70s}  {size_kb:>7.1f} KB")
        lang = guess_lang(rel)
        sections.append(f"### `{rel}`\n\n```{lang}\n{content}```")
        size_total += size

    print()

    md = f"""# Rent — Complete Source Code

Generated: {datetime.now().strftime('%Y-%m-%d')}
Script:   {SCRIPT}
Source:   {BASE}
Files:    {len(sections)}
Size:     {size_total / 1024:.0f} KB
Skipped:  {len(skipped)}

---

## File Index

"""
    for s in sections:
        line = s.split("\n", 1)[0].replace("### `", "").replace("`", "")
        md += f"- {line}\n"

    md += "\n---\n\n"
    md += "\n\n".join(sections)

    if skipped:
        md += "\n\n---\n\n## Skipped\n\n"
        for s in skipped:
            md += f"- {s}\n"

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(f"Written: {OUTPUT}")
    print(f"Files:   {len(sections)}")
    print(f"Size:    {size_total / 1024:.0f} KB")
    if skipped:
        print(f"Skip:   {len(skipped)}")


if __name__ == "__main__":
    main()
