### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:995-1002
- **Concern**: Standalone Step 2b.5 omits DRIFT_* KV binding from the step-3 parse contract. Scenario: The plan adds a drift branch (line 48) that gates on DRIFT_TRIGGER_FIRED but does not extend the retained Step 2b.5 rc=0 parse list (currently HARD_TRIGGER_FIRED, TRIGGER_REASONS, PLAN_LINES, DIFF_LINES, etc. only). Override-after-defects still calls check-plan-size.sh directly; validator exit 10 skips merged plan-size/drift, so this path can hit drift after Gate B growth while HARD_TRIGGER_FIRED=false. Unbound DRIFT_TRIGGER_FIRED falls through to the no-trigger branch and silently continues — the residual sprawl ratchet on the retained standalone path.
- **Proposed resolution**: In the Step 2b.5 procedure, extend step 3 to parse DRIFT_TRIGGER_FIRED, DRIFT_MULTIPLE, DRIFT_PLAN_RATIO, DRIFT_DIFF_RATIO, BASELINE_PLAN_LINES, and BASELINE_DIFF_LINES from _plan_size_out (mirror HARD_TRIGGER_FIRED); insert the drift branch between partition and no-trigger per the stated precedence.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1737-1747
- **Concern**: Collapsed single-pass spec omits pre-round `_clear_session_root_review_artifacts`. Scenario: Gate C re-entry to Step 3 can leave stale `accepted-plan-findings.md` / `ballot.txt` at session root; Gate B or tally may consume prior-round artifacts
- **Proposed resolution**: Keep one `_clear_session_root_review_artifacts` call immediately before `_run_plan_review_round` in the collapsed path (same as the first multi-round iteration today)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:348-376
- **Concern**: Merged drift exit 14 omits FD3 section emission before exit. Scenario: Hard (12) and partition (13) call `_postplan_emit_hard_section` / `_postplan_emit_partition_section` before flush; approval-gates tells merged callers not to re-run Step 2b.5 display. Exit 14 only flushes KVs, so `_postplan_out` lacks `## Plan Size — Drift` and Gate B / discussion paths can prompt blind.
- **Proposed resolution**: Add `_postplan_emit_drift_section` (baseline + ratios) in the design-postplan-emit.sh plan; call it before flush/exit 14 like hard/partition; assert FD3 output in `test-design-postplan-emit.sh` drift-exit-14.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:451-466
- **Concern**: Step 0b still passes --manual-requested and binds manual_requested in tier resolution. Scenario: Plan removes --manual-requested from design-init-runparams.sh but omits SKILL.md Step 0b sub-step 5/6; live /design aborts at Step 0b (unknown option or argv contract failure)
- **Proposed resolution**: Add explicit SKILL.md bullets: drop manual_requested from tier-resolution prose and Step 0b consume list; remove --manual-requested from the design-init-runparams.sh fenced invocation

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-skill-md-flag-signature.sh:121-152
- **Concern**: Testing strategy omits lint harness that pins write-run-params --manual-gate-b signature. Scenario: Removing manual_gate_b without updating this make lint target breaks scripts/relevant-checks.sh
- **Proposed resolution**: Add scripts/test-lint-skill-md-flag-signature.sh (and lint stub shapes) to Testing strategy alongside scripts/test-write-run-params.sh

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:157
- **Concern**: Testing cites nonexistent skills/design/scripts/test-design-route.sh. Scenario: Resume manual_gate_b coverage is in scripts/test-design-structure.sh (~1547-1548); wrong path may send implementer on a dead-end
- **Proposed resolution**: Replace the test-design-route.sh reference with scripts/test-design-structure.sh design-route resume pins

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-flag-removal-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:23,100-102,192-202
- **Concern**: Plan misnames the writer CLI flag as `--manual-requested`; production flag is `--manual-gate-b`. Scenario: Implementer drops a nonexistent flag and leaves `--manual-gate-b` parsing/emission in place — `manual_gate_b` keeps flowing into run-params.json
- **Proposed resolution**: In `write-run-params.sh` step name `--manual-gate-b` explicitly; remove `MANUAL_GATE_B`, usage line, `require_enum`, and jq `--arg manual_gate_b`

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:100-103
- **Concern**: drift-baseline.env on-disk key names not specified. Scenario: Plan says write drift-baseline.env after PLAN_LINES/DIFF_LINES are populated but check-plan-size.sh reads BASELINE_PLAN_LINES and BASELINE_DIFF_LINES from that file; an implementer may write PLAN_LINES=/DIFF_LINES= keys and drift silently never fires (baseline-absent graceful path)
- **Proposed resolution**: Add an explicit write contract: e.g. printf 'BASELINE_PLAN_LINES=%s\nBASELINE_DIFF_LINES=%s\n' "$PLAN_LINES" "$DIFF_LINES" > drift-baseline.env (or equivalent) matching the read keys in check-plan-size.sh

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:995-1002
- **Concern**: Standalone Step 2b.5 step-3 KV parse list omits DRIFT_* keys. Scenario: Retained callers parse _plan_size_out for HARD_TRIGGER_FIRED/TRIGGER_REASONS/PLAN_LINES/... only; the new drift branch tests DRIFT_TRIGGER_FIRED but the plan never extends step 3 to parse DRIFT_TRIGGER_FIRED DRIFT_PLAN_RATIO DRIFT_DIFF_RATIO DRIFT_MULTIPLE BASELINE_* from stdout, and test-design-structure.sh already grep-pins other plan-size KVs (SOFT_ADVISORY DIFF_ADDED etc.)
- **Proposed resolution**: Extend Step 2b.5 item 3 rc=0 parse bullet to list every DRIFT_* / BASELINE_* key emitted by check-plan-size.sh, and add matching test-design-structure.sh grep pins (same pattern as lines 1082-1089)

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:329-331
- **Concern**: Thin-fence harness still mandates only rc arms 0 10 11 12 13 2 1. Scenario: assert_postplan_thin_fence / assert_postplan_reference_thin_fence loop over those arms; adding exit 14 to SKILL.md / approval-gates.md / discussion-rounds.md without updating this loop lets CI pass while merged drift consumption is missing from one or more fences
- **Proposed resolution**: Update the plan to require extending both assert_postplan_thin_fence loops (and the exit 12/13 contains checks at lines 830-831) to include arm 14 and exit 14 in design-postplan-emit.sh

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-loop-collapse-status-mapping
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1760-1818
- **Concern**: Post-round collapse cites hoist range ~1780-1818 but omits ordered guards outside that range and per-status predicates. Scenario: Implementer hoists only tally/zero-findings checks; `_round_rc != 0` (panel-failed at 1760-1777) and `main-agent-vote-required` (1751-1757) are skipped, so failures keep default `LOOP_STATUS=complete` from `_run_plan_review_round:1695` (legacy branch at 1704-1725 already does this for tally-error)
- **Proposed resolution**: Specify single-pass guard order explicitly: `_round_rc != 0` → `panel-failed` exit 1; then `main-agent-vote-required`; then `TALLY_PLAN_REVIEW_STATUS == tally-error` → `tally-error`; then zero-findings branches; then findings-present → `complete`

### OOS_1:
- **Description**: Top-level DRIFT shell defaults not named separately from _postplan_build_kvs. Scenario: Plan says extend _postplan_build_kvs defaults but not mirror HARD_TRIGGER_FIRED=false initialization at lines 126-132; if a parse arm is missed, set -u can trip before _postplan_finish_merged_plan_size
- **Reviewer**: Cursor-dyn-kv-chain-completeness
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-postplan-emit.sh:116-132
- **Phase**: design
