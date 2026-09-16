from pathlib import Path
from datetime import datetime


# ============================================================
# Configuration
# ============================================================

SCRIPT_PATH = Path(__file__).resolve()
ROOT_DIR = SCRIPT_PATH.parent

# Output name is automatically derived from the skill root directory.
OUTPUT_FILE = ROOT_DIR / f"{ROOT_DIR.name}.md"

# Files/directories that should not be embedded.
EXCLUDED_FILES = {
    SCRIPT_PATH.name,
    OUTPUT_FILE.name,
}

EXCLUDED_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
    "nested-skills",
}

# File extensions that are useful for a single-source Markdown skill.
INCLUDED_EXTENSIONS = {
    ".md",
    ".json",
}


# ============================================================
# Helpers
# ============================================================

def should_include_file(path: Path) -> bool:
    """Return True when a file should be included in the bundle."""

    if path.name in EXCLUDED_FILES:
        return False

    if path.suffix.lower() not in INCLUDED_EXTENSIONS:
        return False

    return True


def should_skip_directory(path: Path) -> bool:
    """Return True when a directory should not be traversed."""

    return path.name in EXCLUDED_DIRECTORIES


def collect_files() -> list[Path]:
    """
    Recursively collect all supported files under the skill root.

    Files are sorted by their relative path to make output deterministic.
    """

    files = []

    for path in ROOT_DIR.rglob("*"):
        if not path.is_file():
            continue

        # Skip files inside excluded directories.
        if any(
            should_skip_directory(parent)
            for parent in path.relative_to(ROOT_DIR).parents
        ):
            continue

        if should_include_file(path):
            files.append(path)

    return sorted(
        files,
        key=lambda p: p.relative_to(ROOT_DIR).as_posix().lower(),
    )


def relative_path(path: Path) -> str:
    """Return a normalized project-relative path."""

    return path.relative_to(ROOT_DIR).as_posix()


def language_for(path: Path) -> str:
    """Return the Markdown code-fence language."""

    suffix = path.suffix.lower()

    if suffix == ".json":
        return "json"

    if suffix == ".md":
        return "markdown"

    return ""


def read_file(path: Path) -> str:
    """
    Read text using UTF-8.

    errors='replace' prevents one malformed character from stopping
    the entire bundle generation.
    """

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


# ============================================================
# Markdown Generation
# ============================================================

def build_document(files: list[Path]) -> str:
    """Build the complete single-source Markdown document."""

    generated_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    lines = []

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    lines.append(f"# {ROOT_DIR.name}")
    lines.append("")
    lines.append(
        "> Single-source bundle generated from the complete skill "
        "directory."
    )
    lines.append("")
    lines.append(f"- **Skill directory:** `{ROOT_DIR}`")
    lines.append(f"- **Generated:** `{generated_at}`")
    lines.append(f"- **Files included:** `{len(files)}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --------------------------------------------------------
    # Contents
    # --------------------------------------------------------

    lines.append("# Table of Contents")
    lines.append("")

    for index, path in enumerate(files, start=1):
        rel = relative_path(path)

        # Use a simple escaped heading for the TOC.
        anchor = (
            rel.lower()
            .replace("\\", "-")
            .replace("/", "-")
            .replace(".", "")
            .replace(" ", "-")
        )

        lines.append(f"{index}. [{rel}](#{anchor})")

    lines.append("")
    lines.append("---")
    lines.append("")

    # --------------------------------------------------------
    # File contents
    # --------------------------------------------------------

    for index, path in enumerate(files, start=1):
        rel = relative_path(path)
        content = read_file(path)
        language = language_for(path)

        lines.append(f"# {rel}")
        lines.append("")
        lines.append(f"**Source:** `{rel}`")
        lines.append("")
        lines.append(f"**File {index} of {len(files)}**")
        lines.append("")

        # Explicit source boundary.
        lines.append(
            f"<!-- BEGIN SOURCE: {rel} -->"
        )
        lines.append("")

        # Keep Markdown files readable while still preserving
        # their original contents.
        if path.suffix.lower() == ".md":
            lines.append(content.rstrip())
        else:
            lines.append(
                f"```{language}".rstrip()
            )
            lines.append(content.rstrip())
            lines.append("```")

        lines.append("")
        lines.append(
            f"<!-- END SOURCE: {rel} -->"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ============================================================
# Main
# ============================================================

def main() -> None:
    print("=" * 60)
    print("Skill Single-Source Generator")
    print("=" * 60)
    print()

    print(f"Skill root : {ROOT_DIR}")
    print(f"Output     : {OUTPUT_FILE}")
    print()

    files = collect_files()

    if not files:
        print("ERROR: No supported skill files were found.")
        print(
            f"Supported extensions: "
            f"{', '.join(sorted(INCLUDED_EXTENSIONS))}"
        )
        raise SystemExit(1)

    print("Files to include:")
    print()

    for path in files:
        print(f"  + {relative_path(path)}")

    print()
    print(f"Total files: {len(files)}")
    print()

    document = build_document(files)

    OUTPUT_FILE.write_text(
        document,
        encoding="utf-8",
        newline="\n",
    )

    print(f"Generated successfully:")
    print(f"  {OUTPUT_FILE}")
    print()

    # Basic verification.
    if not OUTPUT_FILE.exists():
        print("ERROR: Output file was not created.")
        raise SystemExit(1)

    output_size = OUTPUT_FILE.stat().st_size

    print(f"Output size: {output_size:,} bytes")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
