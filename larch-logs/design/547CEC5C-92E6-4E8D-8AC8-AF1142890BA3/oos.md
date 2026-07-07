### FINDING_2: Step 3 post-DONE reviewer-table and loop-routing contract has no migrated normative home
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 3 post-`DONE` reviewer-table emit and loop-routing sequence still lives only in `design-background-wait.md`, so migrating `/design` call sites to `bgjob-wait.md` would leave no normative home for printing `reviewer-status-table.txt` and parsing the result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a Step 3 post-`DONE` section to `skills/shared/bgjob-wait.md` (or inline in `skills/design/SKILL.md`): after final `bgjob wait` returns `DONE` with `BGJOB_RC=0` and `.completed/step-3-terminal` is present, Read and emit `reviewer-status-table.txt`, then parse `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` (legacy fallback only when absent). Replace the harness `check_context` pins that still require loading `Step 3 post-notification sequence` from `design-background-wait.md`.
  - From Cursor-Pragmatic: Add a Step 3 post-DONE section to `skills/shared/bgjob-wait.md` (or an explicit `skills/design/references/plan-review.md` anchor): after final `DONE` with `BGJOB_RC=0`, Read `$DESIGN_TMPDIR/reviewer-status-table.txt` once, then parse `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback; require `.completed/step-3` before Step 3b. Pin the new load target in `scripts/test-design-structure.sh`.
  - From Cursor-Requirements: Add a design-specific post-DONE section to `skills/shared/bgjob-wait.md` (or `skills/design/references/plan-review.md`) that preserves the reviewer-table Read/emit rules and result-env routing after final `bgjob wait` `DONE` with `BGJOB_RC=0`, rebinding reads to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback; pin it in `scripts/test-design-structure.sh`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Final validation omits the committed run-log half of AC6
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The final validation step checks only live session transcript entries, so it can miss notification-recovery turns that remain in the committed run logs and still violate acceptance criterion 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the Testing strategy / final-validation bullet to assert the committed run log also has no notification-recovery turns for migrated steps, matching issue AC 6.
  - From Cursor-Pragmatic: Extend the Testing strategy final-validation step to assert no notification-recovery turns in the committed `/design` and `/implement` run logs, matching acceptance criterion 6.
  - From Cursor-Requirements: Restore the AC6 run-log half explicitly in Testing strategy / final validation: inspect the committed `larch-logs` run log (or session transcript export) for notification-recovery turns, not just absence of `<task-notification>` in the live transcript.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh
- **Concern**: [SCOPE-REDUCTION] Step 5 MAV bgjob ownership targets the wrong launcher. Scenario: The plan converts `step-5-resume.sh` into a `bgjob start` launcher for `implement-step5-resume`, but the long-running immediate-background fence in `skills/implement/SKILL.md` is `python/cli.py implement checks-step5-resume`, and `dispatch_commit_route.py` already arms `_bg_wait_marker` on that composite. Converting `step-5-resume.sh` would not migrate the MAV/coder resume wait, and would wrongly bgjob-wrap the foreground `--record-only` timing path.
- **Proposed resolution**: Keep `step-5-resume.sh` foreground for `--record-only` and commit-handoff timing. Migrate `implement-step5-resume` by removing `_bg_wait_marker` from `checks_step5_resume_main` and adding orchestrator `bgjob start`/`wait` around the existing `checks-step5-resume` fence in `skills/implement/SKILL.md` and `checks-repair-loop.md`; update `scripts/test-implement-structure.sh` pins accordingly.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Step 18 cleanup docs still derive stall state from dead `.bg-wait-active` markers
- **Description**: Step 18 cleanup docs still derive stall state from dead `.bg-wait-active` markers. Scenario: The fifth stall-recovery layer in `step18-cleanup.md` still describes dead-PID `.bg-wait-active` for checks legs. After `_tokens.py` moves abandoned-checks detection to bgjob registry rows, operators following Step 18 prose may misread stall cause or retry path even when code classifies correctly.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/step18-cleanup.md:15
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Step 18 cleanup prose still documents `.bg-wait-active` fifth-layer stall detection
- **Description**: Step 18 cleanup prose still documents `.bg-wait-active` fifth-layer stall detection. Scenario: The plan migrates abandoned-checks classification in `python/larch/state/_tokens.py` and `stall-recovery.md` to bgjob registry rows, but `step18-cleanup.md` is not listed. Step 18 still loads that reference, so operators may follow retired marker guidance after Python routes through registry liveness.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/step18-cleanup.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

