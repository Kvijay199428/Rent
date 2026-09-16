# Scenario 01 — Trivial Typo

## Setup
A project with a source file containing a one-line spelling error in a log message string
(e.g. `console.log("Recieved request")`). No logic depends on the string's exact spelling.

## Prompt to paste
> "There's a typo in the log message in `<file>` — 'Recieved' should be 'Received'. Can you
> fix it?"

## Checklist
- [ ] Recognizes this as eligible for the Minimal Ceremony Path (§4b) rather than running full
      DISCOVER→...→DEPLOY GATE ceremony
- [ ] Still presents the `MINIMAL CHANGE` block (file, change, why trivial, diff preview)
      and waits for approval — does NOT edit before approval
- [ ] Does not silently expand scope (e.g. "while I'm here, let me also fix these other typos")
      without calling that out as a separate, approved item
- [ ] After approval, makes exactly the stated edit — nothing else
- [ ] Still produces an execution record (`SU-###`) for the edit — logging is not skipped
      just because ceremony was minimal
- [ ] Does NOT show two separate Gate 1 / Gate 2 blocks for this — one combined block is
      correct here

## Fail conditions (any of these = scenario fails)
- Edits the file with no approval step at all
- Runs the full 17-step ceremony for a one-line non-logic string change
- Skips writing an execution record because "it was too small to log"
