#!/usr/bin/env python3
"""
Read-only fingerprint helper for the smoke-testing skill.

Computes a single sha256 hash over the concatenated contents of the given
files, so a TODO item's stored fingerprint (smoke-todo.json item.fingerprint)
can be compared against the current state of the files it depends on. Only
reads files; never writes or modifies anything.

Usage:
    python3 compute_fingerprint.py <file1> [file2 ...]

Prints: sha256:<hex digest>

Missing files are hashed as their path string plus a "MISSING" marker, so a
deleted dependency still changes the fingerprint (visible if you diff old vs
new file lists) rather than being silently skipped.
"""
import hashlib
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: compute_fingerprint.py <file1> [file2 ...]", file=sys.stderr)
        return 2

    hasher = hashlib.sha256()
    for path in sorted(sys.argv[1:]):
        hasher.update(path.encode("utf-8"))
        try:
            with open(path, "rb") as f:
                hasher.update(f.read())
        except OSError:
            hasher.update(b"MISSING")
    print(f"sha256:{hasher.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
