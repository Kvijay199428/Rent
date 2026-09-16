# Scenario 04 — Two Nested Skills Tie

## Setup
Populate `nested-skills/` with two specialists whose declared capabilities genuinely overlap
for a given finding (e.g. both a `ui-audit` and an `accessibility-audit` nested skill list
"contrast/readability review" as a capability). Set up a finding that plausibly fits both.

## Prompt to paste
> "This button's text is hard to read against its background — can you check what's wrong?"

## Checklist
- [ ] Recognizes the overlap explicitly rather than picking one silently
- [ ] Asks the user once which skill should own this kind of finding
- [ ] **Writes the answer into `skill-mapping.md`** as a declared mapping (this is the fix
      being tested — not just asking, but persisting the answer)
- [ ] On a second, similar finding later in the same session, does NOT re-ask — follows the
      now-declared mapping automatically

## Fail conditions
- Picks one of the two nested skills without surfacing the ambiguity at all
- Asks the user but never writes the resolution to `skill-mapping.md`
- Asks the same overlap question again later in the session despite having asked once already
