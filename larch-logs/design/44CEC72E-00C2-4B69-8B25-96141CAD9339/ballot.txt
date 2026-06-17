### FINDING_1: Makefile loop harness still targets removed embedded pytest names
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `test-review-design-step3-loop` in the Makefile still selects pytest cases via `-k 'embedded_review or embedded_run_step3_review or embedded_waterfall or run_legacy'`. After the G3 port removes embedded-asset parity tests, that selector can collect zero tests (pytest exit 5) and break `test-harnesses-16`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin Makefile:519-520 to native loop/panel selectors (for example cap_reached or tally_error_rollback plus new native round/continuation tests) when embedded tests are removed

### FINDING_2: Step 3b-tail plan inverts step-4 sentinel vs Gate C preview ordering
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan changes when `.completed/step-4` is written relative to the Gate C preview path. Current `design-step3b-tail.sh` runs the Gate C timing mark and preview, emits `SKIP_APPROVE_REQUESTED_GATEC`, then creates `.completed/step-4`. The plan would write the sentinel before the Gate C preview. An interrupted or failed preview could leave Step 4 marked complete while Gate C was never surfaced, and resume may skip the missing Gate C surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan and tests to preserve current ordering: Gate C timing mark and preview first, then SKIP_APPROVE_REQUESTED_GATEC, then create .completed/step-4 after that path succeeds

### FINDING_3: RUN_STEP3_PLAN_REVIEW_LOOP_SH seam lacks a native default target
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan preserves the `RUN_STEP3_PLAN_REVIEW_LOOP_SH` override seam and says surviving `RUN_STEP3_*` hooks default to native CLI targets, but it does not register a single-round `plan-review` verb. After deleting `plan-review-loop.sh` and `_run_legacy`, an unset override can leave `run_step3_review` pointing at a deleted shell path or an unregistered command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Either call run_plan_review_round in process when the env override is unset and document RUN_STEP3_PLAN_REVIEW_LOOP_SH as override-only, or register a minimal native single-round plan-review verb before deleting the shell body

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:93-130
- **Concern**: [SCOPE-REDUCTION] Step 3b-tail ownership is split across wrapper shrink and native verb without a single commit owner. Scenario: The plan tells the wrapper to shrink around `plan-review step3b-tail` while also saying Step 4 tail work may stay wrapper-owned "unless fully ported." Today the live script performs FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC=`, and `.completed/step-4` inline before Gate C preview. A thin wrapper that only delegates preview drops those side effects and breaks Gate C.
- **Proposed resolution**: Pick one owner for this slice: either `plan-review step3b-tail` implements every tail side effect listed in the plan before the wrapper delegates, or keep the current bash body in the wrapper and defer wrapper shrink until that verb exists. Do not land a preview-only wrapper.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:93-130
- **Concern**: [SCOPE-REDUCTION] Step 4 tail authority is split between wrapper and `plan-review step3b-tail`. Scenario: Plan says shrink `design-step3b-tail.sh` to delegate to `plan-review step3b-tail` but also allows retaining FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC`, and `.completed/step-4` in the wrapper unless fully ported. An implementer can delegate to a preview-only native verb and drop Gate C prerequisites.
- **Proposed resolution**: Gate C can run without FINALIZE, rejected-findings markers, `SKIP_APPROVE_REQUESTED_GATEC`, or `.completed/step-4`. Pin one authority: `plan-review step3b-tail` must implement all current tail side effects before merge; `design-step3b-tail.sh` only sources env, pause-checks, and delegates. Remove the unless fully ported escape hatch.
