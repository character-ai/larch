### FINDING_1: Step 1d.7 missing `PAUSE_OK=false` fail-closed after brainstorm-off elision
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Eliding `step1d5 --mode entry` when `brainstorm_requested=false` removes the indirect abort that today fires when pause-save prints `PAUSE_OK=false` and omits `STEP1D5_ACTION`. The planned Step 1d.7 prose only stops on `PAUSE_OK=true` and otherwise continues into `design-outline.md` / `SKIP_APPROVE_REQUESTED` binding. Because `check_pause_and_exit` prints `PAUSE_OK=false` and exits 0 without emitting `SKIP_APPROVE_REQUESTED=`, the orchestrator can treat a failed pause save as a normal fence return and proceed to outline work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add Step 1d.7 handling: if fence output has whole-line PAUSE_OK=false, abort /design before SKIP_APPROVE_REQUESTED binding and outline work (mirror Step 1d.5 missing-directive abort). Add test_step1d7_brainstorm_off_pause_ok_false_aborts with monkeypatched pause_save_main emitting PAUSE_OK=false.
  - From Cursor-Innovation: Add explicit `PAUSE_OK=false` stop (or abort when `SKIP_APPROVE_REQUESTED=` is missing after the fence), mirroring the Step 1d.5 `missing STEP1D5_ACTION` abort; pin it in `scripts/test-design-structure.sh` beside the existing Step 1d.5 pause/fail-closed contains.
  - From Cursor-Pragmatic: Split Step 1d.7 handling into three branches mirroring Step 1d.5: PAUSE_OK=true stops /design; if SKIP_APPROVE_REQUESTED= is missing or empty (including PAUSE_OK=false) print a fail-closed abort before outline work; otherwise bind skip_approve_requested and continue. Add a matching scripts/test-design-structure.sh contains pin parallel to the existing Step 1d.5 missing-STEP1D5_ACTION assertion.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_2: Structure test cannot enforce brainstorm-off guard before entry fence
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Planned `contains`-only pins in `scripts/test-design-structure.sh` verify elision prose exists but not that it precedes the `step1d5 --mode entry` launcher line. Misordered SKILL.md text (guard below the fence) would still pass while the dominant path keeps invoking the entry fence, defeating the turn-count goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Swap the planned contains assertion for check_context_before on skills/design/SKILL.md anchored at step1d5 --mode entry, requiring run-params / brainstorm_requested elision prose in the preceding context (same pattern as Step 0b and Step 3 pause contracts at lines 213-219).
  - From Cursor-Innovation: Use existing `assert_line_precedes` or `check_context_before` (same harness used for Step 3/5c load-before-fence pins) to require elision/run-params authority text before the bare `step1d5 --mode entry` launcher line.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Planned elision guard uses contains-only ordering check
- **Description**: Planned elision guard uses contains-only ordering check. Scenario: The planned structure assertions only require brainstorm-off elision prose and run-params authority text to exist somewhere in skills/design/SKILL.md. test-design-structure.sh already ships assert_line_precedes for ordering-sensitive contracts. A misplaced elision block below the step1d5 --mode entry launcher line would still pass while the dominant brainstorm-off path keeps running the entry fence and forfeits the turn savings.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

