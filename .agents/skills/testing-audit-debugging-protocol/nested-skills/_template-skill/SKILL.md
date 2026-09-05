---
name: _template-skill
description: Replace this. One or two sentences on what this specialist investigates or does, and when the parent orchestrator should route to it.
---

# <Skill Display Name>

Replace this whole file. A nested skill is a **child capability** of
`testing-audit-debugging-protocol` — not a standalone top-level skill. It does not run its own
approval gates, deployment gate, discovery, correlation, or memory; all of that belongs to the
parent. This file should only describe:

## What this skill investigates or does

Plain description of the domain (e.g. "inspects the authentication middleware and backend
request flow" or "reviews CSS transition implementations for hard-coded durations").

## Capabilities

List the specific things this skill can be asked to do — should match `manifest.json`'s
`capabilities` array:

- capability-one
- capability-two

## Read-only vs change-making

State which operations are read-only (investigate/measure/verify) and which are change-making
(edit/generate/delete/migrate/deploy/write). Change-making operations always require Gate 2
from the parent before running.

## How to investigate

Step-by-step guidance for how this skill actually does its job — what to check first, what
tools/commands it uses, what a good finding looks like, what evidence to capture.

## What it returns to the parent

Describe the shape of what gets handed back — findings, evidence, suspected files, confidence
level — structured enough that the parent can drop it straight into its evidence graph
(see `references/evidence-and-traceability.md` in the parent skill).

## Scripts this skill may propose

If this skill sometimes needs a throwaway diagnostic script, say so here — every proposal
still goes through the parent's Nested Skill Execution Plan + script lifecycle rather than
being created silently.
