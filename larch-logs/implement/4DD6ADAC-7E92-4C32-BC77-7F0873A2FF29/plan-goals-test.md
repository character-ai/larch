## Goal
Implement issue #6034: [IMPLEMENTING] [OOS] Terminal-stall closeout path never pins the architectural-guidelines note.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Main agent

**Phase**: implement

**Vote tally**: N/A — auto-filed per policy


## Description

python/larch/state/closeout.py — `step_16_16a` (invoked from `python/larch/report/final_report.py:918-919` `step18b_final_report`, the terminal-unrecoverable-stall recover-then-report path documented in `skills/implement/scripts/step-18.md`) never calls `_pin_architectural_guidelines_note_best_effort`; only `step_16_17` (the green-path / successful-recovery path) does. Reproduction: a run stages an architectural-guidelines assessment, stalls before ever reaching Step 16/17, and recovery never succeeds; Step 18b renders the final report via `step_16_16a` + `write_final_report`, and the guideline note is dropped unconditionally — independent of the fingerprint-drift refresh-retry fixed in #6021. Suggested fix: decide whether `_pin_architectural_guidelines_note_best_effort` should also run inside `step_16_16a` (or be factored so both callers share one call site), guarding against a double-pin attempt if the same run later also reaches `step_16_17`.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
