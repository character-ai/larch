### FINDING_1: [OUT_OF_SCOPE] Bash-less hosts fail finalize parity tests instead of skipping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` lacks a module-level bash-absence `skipif`, so bash-less CI/agent hosts can error or fail collection instead of skipping, while the gate can pass vacuously.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Fail-closed finalize parity gate pins exact pytest pass count
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity_gate.py` hard-codes the human pytest summary, especially `"7 passed"`, so adding or renaming parity tests can break CI despite green parity behavior; the gate should assert successful execution, nonzero collection, and zero skips without exact cardinality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-shell-portability-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Finalize bash subprocess parity coverage is too thin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` only subprocess-compares a small subset of planned finalize paths, and one monkeypatch-only postbump test can be mistaken for bash parity. Postmerge cleanup, verify-main, postbump force-push, checkpoint corruption, teardown rename, and related status-token branches can drift from `implement-finalize.sh` while tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.

### FINDING_4: Duplicate no-push rebase/fetch logic in finalize instead of shared rebase helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` duplicates rebase/fetch behavior instead of reusing `python/rebase.py`, so future retry/abort/parity fixes must be maintained in two places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `stage_and_push` has grown into a multi-responsibility function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ci_monitor.py`’s `stage_and_push` mixes commit, defer-rebase, verification, and force-push responsibilities, making CI-fix regressions harder to reason about and unit-test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Redundant postbump preflight runs in ship and finalize
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/ship.py` and `finalize.postbump()` both perform postbump preflight, causing redundant branch/rev-parse checks on every ship run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Postmerge log finalization is not centralized across callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-design-resume-output.txt
- **Severity**: important
- **Concern**: `finalize_postmerge_logs()` is effectively an alias while `merge.py` can still call `flush_logs_post()` directly, so recovery/manifest/report ordering and skip semantics can diverge between ship and merge postmerge paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-design-resume-output.txt: Address the concern above.

### FINDING_8: Teardown commit failure is incorrectly folded into `recovery_ok`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_teardown_log_flush` marks `recovery_ok` false on larch-log commit failure even though bash parity treats commit outcome separately and teardown currently ignores the return value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Postbump preflight accepts detached HEAD by substituting target branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-git-lifecycle-output.txt
- **Severity**: important
- **Concern**: `postbump_preflight` treats failed/empty `git symbolic-ref` as the expected branch, so detached HEAD can proceed to rebase/force-push instead of failing closed with bash’s `branch-mismatch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-git-lifecycle-output.txt: Address the concern above.

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

### FINDING_15: [OUT_OF_SCOPE] Ship-layer preflight failure omits bash auxiliary finalize KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-design-resume-output.txt
- **Severity**: nit
- **Concern**: Ship-synthesized `FinalizeResult` for postbump preflight failure lacks auxiliary fields such as skipped log/rebase/force-push statuses that `finalize.postbump()` itself emits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-design-resume-output.txt: Address the concern above.

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

### FINDING_19: New timing harnesses may overload Makefile shard 16
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Three timing harnesses were added to `test-harnesses-16`, potentially creating shard wall-time or flake regressions that block unrelated finalize parity CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Merge bash parity lacks a fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_merge_bash_parity.py` can all-skip with green tests if skip configuration regresses because there is no merge-specific fail-closed gate analogous to finalize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Non-rebase CI fix path lacks explicit plain-push assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: CI monitor tests do not explicitly assert that a non-rebase CI fix uses plain `git push` and leaves `did_rebase=False`, making an accidental always-force-push regression harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Orphan flush reset is destructive but within existing trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The new `git reset --hard origin/main` path is intentionally destructive and matches bash; reviewer framed this as bounded by existing `/implement` trust assumptions rather than a new external security vulnerability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Finalize parity subprocess tests are not isolated like merge parity tests
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: Finalize bash subprocess tests invoke real scripts without fully pinning `cwd` and stubbing `git`/`gh`, so bash may inspect the pytest working tree while Python uses faked runner state, producing false parity failures or misses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-portability-output.txt: Address the concern above.

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

### FINDING_27: Postbump exception results use coarse `STATUS=rebase-failed`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `postbump` maps transient and needs-user-input exceptions to `FinalizeResult.status="rebase-failed"` even when `Outcome` is more specific, so status-only consumers can misclassify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Design timing and skill diffs are bundled with finalize parity work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch includes substantial design-skill and timing-ledger changes outside the finalize parity plan, increasing integration/review risk for a PR marketed as finalize parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] `merge_pr(post_flush=True)` can fail an already-merged noop on recovery skip
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: `merge.py` maps post-flush skips such as manifest recovery failure to merge error, unlike ship’s warning-only path; production ship currently passes `post_flush=False`, making this latent for direct callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.

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

### FINDING_34: [OUT_OF_SCOPE] Python `goto_rebase` still does not match bash pre-push conflict handoff
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: latent
- **Concern**: The Python ship driver still resolves conflicts inline instead of emitting bash’s documented pre-push resume handoff; reviewer notes this predates the finalize parity work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] `CI_FIX_REBASE_PENDING_HEAD` is persisted but not hydrated
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Ship state writes `CI_FIX_REBASE_PENDING_HEAD`, but `RunContext.from_env` does not read it, so head-mismatch invalidation metadata is inert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.

### FINDING_36: Teardown execution-issues safety net is fail-open on render/redaction errors
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: Compose/redaction errors in the teardown execution-issues safety net can skip manifest recovery and `commit_larch_logs`, whereas bash warns and continues best-effort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Postmerge helper does not handle late execution-issues rendering
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: nit
- **Concern**: `finalize_postmerge_logs` is a one-line alias and does not separately render execution issues; reviewer notes bash postmerge also only does manifest/final report, leaving late execution-issues parity dependent on teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### FINDING_38: Design resume defaults invalid classification to HARD and can skip SIMPLE repair
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: important
- **Concern**: Missing or invalid `design_classification` in readable `run-params.json` defaults to `HARD`, so a paused/retried SIMPLE run with stale or corrupt params can bypass SIMPLE sentinel repair and launch the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.

### FINDING_39: Pause and terminal design timing-report rendering are duplicated
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` and `design-publish.sh` each implement their own fresh timing-report renderer, so validation, staging, cleanup, and warning behavior can drift between pause snapshots and final publish.
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

### FINDING_42: [OUT_OF_SCOPE] Python README documents stale CI-fix pending limitations
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: nit
- **Concern**: `python/README.md` still says Phase 6 omits `CI_FIX_REBASE_PENDING`, but this branch adds related hydration, ship-state, and monitor retry plumbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.

### FINDING_43: Implement review round timing idempotency probe ignores timestamp tuple
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `record-implement-review-round-timing.sh` exits success when any row exists for `(skill, step, round)`, unlike its post-write verification and design sibling, so a deferred emit can be silently skipped if an earlier partial/different row exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] Timing ledger always exits zero
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: `scripts/timing-ledger.sh` has pre-existing `main "$@" || true` and unconditional `exit 0`; new callers compensate by verifying ledger content afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] Timing report harness still requires pre-existing `jq` dependency
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: New round-attachment cases in `scripts/test-timing-report.sh` continue to require `jq`, but that dependency already existed in the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.
