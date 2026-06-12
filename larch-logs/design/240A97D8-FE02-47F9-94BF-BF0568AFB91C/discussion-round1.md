## Decision 1: HARD_TRIGGER_FIRED rename
- **Question**: What should the plan-size trigger token be renamed to?
- **Resolution**: `SIZE_TRIGGER_FIRED`, with cascading renames to `cancelled-plan-size-hard` → `cancelled-plan-size`, `POSTPLAN_STATUS=plan-size-hard-trigger` → `plan-size-trigger`, `## Plan Size — Hard Trigger` → `## Plan Size — Trigger`.
- **Source**: user (Step 1c AskUserQuestion)

## Decision 2: Removal scope of exclusive HARD machinery
- **Question**: Does "all machinery and tests exclusive to HARD" include sketch scripts, dialectic scripts, snapshot-plan-round, and related tests?
- **Resolution**: Yes. The issue says "removing all machinery and tests exclusive to it." Exclusive HARD machinery includes: sketch prompts/launch references, dialectic-execution/debate references, design-step2a2/2a3/2a5/zero-sketch scripts, snapshot-plan-round.sh and tests, step3_loop_is_hard()/step3_loop_run_hard_snapshots() in review-design-step3-loop.sh, and HARD round-cursor logic in run-step3-review.sh.
- **Source**: codebase (issue acceptance criteria + codebase exploration)

## Decision 3: run-params.json tier fields
- **Question**: Should design_classification, design_classification_reason, design_classification_source, sketch_budget, and workflow_path be removed from run-params.json?
- **Resolution**: Yes. All five fields encode the old tier distinction. Remove them; the remaining flags (partition_requested, brainstorm_requested, etc.) are tier-agnostic and stay.
- **Source**: codebase

## Decision 4: NO_SKETCHES_CLASSIFIED_SIMPLE sentinel rename
- **Question**: What should NO_SKETCHES_CLASSIFIED_SIMPLE be renamed to?
- **Resolution**: NO_SKETCHES. The SIMPLE qualifier is no longer meaningful. The sentinel just indicates no sketches ran.
- **Source**: codebase (issue acceptance: SIMPLE must be removed from code)

## Decision 5: --workflow-path flag in render-run-summary.sh
- **Question**: Should --workflow-path be removed from render-run-summary.sh (and callers)?
- **Resolution**: Yes. The flag passed SIMPLE/HARD values, both of which must go. /implement callers already omit it. The Path bullet will no longer appear in /design run summaries.
- **Source**: codebase (docs/run-logs.md, render-run-summary.md)
