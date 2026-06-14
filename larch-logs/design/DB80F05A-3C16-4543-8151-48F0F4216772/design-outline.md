## Proposed Design Outline

### Goals
- Fix the inverted awk exit-code in `step-5-resume.sh` so round timing is correctly recorded for implement review rounds that escalate through `main-agent-vote-required`.
- Add a structural regression test that prevents the bare `exit found` pattern from being reintroduced.

### Non-goals
- Retroactively fix historical run logs (timing-report.json cannot be regenerated from the committed larch-log).
- Change the timing format, cost calculation, or `render-review-phase-detail.sh` rendering logic.

### Approach sketch
- Change `END { exit found }` to `END { exit found ? 0 : 1 }` in `step-5-resume.sh` (one-expression fix, consistent with majority of codebase usage).
- Add Invariant F to `test-implement-timing-rehydration.sh`: assert the correct pattern is present and bare `exit found }` is absent.
- Update the two sibling `.md` files for the changed script and test.

### Surfaces in scope
- `skills/implement/scripts/step-5-resume.sh`
- `skills/implement/scripts/step-5-resume.md`
- `scripts/test-implement-timing-rehydration.sh`
- `scripts/test-implement-timing-rehydration.md`

### Open questions
- None.
