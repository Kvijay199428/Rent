#!/usr/bin/env python3
"""Generate rent.md with complete source code from the project."""

import os
import re
import fnmatch

# ---------------------------------------------------------------------------
# User-configurable settings
# ---------------------------------------------------------------------------

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCE_FILES = [
    "backend/app/**/*.py",
    "backend/app/**/*.json",
    "backend/app/config/**",
    "backend/Dockerfile",
    "backend/compose.yml",
    "backend/compose.test.yml",
    "backend/.env.example",
    "backend/requirements.txt",
    "backend/shared/routes.json",
    "backend/deploy/**/*.py",
    "backend/scripts/**/*.py",
    "frontend/shared/**/*",
    "frontend/*/src/**/*.ts",
    "frontend/*/src/**/*.tsx",
    "frontend/*.ts",
    "frontend/*/package.json",
    "frontend/*/tsconfig*.json",
    "frontend/*/vite.config.ts",
    "frontend/package.json",
    "frontend/build.sh",
    "frontend-test/nginx.conf",
    "frontend-test/compose.yml",
    "gateway/nginx/nginx.conf",
    "gateway/nginx/routes/rent.conf",
    "gateway/compose.yml",
    "copy.py",
    ".env.example",
    ".gitignore",
    "README.md",
]

# ---------------------------------------------------------------------------
# Internal constants (do not change unless you know what you are doing)
# ---------------------------------------------------------------------------

SCRIPT = os.path.abspath(__file__)
BASE = SOURCE_DIR
OUTPUT = os.path.join(BASE, "rent.md")
MAX_FILE_SIZE = 500 * 1024
INCLUDE = SOURCE_FILES

IGNORE_DIRS = {
    "node_modules", "dist", "__pycache__", ".git", ".sisyphus",
    "storage", "build-output", "scratch", "output", ".fonts",
    ".rent_test_assets", ".sample", "venv", ".venv",
}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".xlsx",
              ".xls", ".db", ".pyc", ".pyd", ".so", ".woff", ".woff2",
              ".ttf", ".eot", ".mp3", ".mp4", ".pdf"}

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
}


def should_ignore(path):
    parts = path.split(os.sep)
    return any(d in IGNORE_DIRS for d in parts)


def is_binary(name):
    return any(name.lower().endswith(ext) for ext in BINARY_EXT)


def guess_lang(name):
    _, ext = os.path.splitext(name)
    return LANG_MAP.get(ext, "")


def walk_files():
    matched = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, BASE)
            if should_ignore(rel):
                continue
            if is_binary(f):
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

Generated: 2025-07-29
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
