#!/usr/bin/env python3
"""
Fixes route constant names across the project.
1. Removes underscores from names found in routes_manifest.py.
2. Case-insensitively fixes usages of these variables that might have wrong casing (e.g., ADMINPAGESETTINGS -> ADMINPAGESETTINGS).
3. Prints live fixing logs as requested.
"""

from pathlib import Path
import re
import sys

PROJECT_ROOT = Path.cwd()
ROUTES_MANIFEST = PROJECT_ROOT / "app" / "app" / "core" / "routes_manifest.py"

# File extensions to process
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".json", 
    ".html", ".css", ".scss", ".md", ".txt", ".yaml", 
    ".yml", ".toml", ".ini", ".cfg", ".env", ".sql", ".xml",
}

# Directories skipped
SKIP_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules",
    ".venv", "venv", "dist", "build", ".pytest_cache", ".mypy_cache",
}

# Words that are too common to blindly case-insensitively replace globally
COMMON_WORDS = {
    "home", "billing", "history", "tenants", "settings", "archive", 
    "backups", "tenant", "public", "healthcheck", "dashboard", 
    "error", "api", "static", "uploads", "favicon", "basepath",
    "pdfview", "pdfdownload"
}

def load_mappings():
    if not ROUTES_MANIFEST.exists():
        raise FileNotFoundError(ROUTES_MANIFEST)

    text = ROUTES_MANIFEST.read_text(encoding="utf-8")
    
    # Match any variable assignment in routes_manifest.py
    pattern = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', re.MULTILINE)
    
    underscore_mapping = {}
    target_names = {}
    
    for name in pattern.findall(text):
        if "_" in name:
            new_name = name.replace("_", "")
            underscore_mapping[name] = new_name
            target_names[new_name.lower()] = new_name
        else:
            target_names[name.lower()] = name

    print(f"Loaded {len(target_names)} identifiers from routes_manifest.py.")
    return underscore_mapping, target_names

def should_skip(path: Path):
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False

def replace_identifiers(text, underscore_mapping, target_names):
    total = 0

    # 1. Exact underscore replacements first
    for old, new in sorted(underscore_mapping.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(old)}\b")
        text, count = pattern.subn(new, text)
        total += count

    # 2. Class attribute case-insensitive replacements
    # specifically replace Routes.xxx -> Routes.XXX for ANY known target, even common ones
    def attr_replacer(match):
        prefix = match.group(1)
        word = match.group(2)
        lower_word = word.lower()
        if lower_word in target_names:
            target = target_names[lower_word]
            if word != target:
                nonlocal total
                total += 1
                return f"{prefix}.{target}"
        return match.group(0)
    
    attr_pattern = re.compile(r'\b(Routes|Names|Paths|Templates|Prefixes)\.([A-Za-z_][A-Za-z0-9_]*)\b')
    text = attr_pattern.sub(attr_replacer, text)

    # 3. General word case-insensitive replacements
    # We find all word boundaries and check if they case-insensitively match a target
    word_pattern = re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\b')
    
    new_text = []
    last_end = 0
    for match in word_pattern.finditer(text):
        word = match.group(0)
        lower_word = word.lower()
        if lower_word in target_names and lower_word not in COMMON_WORDS:
            target = target_names[lower_word]
            if word != target:
                new_text.append(text[last_end:match.start()])
                new_text.append(target)
                last_end = match.end()
                total += 1
                
    new_text.append(text[last_end:])
    text = "".join(new_text)

    return text, total

def main():
    try:
        underscore_mapping, target_names = load_mappings()
    except FileNotFoundError as e:
        print(f"Error: {e} not found.")
        sys.exit(1)

    files_changed = 0
    replacements = 0

    print("Starting fixing process (Live logs)...")

    for path in PROJECT_ROOT.rglob("*"):
        if should_skip(path):
            continue

        if not path.is_file():
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            original = path.read_text(encoding="utf-8")
        except Exception:
            continue

        updated, count = replace_identifiers(original, underscore_mapping, target_names)

        if count:
            path.write_text(updated, encoding="utf-8")
            print(f"Fixed {count:4d} instances in {path.relative_to(PROJECT_ROOT)}")
            files_changed += 1
            replacements += count

    print()
    print("=" * 60)
    print(f"Files changed : {files_changed}")
    print(f"Replacements  : {replacements}")
    print("=" * 60)

if __name__ == "__main__":
    main()