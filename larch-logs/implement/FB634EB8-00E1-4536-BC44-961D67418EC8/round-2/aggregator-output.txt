### FINDING_1: Finalize bash parity coverage is still mostly mock-based
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` has too few real bash subprocess comparisons, leaving high-value finalize decisions such as postbump checkpoints, force-push outcomes, teardown rename, and cleanup paths vulnerable to bash/Python drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt: Address the concern above.

### FINDING_2: CI-fix rebase and pending-retry behavior lacks unit coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: `python/test_ci_monitor.py` does not cover the new `stage_and_push`, defer-rebase, force-push-with-lease, and `CI_FIX_REBASE_PENDING` retry behavior, so regressions in CI-fix push selection and monitor propagation could ship green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_3: Unknown legacy `.postbump-phase` tokens are treated as corrupt
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` returns `postbump-state-corrupt` for valid lowercase legacy checkpoint tokens that bash clears and continues from; the current test also appears to encode that regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt, dyn-bash-parity-output.txt: Address the concern above.

### FINDING_4: `_rebase_no_push` duplicates rebase helper logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` duplicates fetch/ancestor/rebase/abort behavior instead of delegating to shared `rebase.py`, risking divergent semantics as rebase helpers evolve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Finalize unit tests omit plan-listed branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks coverage for multiple finalize branches, including postbump force-push outcomes, verify suffix behavior, teardown rename/guard cases, and larch-only reset paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Ship-layer postmerge/postbump integration tests are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` does not sufficiently cover postmerge flush/sentinel gating, skipped `pr_closed=false` behavior, failed postmerge phase persistence, and postbump layering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Postmerge log finalization alias is not consistently used
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `finalize_postmerge_logs` is effectively a passthrough while callers such as `merge.py` still call `flush_logs_post`, weakening the intended centralized postmerge finalization contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Recovery failure skip behavior is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not prove callers stop side effects when manifest recovery returns `recovery_ok=false`, so report or manifest writes could proceed after recovery failure unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Finalize parity gate checks source text instead of pytest collection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity_gate.py` can stay green even if parity tests are broadly skipped or not collected when bash is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: `_local_cleanup` accepts an unused `ctx`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The unused `ctx` parameter in `_local_cleanup` misleads readers about cleanup dependencies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: Postbump preflight has dead or misleading branch fallback logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `postbump_preflight` contains a branch fallback that is effectively dead after successful `rev-parse`, adding noise and possibly obscuring detached-HEAD semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Branch includes unrelated design/timing/doc changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The diff includes unrelated design, timing, docs, or harness changes beyond finalize parity scope, making the PR harder to audit and increasing regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] CI-fix pending documentation/comments are stale or missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: Comments, docstrings, or README notes still describe old `CI_FIX_REBASE_PENDING` behavior or omit the new lifecycle, which can mislead maintainers and operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_14: Merge bash parity can silently skip when bash exists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_merge_bash_parity.py` can skip when `merge-pr.sh` is missing and lacks a fail-closed gate comparable to finalize parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Trimmed postmerge skip test name overstates bash parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test_postmerge_skip_decisions_match_trimmed_bash` does not invoke bash despite its name, creating misleading CI/review signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Ship state writer lacks newline rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` writes context-sourced fields without the newline guard used by finalize state writing, so untrusted GitHub metadata could corrupt one-line-per-KV state files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Local cleanup can destructively hard-reset default branch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_local_cleanup` can run `git reset --hard origin/main` when flush-only heuristics match, reflecting pre-existing bash behavior but posing operational risk for Python cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Bash branch deletion is less strict than Python
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/local-cleanup.sh` deletes branches without `check-ref-format` or `--`; this is pre-existing and not a regression from the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Orphan reset can hard-reset on empty log/diff evidence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The orphan reset heuristic uses vacuous `all()` on empty subject/path lists when `ahead>0`, so malformed empty git output could trigger an unsafe hard reset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Postmerge reports are rendered before done manifest is written
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` / `finalize_postmerge_logs` render final reports and batches before writing `status=done` / `pr_number`, unlike bash, allowing a merged summary to exist without a coherent done manifest after partial failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-workflow-resume-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_21: Design MAV timing row is emitted before main-agent adjudication
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: Multi-round `main-agent-vote-required` exits can emit a timing row with panel-exit timing and stale tallies instead of deferring emission until after inline re-tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### FINDING_22: Timing report attaches rounds by start time only
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` attaches round rows when only `round_start` is inside the parent step interval, even though the contract requires both round start and end to be contained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### FINDING_23: Implement round timing idempotency cannot supersede stale rows
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: Implement timing rows are idempotent by round number only, unlike design’s superseding behavior, so any premature implement row could not be corrected on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Timing report silently collapses duplicate round rows
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: `emit_round_array` keeps the last duplicate `(skill, step, round)` row without warning, which can hide warn-only double-writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Timing report awk globals are undeclared
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: `match_idx` and `round_match_pos` are undeclared awk globals, making `scripts/timing-report.sh` fragile if the function grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### FINDING_26: Python clears `CI_FIX_REBASE_PENDING` on HEAD mismatch unlike bash
- **Reviewer(s)**: dyn-workflow-resume-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` clears pending CI-fix rebase state when `CI_FIX_REBASE_PENDING_HEAD` is absent or mismatched, while bash persists only the boolean and retries push-only, causing resume divergence across bash/Python boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-resume-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_27: Pending CI-fix push retries skip post-rebase verification
- **Reviewer(s)**: dyn-bash-parity-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: On `CI_FIX_REBASE_PENDING` push-only retries, Python skips verification gates that bash runs for pending retries before force-push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_28: CI defer-rebase path uses bare rebase instead of bash wrapper semantics
- **Reviewer(s)**: dyn-bash-parity-output.txt, dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: Python’s defer-rebase path uses raw fetch/rebase/abort behavior rather than bash’s `run_rebase_rebump` / `rebase-push.sh --no-push` semantics, including keep-on-conflict, transient retry, and handoff behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt, dyn-ci-rebase-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Remote branch state lacks transient retry
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_remote_branch_state()` calls `git ls-remote` without the transient retry behavior bash uses, so flaky network failures may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] CI monitor parity coverage gaps remain
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: The plan’s CI-fix tests for defer-rebase, pending retry, and `FixResult` propagation were not added, leaving parity gaps unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Finalize subprocess parity coverage remains too thin
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Only one real subprocess parity case exists for finalize, leaving postbump, cleanup, teardown, and checkpoint behavior without side-by-side bash assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_32: Teardown log recovery uses stale `ctx.run_id` instead of effective state run id
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `_teardown_log_flush` gates and writes safety-net records using `ctx.run_id` while manifest recovery uses `effective_run_id(ctx)`, so state-file `RUN_ID` can be skipped or logged under the wrong run directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_33: Post-merge sentinel is written too late
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Python writes the post-merge sentinel only after `finalize.postmerge` returns OK, whereas bash writes it immediately after terminal merge success; a postmerge stall can therefore leave teardown commit guards unblocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_34: Absent run directory recovery synthesizes incomplete manifest
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Python recovery writes a bare partial manifest when the run directory is absent instead of using bash-equivalent init semantics, omitting schema/init fields validators expect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_35: `pr_number` is incorrectly stored inside `steps_ran`
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Postmerge finalization stores `pr_number` as a `steps_ran` entry, violating the bash manifest contract that `steps_ran.*` values are booleans and `pr_number` is top-level.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Teardown default-branch gate only checks main/master
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: Teardown’s pre-commit branch gate does not honor non-`main` default branches via `origin/HEAD`, unlike `larch-log.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_37: `CI_FIX_REBASE_PENDING` is persisted without bash’s verify-passed gate
- **Reviewer(s)**: dyn-ci-rebase-output.txt
- **Severity**: important
- **Concern**: Python sets pending retry state whenever rebase/pending exists and push fails, including cases where verification did not run or failed, whereas bash persists pending only after verification passes and force-push fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-output.txt: Address the concern above.
