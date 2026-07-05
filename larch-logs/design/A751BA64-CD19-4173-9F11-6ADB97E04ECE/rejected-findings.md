### [Plan Review] FINDING_2

### FINDING_2: Rewrite the sibling harness doc with the Step 8 contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The harness script is being updated, but its sibling markdown contract still describes the old Phase A/staged pin behavior, leaving the behavior/docs pair inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.md` and rewrite purpose/callers/harness text to match the compose-time Step 8 contract, removed Phase A prose, and new `guidelines-assessment` routing.


### [Plan Review] FINDING_9

### FINDING_9: Resume `guidelines-assessment` before falling back to postbump
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: A pre-PR resume with `PHASE=guidelines-assessment` and no PR number still falls through to a fresh resume, which reruns postbump instead of resuming at pr-create with the durable compose note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an early branch when state PHASE=guidelines-assessment and no PR exists: emit a dedicated ResumePlan.start (for example guidelines-assessment), teach ship.py to skip postbump for that start while still running the compose gate and pr-create path, and add the pre-PR resume test called for in test_ship.py


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:912-940
- **Concern**: [SCOPE-REDUCTION] Parallel compose-prepare CLI duplicates existing prepare. Scenario: The plan still adds a new compose-time prepare verb while `prepare_main` already reads guidelines, materializes the final diff, and emits the same KV/untrusted blocks. A second verb duplicates dispatch surface and migration work without closing a behavioral gap.
- **Proposed resolution**: Repurpose `architectural-guidelines prepare` / `prepare_main` for compose-time materialization (add HEAD metadata and selective stale-artifact cleanup), retire Step 7a-only invalidate semantics, and drop the extra CLI verb from the plan.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:849-940
- **Concern**: [SCOPE-REDUCTION] Plan adds a parallel compose-time prepare CLI though prepare/materialize already exist. Scenario: `prepare_main` already clears artifacts, reads guidelines, and calls `_emit_materialized_diff`; `materialize-diff` exposes the same materialization. A second compose-prepare verb expands `cli.py` dispatch, harness ports, and grep surface without a behavioral gap the acceptance criteria require
- **Proposed resolution**: Have `ship.py` call existing `materialize_implementation_diff` / internal prepare helpers for compose materialization; add only the compose-assessment write verb (or repurpose `write-staged-assessment`); drop the new prepare CLI from the plan


### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py:826-917
- **Concern**: [SCOPE-REDUCTION] Merge-loop compose reassessment is beyond the stated acceptance criteria. Scenario: Acceptance targets Step 8b pre-PR rebase drop notices; in-loop `goto_rebase` / `MERGE_RESULT_MAIN_ADVANCED` paths already created the PR and do not recompose the body. Mandating compose-gate reassessment there adds NEEDS_USER interrupts mid-CI without clearing an acceptance criterion
- **Proposed resolution**: Limit compose-gate reassessment to pre-PR create and explicit open-PR body updates (ci-fix/conflict resume). For merge-loop rebases, remove out-of-gate pin/invalidate only; drop the edge-case requirement to re-author during Step 12 monitoring


### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:912-940
- **Concern**: [SCOPE-REDUCTION] Plan adds a parallel compose-time prepare CLI though prepare already materializes. Scenario: architectural-guidelines prepare already invalidates stale artifacts, reads ARCHITECTURAL_GUIDELINES.md, and materializes the implementation diff; adding a second compose-prepare verb duplicates that surface and expands cli.py dispatch/grep churn without a behavioral gap Repurpose or extend prepare_main for the Step 8 compose gate (adjust invalidation semantics for compose-time only) instead of introducing a parallel prepare verb; repurpose write-staged-assessment into the compose durable writer where possible ### 1. correctness — `python/larch/implement/ship_resume.py:371-382` The compose-time flow depends on pausing after the first `NEEDS_USER_INPUT`, having the orchestrator write the durable note, and relaunching `step-8-ship.sh` without another postbump. Today `_resume_plan` maps any missing `PR_NUMBER` to `_fresh_resume_plan`, which always re-enters the `resume.start == "fresh"` postbump block in `ship.py`. The plan’s failure-mode note flags that risk but does not require the concrete fix at the actual fall-through site. Without an early `PHASE=guidelines-assessment` branch and matching `ship.py` skip-postbump handling, the end-to-end compose-time path can loop or never reach PR creation with the authored note. ### 2. architecture — `python/larch/core/architectural_guidelines.py:912-940` `prepare_main` already performs invalidate → read → materialize-diff, which is exactly what the compose gate needs after postbump. Adding a second compose-prepare CLI verb repeats that logic and increases migration surface (dispatch table, harness ports, grep cleanup) without closing a gap the feature requires. Minimum-change is to extend the existing `architectural-guidelines prepare` path for compose-time use and fold the durable write into a repurposed compose-assessment writer rather than parallel verbs.
- **Proposed resolution**:

