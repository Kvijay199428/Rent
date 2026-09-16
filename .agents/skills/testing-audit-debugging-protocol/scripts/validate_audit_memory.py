#!/usr/bin/env python3
"""
validate_audit_memory.py — mechanical integrity check for .audit/memory/

This closes the biggest gap in the protocol as written: every gate, log write, and
schema was previously enforced only by instruction-following. This script actually
checks the artifacts a session produced, so drift gets caught instead of trusted.

Run from the project root (the directory containing .audit/):

    python3 <skill_dir>/scripts/validate_audit_memory.py [--project-root .]

Exit code 0 = clean. Exit code 1 = at least one violation found (treat as a blocking
finding for the deployment gate, per references/verification-and-integrity.md).

No third-party dependencies — stdlib only, so it runs anywhere Python 3 runs.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ID_RE = {
    "SU": re.compile(r"^SU-\d+$"),
    "SS": re.compile(r"^SS-\d+$"),
    "F": re.compile(r"^F-\d+$"),
    "E": re.compile(r"^E-\d+$"),
    "NS": re.compile(r"^NS-\d+$"),
    "SC": re.compile(r"^SC-\d+$"),
}


def load_jsonl(path):
    """Yield (line_no, record) for each non-empty line. Records a parse error as
    ('__error__', line_no, raw_line) instead of raising, so one bad line doesn't
    stop the whole scan."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except json.JSONDecodeError as e:
                yield i, {"__error__": str(e), "__raw__": line}


