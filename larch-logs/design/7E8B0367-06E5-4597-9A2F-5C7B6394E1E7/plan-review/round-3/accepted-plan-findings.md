### FINDING_1: Standalone Step 2b.5 omits DRIFT_* / BASELINE_* KV parsing
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Concern**: The plan adds a drift branch gated on `DRIFT_TRIGGER_FIRED` but does not extend Step 2b.5 item 3’s rc=0 parse list (currently only `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS`, `PLAN_LINES`, `DIFF_LINES`, etc.). Retained callers that invoke `check-plan-size.sh` directly (e.g. override-after-defects) can hit drift after Gate B growth while `HARD_TRIGGER_FIRED=false`; validator exit 10 skips merged plan-size/drift. Unbound `DRIFT_TRIGGER_FIRED` falls through to the no-trigger branch and silently continues, leaving the residual sprawl ratchet active on the standalone path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the Step 2b.5 procedure, extend step 3 to parse DRIFT_TRIGGER_FIRED, DRIFT_MULTIPLE, DRIFT_PLAN_RATIO, DRIFT_DIFF_RATIO, BASELINE_PLAN_LINES, and BASELINE_DIFF_LINES from _plan_size_out (mirror HARD_TRIGGER_FIRED); insert the drift branch between partition and no-trigger per the stated precedence.
  - From Cursor-dyn-kv-chain-completeness: Extend Step 2b.5 item 3 rc=0 parse bullet to list every DRIFT_* / BASELINE_* key emitted by check-plan-size.sh, and add matching test-design-structure.sh grep pins (same pattern as lines 1082-1089)


### FINDING_2: Collapsed plan-review loop omits pre-round artifact clearing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The collapsed single-pass spec omits `_clear_session_root_review_artifacts` immediately before `_run_plan_review_round`. On Gate C re-entry to Step 3, stale `accepted-plan-findings.md` / `ballot.txt` at session root can remain; Gate B or tally may consume prior-round artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep one `_clear_session_root_review_artifacts` call immediately before `_run_plan_review_round` in the collapsed path (same as the first multi-round iteration today)


### FINDING_3: Merged drift exit 14 omits FD3 section emission
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Hard (exit 12) and partition (exit 13) call `_postplan_emit_hard_section` / `_postplan_emit_partition_section` before flush; approval-gates tells merged callers not to re-run Step 2b.5 display. Exit 14 only flushes KVs, so `_postplan_out` lacks `## Plan Size — Drift` and Gate B / discussion paths can prompt blind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `_postplan_emit_drift_section` (baseline + ratios) in the design-postplan-emit.sh plan; call it before flush/exit 14 like hard/partition; assert FD3 output in `test-design-postplan-emit.sh` drift-exit-14.


### FINDING_4: Step 0b still wires manual_requested into tier resolution and init
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 0b still passes `--manual-requested` and binds `manual_requested` in tier resolution. If the plan removes `--manual-requested` from `design-init-runparams.sh` but omits SKILL.md Step 0b sub-steps 5/6, live `/design` aborts at Step 0b (unknown option or argv contract failure).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit SKILL.md bullets: drop manual_requested from tier-resolution prose and Step 0b consume list; remove --manual-requested from the design-init-runparams.sh fenced invocation


### FINDING_5: Testing strategy omits lint harness for write-run-params signature
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The testing strategy omits the lint harness that pins `write-run-params --manual-gate-b` signature. Removing `manual_gate_b` without updating `scripts/test-lint-skill-md-flag-signature.sh` breaks `scripts/relevant-checks.sh` / `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add scripts/test-lint-skill-md-flag-signature.sh (and lint stub shapes) to Testing strategy alongside scripts/test-write-run-params.sh


### FINDING_6: Plan cites nonexistent test-design-route.sh
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: Testing cites nonexistent `skills/design/scripts/test-design-route.sh`. Resume `manual_gate_b` coverage lives in `scripts/test-design-structure.sh` (~1547-1548); the wrong path may send the implementer on a dead-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Replace the test-design-route.sh reference with scripts/test-design-structure.sh design-route resume pins


### FINDING_7: Plan misnames write-run-params CLI flag as --manual-requested
- **Reviewer(s)**: Cursor-dyn-flag-removal-completeness
- **Severity**: important
- **Concern**: The plan misnames the writer CLI flag as `--manual-requested`; production uses `--manual-gate-b`. An implementer may drop a nonexistent flag and leave `--manual-gate-b` parsing/emission in place, so `manual_gate_b` keeps flowing into `run-params.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-flag-removal-completeness: In `write-run-params.sh` step name `--manual-gate-b` explicitly; remove `MANUAL_GATE_B`, usage line, `require_enum`, and jq `--arg manual_gate_b`


### FINDING_8: drift-baseline.env on-disk key names unspecified
- **Reviewer(s)**: Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Concern**: The plan says to write `drift-baseline.env` after `PLAN_LINES`/`DIFF_LINES` are populated but does not specify key names. `check-plan-size.sh` reads `BASELINE_PLAN_LINES` and `BASELINE_DIFF_LINES` from that file; writing `PLAN_LINES=`/`DIFF_LINES=` keys lets drift silently never fire (baseline-absent graceful path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-chain-completeness: Add an explicit write contract: e.g. printf 'BASELINE_PLAN_LINES=%s\nBASELINE_DIFF_LINES=%s\n' "$PLAN_LINES" "$DIFF_LINES" > drift-baseline.env (or equivalent) matching the read keys in check-plan-size.sh


### FINDING_9: Thin-fence harness omits postplan exit arm 14
- **Reviewer(s)**: Cursor-dyn-kv-chain-completeness
- **Severity**: important
- **Concern**: `assert_postplan_thin_fence` / `assert_postplan_reference_thin_fence` still mandate only rc arms 0, 10, 11, 12, 13, 2, 1. Adding exit 14 to SKILL.md / approval-gates.md / discussion-rounds.md without updating these loops lets CI pass while merged drift consumption is missing from one or more fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-chain-completeness: Update the plan to require extending both assert_postplan_thin_fence loops (and the exit 12/13 contains checks at lines 830-831) to include arm 14 and exit 14 in design-postplan-emit.sh


