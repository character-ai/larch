### FINDING_1: Env-read failure path still depends on deleted loop script for escalation evidence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `design-step3-review.sh` still `source`s `review-design-step3-loop.sh` on `.step3-review-result.env` read failure solely to call `step3_record_report_evidence`. After `review-design-step3-loop.sh` is deleted per the C3a1 cutover, that failure path cannot load escalation helpers; Step 3 may skip `record-escalation` evidence and `test-design-step3-review.sh` runtime checks break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Move step3_record_report_evidence/postplan-failed staging into plan_review.py (invoked from plan-review run) or a tiny retained bash helper; drop the review-design-step3-loop.sh source from design-step3-review.sh




### FINDING_1: Test harness still depends on deleted loop script
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan deletes `review-design-step3-loop.sh` but does not retarget `test-design-step3-review.sh`. That harness sources the deleted script for runtime escalation-ledger and `step3_loop_persist_envelope` remap checks, so `make test-design-step3-review` (shard `test-harnesses-4`) breaks and regression coverage for `record-escalation` behavior is lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an UPDATED entry for `test-design-step3-review.sh` (call `plan-review record-escalation-evidence` / import `plan_review`) or retire it only after porting its runtime assertions into `python/test_plan_review.py`; update Makefile shard 4 and relevant-checks routing accordingly


### FINDING_2: `design-driver.sh` TALLY action still targets retired shell script
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `design-driver.sh` still dispatches `ACTION=TALLY` to the retired `tally-plan-review.sh` path while the plan only calls out `EMIT_PLAN` and `FINALIZE` cutover. After the absorbed script is deleted, any `ACTION=TALLY` dispatch fails with a missing script even though a `plan-review tally` CLI exists, violating the direct call-site cutover requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update the TALLY branch to call `python3 "$PLUGIN_ROOT/python/cli.py" plan-review tally`, or explicitly remove the TALLY action with all producers updated
  - From Cursor-Requirements: Cut the TALLY branch over to `python3 "$PLUGIN_ROOT/python/cli.py" plan-review tally --design-tmpdir "$DESIGN_TMPDIR" "$@"`


### FINDING_3: Step 3 preview sentinel contract not ported with `run-step3-review.sh` retirement
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: `run-step3-review.sh --preview-only` currently owns tmpdir allowlist validation, re-entry suppression via `.step3-entry-plan-printed`, and header-gated sentinel touch. Replacing that path with bare `plan-review preview --variant step3` (which only renders text) drops the sentinel owner. Gate C re-entries and missing-plan repair paths may skip or duplicate the plan preview, or touch the sentinel on warning-only output depending on implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Move the sentinel contract into `plan-review preview` for `--variant step3` (or keep a thin bash fence): validate tmpdir, exit 0 when sentinel exists, touch sentinel only after `## Plan Candidate for Review` output. Port `test-run-step3-review.sh` preview cases into pytest.
  - From Codex-Generic: Move the existing preview sentinel contract into `plan-review preview --variant step3` or into `design-step3-entry-preview.sh`, and pin the same allowlist/header-only touch behavior in `python/test_plan_review.py`


### FINDING_4: `design-step3-review.sh` env-read failure path still depends on deleted loop script
- **Reviewer(s)**: Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: After `review-design-step3-loop.sh` is deleted, `design-step3-review.sh` still sources it when `.step3-review-result.env` read/parse fails. That fallback fails on the missing script instead of normalizing to `panel-failed`, and there is no clear wrapper-callable seam to preserve escalation evidence on this failure path because handling confined to `run_step3_review` cannot observe wrapper-side read failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the wrapper cutover to remove this source dependency while preserving the current `panel-failed` evidence behavior, either in `python/plan_review.py` or a direct CLI helper
  - From Codex-Generic: Add an explicit wrapper-callable `plan-review record-escalation-evidence` CLI verb, or spell out an import-backed Python invocation from `design-step3-review.sh` on `_rre_rc != 0`




### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-step3-orchestrator-fence.sh:39-125
- **Concern**: Harness still stubs run-step3-review.sh but wrapper will launch plan-review run. Scenario: After cutover design-step3-review.sh invokes python/cli.py plan-review run; the fake-plugin stub never intercepts the real driver, so make test-step3-orchestrator-fence loses its integration contract and may pass while the wrapper regresses
- **Proposed resolution**: Add an explicit UPDATED row for test-step3-orchestrator-fence.sh: stub/observe plan-review run (or a thin fake python/cli.py), refresh argv and grep pins, keep the harness in Makefile shard 11



### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:729-744
- **Concern**: The absorbed loop awaiting-continuation path is not spelled out in plan_review.py run_step3_loop. Scenario: Multi-round auto-continue stops after the first settled round; ballot-items-lost and other continuation reasons never schedule round N+1
- **Proposed resolution**: In run_step3_loop port step3_loop_run_continuation: subprocess plan-review-continuation.sh; on PLAN_REVIEW_CONTINUE=true call plan-review step3-state --auto-continuation-entry rm .step3-entry-plan-printed and increment round



### FINDING_1: Round-meta lifecycle not ported
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan omits `scripts/write-design-round-meta.sh` and its tally-error metadata clear. Absorbed bash paths call it after terminal round snapshot (`plan-review-loop.sh:752-757`), after successful revise (`review-design-step3-loop.sh:478-484`), and on MainAgent retally refresh (`persist-retally-step3-env.sh:223`); they clear `round-meta.json` on `tally-error` (`plan-review-loop.sh:733-739`, `persist-retally-step3-env.sh:204-280`). After cutover, `plan-review/round-N/round-meta.json` and `panel-manifest.ndjson` stay missing or stale, breaking Review Phase Detail rendering and consumers such as `python/progress_report.py`, `render-final-summary.sh`, and per-round revise-tier/count reporting. Test coverage is also underspecified: `test_plan_review.py` only lists vague "Round snapshot shape" rather than the existing `revise.{status,tier}` assertions in `test-plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an injectable subprocess seam in `plan_review.py` (default `scripts/write-design-round-meta.sh`) at the three call sites plus tally-error metadata clear; pin pytest coverage ported from `test-plan-review-loop.sh` revise-field cases.
  - From Cursor-Pragmatic: Keep `write-design-round-meta.sh` as a retained bash helper and call it from the ported loop at the same boundaries: terminal round snapshot (`plan-review-loop.sh:752-758`), post-revise refresh (`review-design-step3-loop.sh:481-483`), and MAV retally ok path (`persist-retally-step3-env.sh:213-224`, including the `voting-tally.md` copy first); add an injectable subprocess seam and pytest asserting `round-meta.json` is created.


### FINDING_2: Prompt-template smoke still invokes retired `dispatch-plan-voters.sh`
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan retires `scripts/dispatch-plan-voters.sh` and deletes `scripts/test-dispatch-plan-voters.sh`, but does not retarget `scripts/test-prompt-template-invariants.sh`, which still runs `"$REPO_ROOT/scripts/dispatch-plan-voters.sh"` for plan-voter prompt smoke (`Makefile` shard 12). After cutover, `make lint` / `make test-harnesses-12` / `test-prompt-template-invariants` fail immediately even when `python/test_plan_review_panel.py` passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Retarget the smoke block to `python3 python/cli.py plan-review voter-dispatch` (or an import-backed helper with the same stubs) and update the `docs/linting.md` row that still names `dispatch-plan-voters.sh`.
  - From Cursor-Requirements: Retarget the plan-voter smoke to python/cli.py plan-review voter-dispatch (or render voter) and update scripts/test-prompt-template-invariants.md; add an explicit UPDATED row in the plan.


### FINDING_4: Plan-review nit pre-filter subprocess not ported
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan lacks an explicit port of the plan-review nit pre-filter subprocess. Without the injectable `prune-nit-findings.sh` call (and `INSCOPE_REMAINING` parse), ballot-items-lost detection and continuation scheduling break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an injectable seam for `LARCH_PLAN_REVIEW_PRUNE_NITS_SH` in `run_plan_review_round`, mirror current fail-open behavior, persist `prune-nit.env`, and port the harness cases from `test-plan-review-loop.sh`.


### FINDING_5: Brainstorm non-binding context artifact omitted from loop port
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits the existing brainstorm non-binding context artifact during the loop port. `/design --brainstorm` currently writes `plan-review-feature-context.txt` from stripped feature text plus `brainstorm.md`; dropping it in the Python cutover regresses the documented Step 3 brainstorm handoff and existing harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Port this materialization into python/plan_review.py and add the matching pytest assertion before deleting the shell loop.


### FINDING_6: Forensic TSV harness still invokes retired `tally-plan-review.sh`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan retires `tally-plan-review.sh` but does not account for the surviving forensic TSV harness. `make lint` still runs `test-findings-classification`, which invokes the deleted `tally-plan-review.sh` path and will fail after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Move that harness coverage into python/test_plan_review.py and remove the Makefile/docs target, or retarget the harness to python3 python/cli.py plan-review tally before deleting the shell script.