def load_json(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def check_pattern(record_id, kind, line_no, store, violations):
    pat = ID_RE.get(kind)
    if pat and not pat.match(str(record_id)):
        violations.append(f"{store}:{line_no} — id '{record_id}' does not match expected pattern {kind}-###")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    args = ap.parse_args()

    root = Path(args.project_root)
    mem = root / ".audit" / "memory"
    violations = []
    warnings = []

    if not mem.exists():
        print(f"No .audit/memory/ found under {root} — nothing to validate.")
        return 0

    # --- Load every store we know about ---
    selections = {r.get("selection_id"): r for _, r in load_jsonl(mem / "skill-usage.jsonl")
                  if "selection_id" in r} if False else {}
    # skill-usage.jsonl holds execution records (SU-###), not selections; selections
    # are logged separately per skill-selection.md's guidance to append to
    # skill-usage-log.md. We validate what's actually machine-readable here.

    executions = {}
    for line_no, rec in load_jsonl(mem / "skill-usage.jsonl"):
        if "__error__" in rec:
            violations.append(f"skill-usage.jsonl:{line_no} — invalid JSON: {rec['__error__']}")
            continue
        exec_id = rec.get("execution_id")
        check_pattern(exec_id, "SU", line_no, "skill-usage.jsonl", violations)
        executions[exec_id] = rec

        # --- Rule 1: change-making executions must show a real gate, never "none" ---
        if rec.get("type") == "change-making" and rec.get("approval_gate") in (None, "none"):
            violations.append(
                f"skill-usage.jsonl:{line_no} — execution {exec_id} is change-making but "
                f"approval_gate={rec.get('approval_gate')!r} (expected 'Gate 2')"
            )

        # --- Rule 2: nested-skill executions must carry parent/child linkage ---
        if rec.get("source") == "nested skill":
            for field in ("parent_skill", "child_skill_version", "parent_selection_id", "child_selection_id"):
                if not rec.get(field):
                    violations.append(f"skill-usage.jsonl:{line_no} — execution {exec_id} is a nested-skill "
                                       f"record but is missing '{field}'")
            if rec.get("parent_selection_id"):
                check_pattern(rec["parent_selection_id"], "SS", line_no, "skill-usage.jsonl", violations)
            if rec.get("child_selection_id"):
                check_pattern(rec["child_selection_id"], "NS", line_no, "skill-usage.jsonl", violations)

        # --- Rule 3: every evidence id referenced must look well-formed ---
        for ev in rec.get("evidence_produced", []) or []:
            check_pattern(ev, "E", line_no, "skill-usage.jsonl", violations)

    findings = {}
    for line_no, rec in load_jsonl(mem / "findings.jsonl"):
        if "__error__" in rec:
            violations.append(f"findings.jsonl:{line_no} — invalid JSON: {rec['__error__']}")
            continue
        fid = rec.get("id")
        check_pattern(fid, "F", line_no, "findings.jsonl", violations)
        findings[fid] = rec
        # Rule 4: a FIXED/VERIFIED finding should reference at least one execution record
        if rec.get("status") in ("FIXED", "VERIFIED") and not rec.get("execution_ids") and not rec.get("evidence"):
            warnings.append(f"findings.jsonl:{line_no} — finding {fid} is {rec.get('status')} but cites no "
                             f"execution/evidence — check it's actually traceable")

    script_plans = {}
    for line_no, rec in load_jsonl(mem / "script-plans.jsonl"):
        if "__error__" in rec:
            violations.append(f"script-plans.jsonl:{line_no} — invalid JSON: {rec['__error__']}")
            continue
        sid = rec.get("script_id")
        check_pattern(sid, "SC", line_no, "script-plans.jsonl", violations)
        script_plans[sid] = rec
        # Rule 5: every script that reached CREATED or later must show Gate 2 approval
        if rec.get("lifecycle") in ("CREATED", "EXECUTED", "EVIDENCE_CAPTURED", "RETAINED") \
                and rec.get("approval") != "Gate 2 required":
            violations.append(f"script-plans.jsonl:{line_no} — script {sid} reached "
                               f"'{rec.get('lifecycle')}' without approval == 'Gate 2 required'")
        # Rule 6: REMOVED scripts must record a reason
        if rec.get("lifecycle") == "REMOVED" and not rec.get("removal_reason"):
            violations.append(f"script-plans.jsonl:{line_no} — script {sid} is REMOVED with no removal_reason")

    nested_plans = {}
    for line_no, rec in load_jsonl(mem / "nested-skill-selection.jsonl"):
        if "__error__" in rec:
            violations.append(f"nested-skill-selection.jsonl:{line_no} — invalid JSON: {rec['__error__']}")
            continue
        pid = rec.get("plan_entry_id")
        check_pattern(pid, "NS", line_no, "nested-skill-selection.jsonl", violations)
        nested_plans[pid] = rec
        # Rule 7: a nested skill plan entry proposing scripts must reference ones that exist
        for sc in rec.get("scripts_proposed", []) or []:
            if sc not in script_plans:
                warnings.append(f"nested-skill-selection.jsonl:{line_no} — plan {pid} references "
                                 f"script {sc} not found in script-plans.jsonl (may not be written yet)")
        # Rule 8: CHANGE-MAKING plan entries must not be marked 'approved' without a
        # corresponding change-making execution showing Gate 2 (best-effort cross-check)
        if rec.get("mutation_status") == "CHANGE-MAKING" and rec.get("approval") == "approved":
            matching = [e for e in executions.values()
                        if e.get("child_selection_id") == pid and e.get("type") == "change-making"]
            if matching and any(e.get("approval_gate") != "Gate 2" for e in matching):
                violations.append(f"nested-skill-selection.jsonl:{line_no} — plan {pid} is CHANGE-MAKING "
                                   f"and approved, but a linked execution lacks Gate 2")

    registry = load_json(mem / "nested-skill-registry.json")
    if registry is not None:
        seen_ids = set()
        for entry in registry.get("skills", []):
            sid = entry.get("id")
            if sid in seen_ids:
                violations.append(f"nested-skill-registry.json — duplicate skill id '{sid}'")
            seen_ids.add(sid)
            if not entry.get("version"):
                warnings.append(f"nested-skill-registry.json — skill '{sid}' has no version recorded")

    # --- Report ---
    print(f"Checked {mem}")
    print(f"  executions: {len(executions)}, findings: {len(findings)}, "
          f"script plans: {len(script_plans)}, nested-skill plans: {len(nested_plans)}")
    print()
    if violations:
        print(f"VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")
    else:
        print("No violations found.")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}) — not blocking, but worth checking:")
        for w in warnings:
            print(f"  - {w}")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
