### FINDING_2: Step 3 entry dedup test pins lack negative guard for duplicate bash fences
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Step 3 entry dedup test pins are positive-only (`one parameterized Step 3 entry fence`, preserved `--reentry` note) with no structural negative guard for the duplicate bash fences at `skills/design/SKILL.md:524-532`. An implementer can add parameterized prose while leaving both `design-step3-entry.sh` and `design-step3-entry.sh --reentry` fences; `make test-design-structure` still passes and issue mechanism #3 (~conditional lines) ships incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `contains` for ``design-step3-entry.sh ${STEP3_REENTRY_FLAG}`` (or equivalent) plus `not_contains` for a second standalone ``design-step3-entry.sh --reentry`` bash fence (or an assert that only one Step 3 entry launcher fence remains).


### FINDING_4: run_step3b_finalize touches .completed/step-3b before STEP4_MODE handoff
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: `run_step3b_finalize` still writes `.completed/step-3b` before the new probe-only `STEP4_MODE` handoff. The plan asks finalize mode to probe dialectic eligibility and emit `STEP4_MODE`, but the marker is already touched inside `run_step3b_finalize`. A probe failure or pause between finalize and Step 4 will look like Step 3b completed even though the new Step 4 contract never finished, which can misroute resume logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the .completed/step-3b touch out of run_step3b_finalize or after the probe and STEP4_MODE emission succeed, and update the matching SKILL.md / design-step3b-entry.md wording to match


