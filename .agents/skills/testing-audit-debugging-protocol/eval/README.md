# Eval Scenarios

This protocol has never been run against a fixed set of scenarios to check whether it
actually produces the behavior it specifies — every gate, log, and rule here is currently
just an instruction, not something verified to hold across real sessions. This directory is a
minimal harness to close that gap.

## How to use

For each scenario in `scenarios/`, start a fresh session with this skill active, paste the
prompt, and go through the checklist. Check off each item as it either happens or doesn't. Do
not fix the skill to make an in-progress run pass — finish the run, record the result, then
fix the skill and re-run from scratch.

Track outcomes here as you build a track record:

| Scenario | Last run | Result | Notes |
|---|---|---|---|
| 01-trivial-typo | — | — | |
| 02-ambiguous-root-cause | — | — | |
| 03-nested-skill-needed | — | — | |
| 04-two-nested-skills-tie | — | — | |
| 05-script-creation-required | — | — | |
| 06-database-schema-conflict | — | — | |

## What "pass" means

A scenario passes if every checklist item is satisfied — not "mostly right" or "the spirit was
there." The whole point of the protocol is that gates and logs either happened or they didn't;
partial credit defeats the purpose of having a checklist instead of a vibe check.

## After a failing run

Run `scripts/validate_audit_memory.py` against whatever `.audit/memory/` the session produced
— a real failure often shows up there even if the transcript looked fine (e.g. a gate was
shown but never logged). Fix the specific gap in `SKILL.md` or the relevant `references/` file,
then re-run the *same* scenario from a fresh session before moving on.
