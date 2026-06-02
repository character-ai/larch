### OOS_1: [OUT_OF_SCOPE] `needs_user_bail_reason` vs autonomous bail helper naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-exhaustion-predicate-output.txt
- **Severity**: nit
- **Concern**: `needs_user_bail_reason` includes autonomous tokens excluded by `is_autonomous_exit3_bail_reason` (e.g. `ci-fix-exhausted` listed at `scripts/ship-pr.sh:1720–1722` vs narrower handling at 1728–1731). Confusing for new readers; pre-existing, not introduced by this diff. Orchestrator behavior depends on the narrower helper plus `BAIL_NEEDS_USER_INPUT=false` at exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-exhaustion-predicate-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Pre-existing stall-recovery / structure test gaps for `ci-fix-exhausted`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/stall-recovery-report.sh:251` allowlists `first-fixer-non-health` but not `ci-fix-exhausted`; `scripts/test-implement-structure.sh:233-247` structural awk still only requires `first-fixer-non-health` in the Exit 3 block (weaker than dedicated step8 test).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-routing-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Branch bundles unrelated commits beyond #3334
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch contains commits unrelated to #3334 (#3314, #3297, #3338, etc.). Unrelated harness failures could block merge while reviewing ship-pr changes only. Consider isolating the #3334 commit or running full relevant-checks / harness splits before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Codex Step 2 grant narrowing (#3314)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-codex-implement.sh` grant narrowed with symlink and IMPLEMENT_TMPDIR-root rejection; reduces risk of Codex writing orchestrator-owned session artifacts; unrelated to #3334 but present on the branch. No action required for #3334.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Missing per-job exhaustion test as regression gap for push-failed predicate
- **Reviewer(s)**: dyn-exhaustion-predicate-output.txt
- **Severity**: latent
- **Concern**: Plan-listed `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` is absent; the push-failed `code_fix_attempted_on_ready_log` gap has no targeted regression in `python/test_ci_monitor.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exhaustion-predicate-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] Planned test absence would have caught ordering drift
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Plan-listed `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` is not in `python/test_ci_monitor.py`; only `test_evaluate_failure_exhausted_routes_needs_user_input` (~774) with winning tier via `launcher_exit=0`. That gap would have caught per-job-before-vendor ordering drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Pre-existing Bash per-job-before-vendor vs Python vendor-first structure
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Bash runs `run_per_job_local_fix_loop` before `run_ci_fix_vendor`; Python runs vendor waterfall inside `run_ci_fix` before the per-job loop. Predicate text claims a single contract but entry points differ structurally across trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Verified — Python `fix-exhausted` does not fall through to stall in `monitor()`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `python/ci_monitor.py:1083-1084` returns `fix-exhausted` / `ci-fix-exhausted`; `monitor()` handles it at 1211-1218 with `Outcome.NEEDS_USER_INPUT` before generic STALLED at 1225-1228. No routing defect.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Verified — Bash autonomous exit 3 wiring for `ci-fix-exhausted`
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `is_autonomous_exit3_bail_reason` includes `ci-fix-exhausted`; terminal exhaustion sets `BAIL_NEEDS_USER_INPUT=false`; `bail` handler skips needs-user when autonomous reason matches. No routing defect.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Verified — implement SKILL groups both autonomous exit-3 tokens
- **Reviewer(s)**: dyn-exit-routing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md:1169,1182` groups `first-fixer-non-health` and `ci-fix-exhausted` in the autonomous When clause; `scripts/test-implement-step8-exit3-first-fixer.sh:19-20` greps both strings.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

