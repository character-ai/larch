## Proposed Design Outline

### Goals
- Convert the `design-publish.sh` missing-`composed-plan.md` abort (exit 5) into a recoverable validator gate (exit 4).
- Allow Fix-and-retry to compose the file and proceed without restarting the design session.
- Update the test and sibling docs to match the new exit code.

### Non-goals
- Do not add a guard in `design-step5c.sh` (Option B not needed).
- Do not fix the pre-existing doc discrepancy where `design-publish.md` cites exit 2 for other `fail()` cases (out of scope).
- Do not change the `fail()` function or the step-5b sentinel exit behavior.

### Approach sketch
- In `design-publish.sh`: replace the `|| fail 'composed-plan.md missing...'` one-liner with an `if [[ ! -s ]]` block that sets `VALIDATE_STATUS=defects-found`, writes a diagnostic to `validate-plan-commands.log`, calls `write_result_env_and_emit`, then exits 4.
- In `test-design-publish.sh`: update the "empty composed plan" test to expect exit 4, capture stdout, and assert the result env has `VALIDATE_STATUS=defects-found`.
- In `design-publish.md`: fix Responsibility 1 to say exit 4 (not exit 2) for missing `composed-plan.md`, and update the exit code table and ordering invariants.
- In `SKILL.md` Step 5c: add a sentence noting that a missing or empty `composed-plan.md` also exits 4.

### Surfaces in scope
- `skills/design/scripts/design-publish.sh`
- `skills/design/scripts/test-design-publish.sh`
- `skills/design/scripts/design-publish.md`
- `skills/design/SKILL.md` (minimal clarification)

### Open questions
- None.
