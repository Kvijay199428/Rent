#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import argparse
import shutil
import sys
import re


# Accept:
# ### `backend/file.py`
# ### backend/file.py
# ### **`backend/file.py`**
HEADER_RE = re.compile(
    r'^\s*#{3,6}\s*(?:\*\*)?\s*`?([^`\r\n]+?)`?\s*(?:\*\*)?\s*$'
)

FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')


def looks_like_file_path(value: str) -> bool:
    value = value.strip()

    if not value:
        return False

    # Remove Markdown formatting
    value = value.strip("`* ")

    # Project files normally contain / or filename extension,
    # or are common extensionless project files.
    common_files = {
        "Dockerfile",
        "Makefile",
        "Procfile",
        "LICENSE",
        "README",
        ".gitignore",
        ".dockerignore",
        ".env",
        ".env.example",
    }

    name = Path(value).name

    if "/" in value:
        return True

    if "." in name:
        return True

    if name in common_files:
        return True

    return False


def parse_markdown(md_file: Path):
    text = md_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    lines = text.splitlines(keepends=True)

    files = []

    i = 0

    while i < len(lines):

        line = lines[i].rstrip("\r\n")

        header = HEADER_RE.match(line)

        if not header:
            i += 1
            continue

        relative_path = header.group(1).strip()
        relative_path = relative_path.strip("`* ")

        if not looks_like_file_path(relative_path):
            i += 1
            continue

        # Search for code fence after header.
        # Allow blank lines between header and fence.
        j = i + 1

        while j < len(lines) and not lines[j].strip():
            j += 1

        if j >= len(lines):
            i += 1
            continue

        opening = FENCE_RE.match(
            lines[j].rstrip("\r\n")
        )

        if not opening:
            i += 1
            continue

        fence = opening.group(1)
        fence_char = fence[0]
        fence_length = len(fence)

        content_start = j + 1
        k = content_start

        content_lines = []

        while k < len(lines):

            stripped = lines[k].strip()

            # Closing ``` or ~~~
            if (
                stripped
                and set(stripped) == {fence_char}
                and len(stripped) >= fence_length
            ):
                break

            content_lines.append(lines[k])
            k += 1

        if k >= len(lines):
            print(
                f"WARNING: No closing fence for: "
                f"{relative_path}"
            )
            i += 1
            continue

        content = "".join(content_lines)

        # Normalize line endings
        content = content.replace(
            "\r\n", "\n"
        ).replace(
            "\r", "\n"
        )

        files.append(
            (relative_path, content)
        )

        i = k + 1

    return files


def validate_path(project_root: Path, relative_path: str):

    relative_path = relative_path.strip()

    relative = Path(relative_path)

    if relative.is_absolute():
        raise ValueError(
            f"Absolute path not allowed: "
            f"{relative_path}"
        )

    destination = (
        project_root / relative
    ).resolve()

    root = project_root.resolve()

    try:
        destination.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Path escapes project directory: "
            f"{relative_path}"
        )

    return destination


def backup_file(
    source: Path,
    backup_root: Path,
    project_root: Path
):

    relative = source.relative_to(
        project_root
    )

    destination = backup_root / relative

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        source,
        destination
    )


def restore(
    md_file: Path,
    project_root: Path,
    dry_run=False,
    make_backup=True
):

    md_file = md_file.resolve()
    project_root = project_root.resolve()

    print("=" * 70)
    print(" RENT PROJECT MARKDOWN RESTORER")
    print("=" * 70)
    print(f"Markdown : {md_file}")
    print(f"Project  : {project_root}")
    print(f"Dry run  : {dry_run}")
    print("=" * 70)

    if not md_file.exists():
        print(
            f"\nERROR: Markdown file not found:"
            f"\n{md_file}"
        )
        sys.exit(1)

    files = parse_markdown(md_file)

    if not files:

        print()
        print(
            "ERROR: No source-code files "
            "were detected."
        )

        print()
        print("Checking Markdown headings...")
        print()

        text = md_file.read_text(
            encoding="utf-8",
            errors="replace"
        )

        count = 0

        for number, line in enumerate(
            text.splitlines(),
            1
        ):

            if line.lstrip().startswith("#"):

                print(
                    f"{number:6}: "
                    f"{line[:150]}"
                )

                count += 1

                if count >= 30:
                    break

        sys.exit(1)

    print()
    print(
        f"Detected {len(files)} "
        f"source files."
    )
    print()

    # Detect duplicates
    path_counts = {}

    for path, _ in files:
        path_counts[path] = (
            path_counts.get(path, 0) + 1
        )

    duplicates = [
        path
        for path, count
        in path_counts.items()
        if count > 1
    ]

    if duplicates:

        print("WARNING: Duplicate paths:")
        print()

        for path in duplicates:
            print(
                f"  {path} "
                f"({path_counts[path]} times)"
            )

        print()
        print(
            "The LAST occurrence will "
            "ultimately remain."
        )
        print()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_root = (
        project_root /
        f".restore_backup_{timestamp}"
    )

    created = 0
    replaced = 0
    unchanged = 0
    failed = 0

    for index, (
        relative_path,
        content
    ) in enumerate(files, 1):

        print(
            f"[{index}/{len(files)}] "
            f"{relative_path}"
        )

        try:

            destination = validate_path(
                project_root,
                relative_path
            )

            exists = destination.exists()

            # Compare existing contents
            if exists and destination.is_file():

                try:

                    old_content = (
                        destination.read_text(
                            encoding="utf-8",
                            errors="replace"
                        )
                    )

                    old_content = (
                        old_content
                        .replace("\r\n", "\n")
                        .replace("\r", "\n")
                    )

                    if old_content == content:

                        print(
                            "    -> UNCHANGED"
                        )

                        unchanged += 1
                        continue

                except Exception:
                    pass

            if dry_run:

                if exists:
                    print(
                        "    -> WOULD REPLACE"
                    )
                else:
                    print(
                        "    -> WOULD CREATE"
                    )

                continue

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            if (
                exists
                and destination.is_file()
                and make_backup
            ):

                backup_file(
                    destination,
                    backup_root,
                    project_root
                )

            # Write temporary file first
            temp = destination.with_name(
                destination.name
                + ".restore_tmp"
            )

            temp.write_text(
                content,
                encoding="utf-8",
                newline="\n"
            )

            temp.replace(destination)

            if exists:

                replaced += 1

                print(
                    "    -> REPLACED"
                )

            else:

                created += 1

                print(
                    "    -> CREATED"
                )

        except Exception as exc:

            failed += 1

            print(
                f"    -> ERROR: {exc}"
            )

    print()
    print("=" * 70)
    print(" RESTORE SUMMARY")
    print("=" * 70)

    print(
        f"Detected  : {len(files)}"
    )

    if dry_run:

        print(
            "DRY RUN - nothing modified."
        )

    else:

        print(
            f"Created   : {created}"
        )

        print(
            f"Replaced  : {replaced}"
        )

        print(
            f"Unchanged : {unchanged}"
        )

        print(
            f"Failed    : {failed}"
        )

        if backup_root.exists():

            print()
            print(
                f"Backup    : "
                f"{backup_root}"
            )

    print("=" * 70)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "markdown",
        nargs="?",
        default="rent.md"
    )

    parser.add_argument(
        "--root",
        default="."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true"
    )

    args = parser.parse_args()

    restore(
        Path(args.markdown),
        Path(args.root),
        dry_run=args.dry_run,
        make_backup=not args.no_backup
    )


if __name__ == "__main__":
    main()
