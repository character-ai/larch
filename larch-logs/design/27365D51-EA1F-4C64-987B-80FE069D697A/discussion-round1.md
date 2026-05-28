## Decision 1: Coverage scope
- **Question**: Wire only production --design-tmpdir consumers, or include test harnesses too?
- **Resolution**: Production consumers only (17 scripts). Skip the 3 test harnesses (scripts/test-revise-plan-with-waterfall.sh, skills/design/scripts/test-design-pause-resume.sh, skills/design/scripts/test-plan-review-loop.sh) — they are not /design or /implement orchestrator paths and use mktemp-controlled test fixtures.
- **Source**: user

## Decision 2: Missing sibling .md for emit-design-plan-preview.sh
- **Question**: The script-md-siblings rule says every .sh has a sibling .md. emit-design-plan-preview.md does not exist (pre-existing violation). Should this PR create it?
- **Resolution**: Out of scope for this PR. Wire the .sh; leave the missing .md as a separate concern.
- **Source**: user

## Decision 3: Existing wiring pattern is authoritative
- **Question**: Use the same pattern as scripts/dispatch-plan-voters.sh and skills/design/scripts/tally-plan-review.sh?
- **Resolution**: Yes — `source` the library (path depends on script location), then `larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?` after argv required-arg checks and before any read/write into $DESIGN_TMPDIR.
- **Source**: codebase

## Decision 4: Sibling .md updates
- **Question**: Update sibling .md for each modified script?
- **Resolution**: Yes — the validator call is a behavior change (now rejects misconfigured paths). 16 sibling .md updates required (17 scripts minus emit-design-plan-preview.md which has no sibling — per Decision 2).
- **Source**: codebase (script-md-siblings rule)

## Decision 5: Out-of-scope boundaries
- **Question**: What must NOT be touched in this PR?
- **Resolution**:
  - No changes to `scripts/lib-design-tmpdir.sh` (validator behavior unchanged).
  - No changes to the 2 already-wired scripts (`scripts/dispatch-plan-voters.sh`, `skills/design/scripts/tally-plan-review.sh`).
  - No changes to test harnesses.
  - No refactoring of unrelated code in target scripts.
- **Source**: derived from user answers and minimum-change SIMPLE-tier bias
