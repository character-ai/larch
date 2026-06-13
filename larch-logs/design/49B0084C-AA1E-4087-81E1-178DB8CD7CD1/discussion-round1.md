## Decision 1: All four areas in scope
- **Question**: Which parts of the Gantt bug are in scope?
- **Resolution**: All four: postplan-failed path timing fix, label quality, in-flight progress report Gantt, implement skill parity.
- **Source**: user

## Decision 2: postplan-failed paths to fix
- **Question**: Which terminal exits in `review-design-step3-loop.sh` are missing `step3_loop_record_timing` after plan revision runs?
- **Resolution**: Three paths where plan revision is already complete but loop exits without recording timing: (1) `awaiting-post-apply` → `postplan-failed` default arm, (2) `awaiting-postplan-operator` failure path, (3) `awaiting-continuation` → `if [[ "$post_rc" -ne 0 ]]`. Fix all three.
- **Source**: codebase

## Decision 3: Label quality targets
- **Question**: Which output filenames need better labels?
- **Resolution**: (1) `aggregator-output.txt` → derive returns "unknown/aggregator" → fix to "aggregator". (2) `codex-output.txt` / `cursor-output.txt` (plan revision) → derive returns "unknown/codex"/"unknown/cursor" → fix by passing explicit `--timing-task-kind codex-plan-autofix`/`cursor-plan-autofix` in `revise_plan_with_waterfall_main`. (3) `scout-plan-manifest.json.raw` → derive returns long "unknown/scout-plan-manifest.json.raw" → fix to "scout". Fix in both `render-review-phase-detail.sh` derive.awk and `progress_report.py` `_derive_progress_label`.
- **Source**: codebase

## Decision 4: Implement timing edge case
- **Question**: Does `review-implement-step5-loop.sh` have the same postplan-failed edge case?
- **Resolution**: No. `_emit_implement_round_timing_row` is called at every terminal exit point (lines 256–467). The implement path already handles all terminal exits correctly. No fix needed for timing row writing. Only label quality and in-flight Gantt apply to implement.
- **Source**: codebase

## Decision 5: In-flight Gantt scope
- **Question**: Should the in-flight Gantt use a label map from available manifests?
- **Resolution**: Yes. `plan-review-slots.ndjson` exists in the design tmpdir before reviewers start. Pass its data as label context so reviewer labels match the completed-round Gantt. For implement, use the round dir's `panel-manifest.ndjson` if present, else fallback to derive.
- **Source**: codebase
