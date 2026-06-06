### FINDING_1: Merged drift exit 14 lacks DRIFT_* / BASELINE_* KV plumbing
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan branches merged drift handling on `DRIFT_TRIGGER_FIRED`, but never extends KV plumbing in `design-postplan-emit.sh`. `_postplan_run_plan_size` parses `check-plan-size` stdout through `parse_kv_from_output`, which has no `DRIFT_*` / `BASELINE_*` arms; `_postplan_build_kvs` omits them as well. As a result, `DRIFT_TRIGGER_FIRED` never binds into `.design-postplan-emit-result.env`, `_postplan_finish_merged_plan_size` never sees `DRIFT_TRIGGER_FIRED=true`, and exit 14 never fires on Gate B / discussion merged fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend parse_kv_from_output and _postplan_build_kvs with DRIFT_* / BASELINE_* (mirror HARD_TRIGGER_FIRED); document in design-postplan-emit.md
  - From Cursor-Pragmatic: Extend parse_kv_from_output and _postplan_build_kvs for DRIFT_* and BASELINE_*; document keys in design-postplan-emit.md allowlist
  - From Cursor-Requirements: Extend the design-postplan-emit.sh bullet to add DRIFT_* / BASELINE_* parse arms, defaults, and _postplan_build_kvs forwarding (mirror HARD_TRIGGER_FIRED wiring)


### FINDING_2: Drift Continue omits step-2b.5 sentinel contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan says to log warnings and proceed on drift Continue, but unlike the `rc=0` clean merged paths it does not require `: > .completed/step-2b.5`. Pause/resume and step-boundary logic can therefore treat the plan-size check as incomplete after the operator accepts growth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify drift Continue (standalone Step 2b.5 and merged _postplan_rc=14 arms) must mkdir .completed and touch step-2b.5 before continuing to Step 3 / Step 3.6; mirror rc=0 Gate B wording in approval-gates.md and discussion-rounds.md


### FINDING_3: Single-pass exit omits post-round LOOP_STATUS mapping
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The unified single-pass exit may be built from the legacy branch that omits post-round status mapping. Production always passes `--round-cap`; only the multi-round loop body sets `LOOP_STATUS=tally-error`, `degraded-empty-collector`, and `zero-findings-degraded-panel` after `_run_plan_review_round`. Collapsing onto the legacy template leaves `LOOP_STATUS=complete` on tally failure and breaks `run-step3-review.sh` cap rollback plus SKILL.md Gate-B-bypass routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Explicitly hoist the post-round checks from the multi-round body (~1780-1818) into the single-pass exit (after one _run_plan_review_round, before _terminal_exit); do not treat lines 1704-1725 as the template


### FINDING_4: Reduced LOOP_STATUS enum omits cap-reached
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The reduced `LOOP_STATUS` enum omits `cap-reached`. The outer Gate-C cap guard in `run-step3-review.sh` still emits `LOOP_STATUS=cap-reached`; dropping it from the regex coerces valid cap hits to `panel-failed` and breaks the Step 3 cap-reached short-circuit (`SKILL.md:1138`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Outer Gate-C cap guard in run-step3-review.sh still emits LOOP_STATUS=cap-reached; dropping it from the regex coerces valid cap hits to panel-failed and breaks the Step 3 cap-reached short-circuit (SKILL.md:1138) Explicitly keep cap-reached (and cap-reached branch-matrix row) in every reduced enum: SKILL.md regex, run-step3-review.sh validator, test-step3-orchestrator-fence.sh


### FINDING_5: plan-review-loop.md still documents removed post-apply pipeline
- **Reviewer(s)**: Cursor-dyn-doc-table-consistency
- **Severity**: important
- **Concern**: The plan rewrites `LOOP_STATUS` / exit tables but not the `_run_post_apply_pipeline` / `check-plan-size.sh` section that still documents `plan-size-trigger` emissions. After single-pass collapse, the deleted post-apply pipeline remains documented; readers still expect loop-internal `plan-size-trigger` / `plan-validator-defects` handoffs that conflict with removed branch-matrix rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-table-consistency: Add explicit plan step: delete `## check-plan-size.sh call in _run_post_apply_pipeline` (and related multi-round tail prose ~108) when removing `_run_post_apply_pipeline` from `plan-review-loop.sh`


### FINDING_6: parse-design-argv.md still mandates eight success KVs
- **Reviewer(s)**: Cursor-dyn-flag-removal-atomicity
- **Severity**: important
- **Concern**: The parser contract doc still mandates eight success KVs including `MANUAL_REQUESTED`. The plan updates `parse-design-argv.sh` and SKILL.md Step 0-pre (8→7) but omits this sibling contract; post-change stdout is seven KVs while the doc still says eight, and failure-mode mitigation (`plan.txt:139`) names the script/harnesses only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-flag-removal-atomicity: Add ### UPDATED: skills/design/scripts/parse-design-argv.md — drop MANUAL_REQUESTED, change eight→seven KVs in Machine output and exit-code table; update test-parse-design-argv.md if it references the old count

