### FINDING_1: Override-path drift baseline is documented but not mechanically seeded
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-baseline-contract, Cursor-dyn-handoff-schema, Cursor-dyn-operator-fence
- **Severity**: important
- **Concern**: The retained Step 2b.5 Override path can run without any prior successful `--snapshot-original` baseline write, while `check-plan-size.sh` only reads an existing baseline. As a result, `drift-baseline.env` may remain absent and cumulative drift detection stays disabled for the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add write-once seeding to check-plan-size.sh (and check-plan-size.md): after a successful rc 0 size parse, if drift-baseline.env is missing write BASELINE_PLAN_LINES/BASELINE_DIFF_LINES from computed PLAN_LINES/DIFF_LINES under the same [[ ! -f ... ]] guard as design-postplan-emit, then compute drift; add a test-check-plan-size.sh case for validator-Override first parse seeds baseline and second parse can trigger drift
  - From Cursor-Edge: Add write-once seeding to check-plan-size.sh (when baseline file absent after successful rc 0 emit current PLAN_LINES/DIFF_LINES as BASELINE_*) or explicitly duplicate the design-postplan-emit guard in one script authority; add a test-check-plan-size case for Override-first seeding
  - From Cursor-Pragmatic: Add write-once baseline creation to check-plan-size.sh (or an explicitly named helper it calls): after computing PLAN_LINES/DIFF_LINES, if drift-baseline.env is absent write BASELINE_PLAN_LINES/BASELINE_DIFF_LINES under the same [[ ! -f ... ]] guard, then run drift comparison; mirror in check-plan-size.md
  - From Cursor-Requirements: Add one write-on-absent owner: either have `check-plan-size.sh` write `BASELINE_PLAN_LINES`/`BASELINE_DIFF_LINES` once when the file is missing (minimum change), or extend the Step 2b.5 standalone procedure and Gate B Override prose to seed the same keys after every retained caller’s first successful parse; add a harness case for Override-without-snapshot seeding
  - From Cursor-dyn-baseline-contract: Add one write-once path: either extend check-plan-size.sh to seed drift-baseline.env with [[ ! -f ... ]] when absent (then DRIFT false on that call), or add an explicit Step 2b.5 rc=0 sub-step that writes BASELINE_PLAN_LINES/BASELINE_DIFF_LINES from parsed PLAN_LINES/DIFF_LINES before drift branches. Mirror the design-postplan-emit guard and keys.
  - From Cursor-dyn-handoff-schema: Add a write-once block to check-plan-size.sh (or an equally named helper) that writes BASELINE_PLAN_LINES and BASELINE_DIFF_LINES to drift-baseline.env when the file is absent, using the same keys and guard as design-postplan-emit.sh; align check-plan-size.md with that producer
  - From Cursor-dyn-operator-fence: Add a write-once baseline seed to check-plan-size.sh (or design-postplan-emit.sh) when drift-baseline.env is absent after a successful size parse, using BASELINE_PLAN_LINES/BASELINE_DIFF_LINES keys and the same [[ ! -f ... ]] guard; add a harness case in test-check-plan-size.sh


### FINDING_3: Single-pass review status mapping can lose panel-failed
- **Reviewer(s)**: Codex-Edge, Codex-dyn-handoff-schema
- **Severity**: important
- **Concern**: The proposed single-pass terminal mapping lacks an explicit nonzero `_run_plan_review_round` / `panel-failed` branch before accepted-count or zero-collector fallback logic, so hard failures can be remapped to degraded or complete states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a _round_rc != 0 branch before the ordered accepted-count mapping that preserves LOOP_STATUS=panel-failed, writes the result env, records timing/snapshot as applicable, and exits nonzero
  - From Codex-dyn-handoff-schema: Add an explicit _run_plan_review_round rc/LOOP_STATUS=panel-failed branch before the degraded-empty-collector mapping, preserving panel-failed in stdout and .step3-plan-review-result.env.


### FINDING_4: Multi-round integration harness still expects removed converged behavior
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The integration harness remains outside the files-to-modify list while it still asserts converged multi-round `LOOP_STATUS`, so the single-pass rewrite can break `make test-harnesses-11`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-design-multi-round-integration.sh to Files (retire converged cases or re-scope to single-pass complete) and drop or rewrite plan-review-loop.md integration reference


### FINDING_5: Single-pass review rewrite can drop cumulative OOS findings
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The proposed single-pass flow omits the existing cumulative OOS save/restore and accumulation behavior, so reruns or degraded rounds can truncate previously accepted OOS items before filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the prior-cumulative OOS save/restore around the one review round, and call _accumulate_round_oos before terminal status mapping; restore the prior file on panel-failed/tally-error paths


### FINDING_6: Deprecated manual flags should remain accepted inert aliases
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Removing `--manual` / `-m` from argument parsing can break existing aliases or scripts even though Gate B is now always explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep --manual and -m accepted-but-inert in parse-design-argv.sh, stop emitting MANUAL_REQUESTED, and do not persist manual_gate_b


### FINDING_7: New drift result-env keys need default initialization
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Adding `DRIFT_*` and `BASELINE_*` keys without defaults can interact with `set -u` and abort early flush paths before plan-size parsing initializes them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Initialize all DRIFT_* and BASELINE_* variables beside existing PLAN_SIZE defaults before any flush path


### FINDING_8: Stale decompose-panel prompt still references deleted Step 3 plan-size-trigger routing
- **Reviewer(s)**: Codex-dyn-handoff-schema, Codex-dyn-operator-fence
- **Severity**: latent
- **Concern**: `decompose-panel.md` still describes retained Step 3 `LOOP_STATUS=plan-size-trigger` handling after that status is removed, which can steer Split-path operators toward obsolete routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-handoff-schema: Add skills/design/references/decompose-panel.md to the update list and remove the retained Step 3 plan-size-trigger return prose, leaving only the surviving merged and retained caller behavior.
  - From Codex-dyn-operator-fence: Add decompose-panel.md to the update set and remove the Step 3 plan-size-trigger clauses while preserving marker-touch guidance for remaining split callers


### FINDING_9: Standalone drift prompt lacks operator-visible drift context
- **Reviewer(s)**: Codex-dyn-operator-fence
- **Severity**: important
- **Concern**: The standalone Step 2b.5 drift branch may prompt Continue/Cancel without displaying current size, baseline, ratios, or threshold evidence, because `check-plan-size.sh` emits only KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-fence: Require the standalone drift branch to print current PLAN_LINES/DIFF_LINES, BASELINE_PLAN_LINES/BASELINE_DIFF_LINES, DRIFT_PLAN_RATIO/DRIFT_DIFF_RATIO, and DRIFT_MULTIPLE before AskUserQuestion


### FINDING_10: Gate C prose still implies auto-applied feedback
- **Reviewer(s)**: Codex-dyn-operator-fence
- **Severity**: latent
- **Concern**: Gate C re-run-review text still says reviewers see auto-applied feedback, conflicting with the new always-explicit Gate B behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-fence: Update this narrow Gate C sentence to say reviewers see the latest plan with operator-approved/applied feedback, with no auto-applied wording

