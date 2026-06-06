### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:26-44,162-188,348-376
- **Concern**: Merged drift exit 14 branches on DRIFT_TRIGGER_FIRED but plan omits KV plumbing. Scenario: _postplan_run_plan_size parses check-plan-size stdout via parse_kv_from_output which has no DRIFT_* cases; _postplan_build_kvs also omits them — DRIFT_TRIGGER_FIRED never binds and exit 14 never fires on Gate B/discussion merged fences
- **Proposed resolution**: Extend parse_kv_from_output and _postplan_build_kvs with DRIFT_* / BASELINE_* (mirror HARD_TRIGGER_FIRED); document in design-postplan-emit.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1019,skills/design/references/approval-gates.md:158
- **Concern**: Drift Continue omits step-2b.5 sentinel contract. Scenario: Plan says log Warnings and proceed on drift Continue but unlike rc=0 clean merged paths does not require : > .completed/step-2b.5 — pause/resume and step-boundary logic can treat plan-size check incomplete after operator accepts growth
- **Proposed resolution**: Specify drift Continue (standalone Step 2b.5 and merged _postplan_rc=14 arms) must mkdir .completed and touch step-2b.5 before continuing to Step 3 / Step 3.6; mirror rc=0 Gate B wording in approval-gates.md and discussion-rounds.md

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1703-1726
- **Concern**: Unified single-pass exit may be built from the legacy branch that omits post-round status mapping. Scenario: Production always passes --round-cap; only the multi-round loop body sets LOOP_STATUS=tally-error, degraded-empty-collector, and zero-findings-degraded-panel after _run_plan_review_round. Collapsing onto the legacy template leaves LOOP_STATUS=complete on tally failure and breaks run-step3-review.sh cap rollback plus SKILL.md Gate-B-bypass routing
- **Proposed resolution**: Explicitly hoist the post-round checks from the multi-round body (~1780-1818) into the single-pass exit (after one _run_plan_review_round, before _terminal_exit); do not treat lines 1704-1725 as the template

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1104
- **Concern**: skills/design/scripts/run-step3-review.sh:372. Scenario: Reduced LOOP_STATUS enum omits cap-reached
- **Proposed resolution**: Outer Gate-C cap guard in run-step3-review.sh still emits LOOP_STATUS=cap-reached; dropping it from the regex coerces valid cap hits to panel-failed and breaks the Step 3 cap-reached short-circuit (SKILL.md:1138) Explicitly keep cap-reached (and cap-reached branch-matrix row) in every reduced enum: SKILL.md regex, run-step3-review.sh validator, test-step3-orchestrator-fence.sh

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:20-44,348-376
- **Concern**: Plan branches merged drift on DRIFT_TRIGGER_FIRED but does not extend KV plumbing. Scenario: _postplan_run_plan_size parses check-plan-size stdout via parse_kv_from_output which has no DRIFT_* / BASELINE_* arms; _postplan_build_kvs omits them too, so _postplan_finish_merged_plan_size never sees DRIFT_TRIGGER_FIRED=true and Gate B/discussion merged fences never exit 14
- **Proposed resolution**: Extend parse_kv_from_output and _postplan_build_kvs for DRIFT_* and BASELINE_*; document keys in design-postplan-emit.md allowlist

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:20-45,162-183
- **Concern**: Merged drift exit 14 omits DRIFT_* KV plumbing. Scenario: _postplan_finish_merged_plan_size branches on DRIFT_TRIGGER_FIRED but the plan never updates parse_kv_from_output or _postplan_build_kvs; new check-plan-size.sh outputs never reach .design-postplan-emit-result.env so Gate B/discussion _postplan_rc=14 arms cannot prompt
- **Proposed resolution**: Extend the design-postplan-emit.sh bullet to add DRIFT_* / BASELINE_* parse arms, defaults, and _postplan_build_kvs forwarding (mirror HARD_TRIGGER_FIRED wiring)

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-doc-table-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.md:76-85
- **Concern**: Plan rewrites LOOP_STATUS/exit tables but not the `_run_post_apply_pipeline` / `check-plan-size.sh` section that still documents `plan-size-trigger` emissions. Scenario: After single-pass collapse the deleted post-apply pipeline remains documented; readers still expect loop-internal `plan-size-trigger` / `plan-validator-defects` handoffs conflicting with removed branch-matrix rows
- **Proposed resolution**: Add explicit plan step: delete `## check-plan-size.sh call in _run_post_apply_pipeline` (and related multi-round tail prose ~108) when removing `_run_post_apply_pipeline` from `plan-review-loop.sh`

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-flag-removal-atomicity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/parse-design-argv.md:17-26,48
- **Concern**: Parser contract doc still mandates eight success KVs including MANUAL_REQUESTED. Scenario: Plan updates parse-design-argv.sh and SKILL.md Step 0-pre (8→7) but omits this sibling contract; post-change stdout is seven KVs while the doc still says eight, and failure-mode mitigation (plan.txt:139) names the script/harnesses only
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/parse-design-argv.md — drop MANUAL_REQUESTED, change eight→seven KVs in Machine output and exit-code table; update test-parse-design-argv.md if it references the old count
