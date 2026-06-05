### FINDING_1: Finalize bash parity tests never invoke bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` is named and positioned as bash parity coverage but only exercises Python finalize code with mocks. It does not subprocess-invoke `scripts/implement-finalize.sh` or compare bash `STATUS`/KV output to `FinalizeResult`, so Python/bash finalize drift can pass CI until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_13: Stall teardown writes `stalled_at_step` in wrong manifest location
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Stall teardown writes `stalled_at_step` into `steps_ran` instead of the top-level manifest field used by bash `larch-log.sh manifest --field`, so downstream readers see `manifest.json.stalled_at_step` as null under Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_16: Branch deletion lacks `--` separator and ref validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_local_cleanup` deletes the feature branch with `git branch -D` without `--`. A branch name beginning with `-` from session state can be parsed as an option, causing wrong behavior or failure around a destructive operation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_18: Writable CI pending state can authorize force-push without revalidation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `CI_FIX_REBASE_PENDING` is honored from writable ship state and can trigger a lease force-push without re-running behind-main/rebase validation or checking an expected HEAD OID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_19: CI-fix rebase failure can fall through to plain push
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-git-safety-output.txt
- **Severity**: important
- **Concern**: `stage_and_push` can continue after a failed defer-rebase, leaving an in-progress/conflicted rebase and then attempting a normal `git push` instead of aborting/stalling cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-git-safety-output.txt: Address the concern above.


### FINDING_20: CI-fix defer-rebase lacks bash failed-jobs guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-git-safety-output.txt
- **Severity**: important
- **Concern**: Python triggers defer-rebase whenever behind-main is detected, without bash’s guard that failed-jobs TSV/classification must be known. It can rebase and force-push in situations bash deliberately skips.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-git-safety-output.txt: Address the concern above.


### FINDING_21: CI-fix post-rebase verify and pre-push refresh gates are missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-git-safety-output.txt, dyn-state-resume-output.txt
- **Severity**: important
- **Concern**: After a CI-fix rebase, Python goes directly toward force-push and can arm pending without bash-equivalent post-rebase verification, optional delta commit, failed-jobs checks, or pre-push run-log refresh. This can push or retry unverified rebased fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-git-safety-output.txt: Address the concern above.
  - From dyn-state-resume-output.txt: Address the concern above.


### FINDING_22: Postbump error exits omit auxiliary bash KV fields
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Postbump transient/`ShipError` paths omit auxiliary KVs such as `rebase_status`, `force_push_status`, and `log_write_status=skipped`, diverging from bash output expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: Final manifest write OSError is not converted to `RefreshSkip`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `flush_logs_post` can raise uncaught `OSError` on final manifest write, causing ship postmerge to crash instead of returning a structured `RefreshSkip` reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_27: CI pending retry state is not carried or consumed like bash
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-state-resume-output.txt
- **Severity**: important
- **Concern**: `evaluate_failure` and `ship.py` do not implement bash’s push-only `CI_FIX_REBASE_PENDING` retry lifecycle. Pending is not reliably threaded across loop iterations or terminal returns, force-push failure can stall the monitor immediately, and hydrated pending retries can be skipped or overwritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-state-resume-output.txt: Address the concern above.


### FINDING_3: Plan-listed finalize unit branches lack coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-listed finalize tests for postbump gates, checkpoint corrupt handling, local cleanup reset/partial paths, verify suffixes, teardown commit gates, and rename/branch paths are largely absent, leaving new finalize branches without regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_30: `_rebase_no_push` may abort unrelated rebase after fetch failure
- **Reviewer(s)**: dyn-git-safety-output.txt
- **Severity**: important
- **Concern**: `_rebase_no_push` calls `git rebase --abort` when fetch fails, even though no rebase was started by that function. If another operation left the repo mid-rebase, postbump can abort unrelated state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-safety-output.txt: Address the concern above.


### FINDING_33: Pre-rebase run-log recovery failure stalls where bash continues
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: In the CI-loop pre-rebase path, `flush_logs_pre` returning `manifest-recovery-failed` is treated as a stall because the reason is not merge-ok, while bash runs refresh with `|| true` and continues into rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_34: Postmerge flush gate ignores state-file `RUN_ID`
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `_postmerge_should_flush` gates on `ctx.run_id`, but `flush_logs_post` resolves the effective run ID from the state file. A caller with `RUN_ID=` only in `SHIP_PR_STATE_FILE` can skip postmerge finalization even though bash would flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_35: Design round timing writer can leak into implement ledger
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: `record-plan-review-round-timing.sh` invokes `timing-ledger.sh` without unsetting stale `IMPLEMENT_TMPDIR`. If `LARCH_TIMING_LEDGER` validation fails, the design round row can be written to an implement ledger instead of the design ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


### FINDING_36: Design MAV-deferred plan-review timing lacks mandatory fence
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: Deferred plan-review round timing after `main-agent-vote-required` is only specified in prose. If the orchestrator halts, pauses, or skips the prose step, no round row is recorded before pause/publish rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


### FINDING_37: Implement Step 5 lint-fix stall can drop deferred timing row
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: On `lint-fix-main-agent-required`, `review-implement-step5-loop.sh` persists round start and exits stall without emitting the timing row, relying on unpinned prose rather than a mandatory Bash fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


### FINDING_42: Ship state rewrite can drop bash/orchestrator resume keys
- **Reviewer(s)**: dyn-state-resume-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` rewrites the state file from a fixed key list instead of updating keys in place. Persisting CI-loop state can drop keys such as stall/bail/no-logs/failed-run metadata that bash expects for resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-resume-output.txt: Address the concern above.

### FINDING_5: Plan-listed ship postmerge/postbump tests lack coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Ship integration tests for `pr_closed`-gated postmerge flush/sentinel behavior, postbump layering, and CI pending state are missing or incomplete, so incorrect flushing or `phase=done` writes may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_7: Merge post-flush recovery failure propagation lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `merge_pr` post-flush handling lacks a regression test for `manifest-recovery-failed` skips propagating to `MERGE_RESULT_ERROR`, so production merge post-flush errors could stop surfacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_8: Postbump checkpoint parsing diverges from bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python postbump checkpoint handling uses a different size limit and validation behavior than `implement-finalize.sh`. Checkpoints bash treats as corrupt or legacy-clear can be accepted or rejected differently in Python, changing stall/continue behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_9: Local cleanup pull lacks bash retry and ahead diagnostic
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_local_cleanup` runs pull without bash-equivalent transient retry and does not emit the ahead-by-N diagnostic on pull failure. Transient failures or ahead-main states can become partial cleanup without the operator guidance bash provides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


