# Discussion Round 1

Feature description is a corrected re-filing with explicit tasks, acceptance criteria, and non-goals. No scope questions required user input. The issue's three open questions were resolved from the codebase.

## Decision 1: Reship resume after waived assessment bail

- **Question**: Does the Step 8 reship start/wait pair resume cleanly after a `NEEDS_USER_INPUT` exit with the waiver present, and is the waived resume counted as a failed attempt by stall or attempt-cap accounting?
- **Resolution**: Yes, it resumes cleanly, and no attempt budget is consumed. The bail returns from `python/larch/implement/ship.py:1594` right after `_write_ship_state(phase="assessments")` (ship.py:1579), which preserves counters and writes no terminal overlay. On relaunch, `_resume_plan` maps `PHASE=assessments` with `pr_number=None` to `ResumePlan(start="pre-pr-compose")` with counters carried from state (`python/larch/implement/ship_resume.py:448-458`). Counters (`FIX_ATTEMPTS`, `TRANSIENT_RETRIES`, `REBASE_COUNT`, `ITERATION`) are incremented only by CI-fix/monitor loops, never by a reship launch. The resumed compose gate re-reads the durable `unavailable` notes; with the Task 2 waiver honored inside `_combined_assessment_result`, the gate falls through to `pr-create`. Plan adds a resume-shaped test to pin this.
- **Source**: codebase

## Decision 2: `ship-pr-state.sh` write mechanism for `reconcile-manual-merge`

- **Question**: Reuse driver `_write_ship_state` or a preserve-and-rewrite helper?
- **Resolution**: Preserve-and-rewrite helper modeled on `_merge_line_count_state` (`python/larch/report/final_report.py:427`), with symlink refusal and `O_NOFOLLOW` like `_write_ship_state`. Reusing `_write_ship_state` requires hydrating a full `RunContext` outside the driver and rewrites the whole file from context fields (stomping counters/branch fields, dropping non-allowlisted rows). Additionally the verb must mirror the driver's `phase="done"` clear-set (`STALL_TRACKING=false`, `STALL_STEP=`, `BAIL_REASON=`, `BAIL_NEEDS_USER_INPUT=false`, `BAIL_FAILURE_DETAIL_LOG=`, `EXIT_CODE=0`, `FAILED_RUN_ID=`; `python/larch/implement/ship_state.py:356-364`): leaving stale stall/bail rows would make `_stall_signal_is_terminal` (`python/larch/state/_normalize.py:166`) label a merged run `stalled`, defeating the back-fill for post-stall manual recoveries (acceptance criteria 2 and 4).
- **Source**: codebase

## Decision 3: Halt-rate harness coverage for Task 5

- **Question**: Does the Task 5 deferred-emit prose need a halt-rate-harness check or stay prose-only?
- **Resolution**: Add one focused needle assertion to `scripts/test-implement-anti-halt.sh` (and a line in its `.md` contract) pinning the new next-turn deferred-emit sentence. The harness contract says halt-prone boundary prose added to `skills/implement/SKILL.md` must be pinned in the same PR; the deferred-emit obligation is exactly the silent-turn-end family that harness exists for. No new harness.
- **Source**: codebase

3 decisions resolved (all from codebase; 0 AskUserQuestion calls).
