### FINDING_1: [OUT_OF_SCOPE] Bash-less hosts fail finalize parity tests instead of skipping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` lacks a module-level bash-absence `skipif`, so bash-less CI/agent hosts can error or fail collection instead of skipping, while the gate can pass vacuously.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Ship-layer preflight failure omits bash auxiliary finalize KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-design-resume-output.txt
- **Severity**: nit
- **Concern**: Ship-synthesized `FinalizeResult` for postbump preflight failure lacks auxiliary fields such as skipped log/rebase/force-push statuses that `finalize.postbump()` itself emits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-design-resume-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: [OUT_OF_SCOPE] Fail-closed finalize parity gate pins exact pytest pass count
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity_gate.py` hard-codes the human pytest summary, especially `"7 passed"`, so adding or renaming parity tests can break CI despite green parity behavior; the gate should assert successful execution, nonzero collection, and zero skips without exact cardinality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-shell-portability-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Merge bash parity lacks a fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_merge_bash_parity.py` can all-skip with green tests if skip configuration regresses because there is no merge-specific fail-closed gate analogous to finalize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] Non-rebase CI fix path lacks explicit plain-push assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: CI monitor tests do not explicitly assert that a non-rebase CI fix uses plain `git push` and leaves `did_rebase=False`, making an accidental always-force-push regression harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] Orphan flush reset is destructive but within existing trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The new `git reset --hard origin/main` path is intentionally destructive and matches bash; reviewer framed this as bounded by existing `/implement` trust assumptions rather than a new external security vulnerability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] Finalize parity subprocess tests are not isolated like merge parity tests
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: Finalize bash subprocess tests invoke real scripts without fully pinning `cwd` and stubbing `git`/`gh`, so bash may inspect the pytest working tree while Python uses faked runner state, producing false parity failures or misses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-portability-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Design timing and skill diffs are bundled with finalize parity work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch includes substantial design-skill and timing-ledger changes outside the finalize parity plan, increasing integration/review risk for a PR marketed as finalize parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] `merge_pr(post_flush=True)` can fail an already-merged noop on recovery skip
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: `merge.py` maps post-flush skips such as manifest recovery failure to merge error, unlike ship’s warning-only path; production ship currently passes `post_flush=False`, making this latent for direct callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-runlog-recovery-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Finalize bash subprocess parity coverage is too thin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` only subprocess-compares a small subset of planned finalize paths, and one monkeypatch-only postbump test can be mistaken for bash parity. Postmerge cleanup, verify-main, postbump force-push, checkpoint corruption, teardown rename, and related status-token branches can drift from `implement-finalize.sh` while tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] Python `goto_rebase` still does not match bash pre-push conflict handoff
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: latent
- **Concern**: The Python ship driver still resolves conflicts inline instead of emitting bash’s documented pre-push resume handoff; reviewer notes this predates the finalize parity work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_35: [OUT_OF_SCOPE] `CI_FIX_REBASE_PENDING_HEAD` is persisted but not hydrated
- **Reviewer(s)**: dyn-git-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Ship state writes `CI_FIX_REBASE_PENDING_HEAD`, but `RunContext.from_env` does not read it, so head-mismatch invalidation metadata is inert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-lifecycle-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] Postmerge helper does not handle late execution-issues rendering
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: nit
- **Concern**: `finalize_postmerge_logs` is a one-line alias and does not separately render execution issues; reviewer notes bash postmerge also only does manifest/final report, leaving late execution-issues parity dependent on teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_42: [OUT_OF_SCOPE] Python README documents stale CI-fix pending limitations
- **Reviewer(s)**: dyn-design-resume-output.txt
- **Severity**: nit
- **Concern**: `python/README.md` still says Phase 6 omits `CI_FIX_REBASE_PENDING`, but this branch adds related hydration, ship-state, and monitor retry plumbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-resume-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] Timing ledger always exits zero
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: `scripts/timing-ledger.sh` has pre-existing `main "$@" || true` and unconditional `exit 0`; new callers compensate by verifying ledger content afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_45: [OUT_OF_SCOPE] Timing report harness still requires pre-existing `jq` dependency
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: New round-attachment cases in `scripts/test-timing-report.sh` continue to require `jq`, but that dependency already existed in the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

