# Tool Orchestration — Read-Only vs Change-Making, & Child-Skill Enforcement

This reference is part of the **testing-audit-debugging-protocol** skill — orchestrator edition. Load it whenever you are about to **invoke** a tool or a child skill, and whenever you must classify an invocation as read-only or change-making.

The core question tool orchestration answers: *"Does using this tool/child skill require approval, or is it just reading/analyzing?"*

---

## 1. Read-Only vs Change-Making

Classify every invocation. When unsure, treat it as **change-making** and ask.

### 1.1 Read-only / investigative (no approval, but must be recorded)
* Running the existing test / lint / build / typecheck commands
* Static analysis, reading files, inspecting structure
* Searching documentation, specs, or the web for expected behavior
* A skill used purely to *read* or *inspect* an artifact (read a `.docx`, check a spreadsheet formula)
* Viewing screenshots/images to compare expected vs. actual UI
* Non-mutating analysis (differential verification that only reads UI/API/DB)

### 1.2 Change-making (approval required — Gate 2)
* Any skill/tool invocation that writes, edits, generates, or deletes a file in the project
* Any invocation of a write-capable connector (ticket creation, deployment, migrations, package installs)
* Any skill whose output is meant to directly become the fix (e.g. a code-generation skill producing the patch)
* Any command that mutates project state even if not a "code edit" (seeding a DB, running a destructive migration)

---

## 2. Child-Skill / Child-Tool Read-Only Enforcement

Any skill or tool you invoke is a *child* of this orchestrator and is subject to the **same read-only default**. When you delegate to a child:

1. **Confirm scope.** Is the child being invoked in read-only scope, or is its mutation explicitly approved via Gate 2?
2. **Record the classification.** The execution record's `type` field is `read-only` or `change-making`, and its `approval_gate` reflects the gate status.
3. **Refuse unintended mutation.** If a child appears able to or starts to mutate the project outside an approved change budget, stop, report, and ask.
4. **Don't launder changes.** You may not invoke a child "read-only" and then let it write as a side effect; a child that writes is change-making regardless of how it was framed.

---

## 3. Tool-Specific Notes

* **Project-native tools** (the repo's own test runner, linter, build) are usually the best fit and are read-only when they only run tests/checks. Their *outputs* are evidence.
* **Write-capable connectors** (deploy, migrate, install, ticket) are change-making by definition and need Gate 2 even if they don't touch source files directly.
* **Shell/execution tools** are read-only when used to inspect (`cat`, `git status`, `ls`, running tests) and change-making when used to mutate (`rm`, `git reset --hard`, writing files). Be explicit about which you are doing.

---

## 4. Execution Records for Tools

Every tool invocation produces an execution record (see `schemas/tool-execution.schema.json` and `templates/tool-execution.md`) with the same mandatory fields as a skill execution record, plus the tool's `command`/`call_type`. It is appended to `.audit/memory/tool-usage.jsonl` (and mirrored into `skill-usage-log.md`) so tool usage is as auditable as skill usage.

---

## 5. Rules

* Read-only use is **allowed and encouraged for gathering evidence** — but must be logged.
* Change-making use is **gated** — never run without Gate 2 approval.
* A tool classified read-only in one context may be change-making in another (e.g. `sqlite3 file.db 'SELECT ...'` is read-only; `sqlite3 file.db 'DELETE ...'` is change-making). Classify per invocation, not once per tool.
* Never let an execution record's mere existence imply approval — logging a use and approving a change are different things.
