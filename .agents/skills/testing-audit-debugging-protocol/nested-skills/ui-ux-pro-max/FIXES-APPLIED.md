# Fixes Applied — Complete Bundle (68 files, incl. scripts/*.py)

This is the first version built from the truly complete source: `SKILL.md`, 15 `.json`, 37
`.csv`, and 15 `.py` files (`scripts/core.py`, `scripts/design_system.py`,
`scripts/reasoning_contract.py`, `scripts/search.py`, `scripts/validate_data.py`, and 10 test
modules). This let me actually run the code instead of only reading data files.

## 1. Hardcoded absolute path (SKILL.md, 17 occurrences) — fixed, same as before
`~/.opencode/skills/ui-ux-pro-max/scripts/search.py` → `./scripts/search.py`, with a note that
it must resolve relative to wherever this skill is actually installed.

## 2. Invalid JSON/CSV/Python — stray code-fence wrapping (67 files) — fixed
Every one of the 15 JSON, 37 CSV, and **15 Python** files was wrapped in a leading/trailing
` ``` ` fence from the export tool. Stripped all 67. Validated: JSON via `json.load()` (15/15),
CSV via `csv.reader` + per-row column-count check (37/37, zero ragged rows), Python via
`compile()` and `py_compile` (15/15 — no syntax errors).

## 3. Actually ran the code (new — only possible with scripts/*.py present)

**Full test suite:** `python3 -m unittest discover -s scripts/tests -v` → **130 of 132 tests
pass.** The 2 failures are both `ImportError` at collection time, not logic failures:

- `test_catalog_refresh.py` and `test_relevance_evaluator.py` both do
  `next(parent for parent in Path(__file__).resolve().parents if <marker file exists>)` to
  locate the repo root, where the marker files are `scripts/refresh-google-fonts.py`,
  `scripts/refresh-icon-catalog.py`, and `scripts/evaluate-relevance.py`. **None of these three
  scripts have appeared in any of the three uploads so far.** They're maintenance/tooling
  scripts (catalog refresh + the relevance-metric evaluator), not part of the core search path
  — `search.py`, `core.py`, `design_system.py`, and `reasoning_contract.py` are all present and
  fully covered by the other 130 passing tests. But this does mean **the relevance-threshold
  claims in `relevance-thresholds.json` still can't be mechanically verified** — the one script
  that would actually compute precision@1/routing-accuracy against `relevance-cases.json`
  (`evaluate-relevance.py`) is the one still missing.

**Ran real queries end-to-end**, not just unit tests:
- `python3 scripts/search.py "glassmorphism dashboard" --domain style --max-results 2` →
  correctly returned the Glassmorphism style row with full metadata.
- `python3 scripts/search.py "modern SaaS dashboard dark mode" --design-system --persist
  -p "TestProj" --output-dir /tmp/testproj` → correctly detected dark-mode intent, selected a
  dark-appropriate palette (background `#0F172A`, foreground `#F8FAFC`), and wrote
  `design-system/testproj/MASTER.md`. The persistence path genuinely works.

## Still missing (out of scope — not in any upload yet)
- `scripts/refresh-google-fonts.py`, `scripts/refresh-icon-catalog.py`,
  `scripts/evaluate-relevance.py` — needed to make the full test suite collectible (132/132)
  and to actually verify the relevance-threshold claims mechanically. If you want those two
  test modules to run and the relevance floors independently checked, these three files are
  what's still needed.
