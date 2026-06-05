### FINDING_10: Teardown recovery failures can skip bash best-effort larch-log commit and warning breadcrumbs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `_teardown_log_flush` can return early on manifest recovery exceptions and lacks bash-style warning/audit breadcrumbs, so teardown may skip the best-effort larch-log commit and hide recovery or commit failures from operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_11: Larch-log commit guards do not centrally enforce default-branch and sentinel refusal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Teardown checks only literal `main`/`master`, and `_larch_log_commit` lacks bash’s centralized default-branch/postmerge-sentinel hard stops, so run-log commits can occur on branches bash would refuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_12: Non-OK postmerge finalize leaves ship phase inconsistent with bash resume semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `run_ship`/`run_postmerge_phase` do not align terminal phase persistence with bash when postmerge finalization is non-OK after merge completion, leaving state at an earlier phase or stalled instead of consistently recording the terminal phase semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_13: `flush_logs_post` can write `status=done` before report/batch rendering succeeds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` persists terminal manifest fields before final report, ledger, token, or timing artifacts are fully rendered; later failure can leave a `done` manifest with stale or missing summary artifacts while callers treat the skip as warning-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_14: CI-fix post-rebase verification and pending-state semantics diverge from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: After defer-rebase or `CI_FIX_REBASE_PENDING`, Python can skip bash-required post-rebase verify/lint gates and set or preserve pending state without the same `verify_passed` requirement, allowing unsafe force-push or retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-parity-output.txt: Address the concern above.


### FINDING_16: Planned finalize unit branches are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks planned unit coverage for postbump force-push, remote checks, protected branch, verify-main suffix/mismatch, orphan reset, teardown rename, and larch-log guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: Planned ship integration branches are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` lacks planned coverage for postbump preflight, terminal phase failure, postmerge `phase=done` gating, partial-cleanup flush, sentinel writes, and skipped log-write status paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Postmerge log recovery failure lacks fail-closed test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not assert that `flush_logs_post`/`finalize_postmerge_logs` skip manifest/report writes when `recovery_ok=false`, so future refactors could write `done` despite recovery failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_24: Stall teardown can downgrade an existing `done` manifest to `partial`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Python stall teardown writes `status=partial` along with `stalled_at_step`, while bash only adds stall metadata; an existing `done` manifest can therefore be downgraded during teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_25: CI-fix rebase force-push failure can clear durable pending state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-git-lifecycle-output.txt
- **Severity**: latent
- **Concern**: When remote lease OID resolution fails after CI-fix rebase, `stage_and_push` returns `pending=False`, clearing `CI_FIX_REBASE_PENDING` even though bash preserves a push-only retry after verified force-push failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-git-lifecycle-output.txt: Address the concern above.


### FINDING_26: Orphan flush-reset has an intentional but undocumented bash parity gap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Python requires non-empty `git log` subject evidence before orphan flush reset, while bash’s empty-loop semantics may reset even with empty/malformed log output; the safer Python behavior is encoded by tests but not clearly documented as a parity deviation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_30: CI defer-rebase behind count uses stale remote-tracking refs
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python counts `HEAD..origin/main` before fetching, while bash’s `ci-behind-count.sh` fetches first, so stale refs can make Python skip or perform defer-rebase incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_31: CI-fix defer-rebase conflict handling leaves the tree in a bad state
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: important
- **Concern**: On nonzero `rebase-push.sh --no-push --keep-on-conflict`, Python returns without aborting rebase or invoking bash’s conflict-resolution handoff, so later CI iterations can run against conflicted or detached state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.


### FINDING_32: Remote branch probe lacks bash transient retry
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `_remote_branch_state` calls `git ls-remote` once, while bash wraps the probe in transient retry; network/auth flakes can become false `remote-check-failed` stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.


### FINDING_33: Postbump force-push can use weaker lease when tracking ref is missing
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: important
- **Concern**: After confirming remote branch presence, postbump only reads `origin/<branch>` for `expected_remote_oid` and does not fall back to `ls-remote`, so first-time or stale-tracking-ref runs can force-push with a weaker lease than bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.


### FINDING_36: Teardown execution-issues safety net is fail-open on render/redaction errors
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Compose/redaction errors in the teardown execution-issues safety net can skip manifest recovery and `commit_larch_logs`, whereas bash warns and continues best-effort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.


### FINDING_38: Design resume defaults invalid classification to HARD and can skip SIMPLE repair
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: important
- **Concern**: Missing or invalid `design_classification` in readable `run-params.json` defaults to `HARD`, so a paused/retried SIMPLE run with stale or corrupt params can bypass SIMPLE sentinel repair and launch the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.


### FINDING_40: Cancel route final-summary emission has split ownership
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: latent
- **Concern**: Cancel routes render `final-summary.md`, the Step 0b bash fence also `cat`s it, and orchestrator prose separately instructs read-and-emit, making double or missing summary emission depend on which layer is treated as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.


### FINDING_41: SIMPLE and HARD-degraded design paths use indistinguishable sentinel artifacts
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: important
- **Concern**: SIMPLE fast-path and HARD “both tools down” write identical sentinel bytes, so pause/resume routing depends on potentially stale tier metadata and completion markers rather than artifact shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.


### FINDING_43: Implement review round timing idempotency probe ignores timestamp tuple
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `record-implement-review-round-timing.sh` exits success when any row exists for `(skill, step, round)`, unlike its post-write verification and design sibling, so a deferred emit can be silently skipped if an earlier partial/different row exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.


### FINDING_9: Postbump preflight accepts detached HEAD by substituting target branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-git-lifecycle-output.txt
- **Severity**: important
- **Concern**: `postbump_preflight` treats failed/empty `git symbolic-ref` as the expected branch, so detached HEAD can proceed to rebase/force-push instead of failing closed with bash’s `branch-mismatch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-git-lifecycle-output.txt: Address the concern above.


