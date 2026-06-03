### FINDING_11: [OUT_OF_SCOPE] Test runner helpers are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `RecordingRunner` is copied across many test modules, increasing harness duplication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] `RunContext` has duplicate alias fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `RunContext` aliases like `branch`/`branch_name` and `forked`/`forked_target` can drift if updates set only one side.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] Python redaction lacks internal-URL handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` lacks repository-wide internal URL scrubbing for outbound session-derived text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_30: [OUT_OF_SCOPE] Driver test coverage gap noted as non-runtime
- **Reviewer(s)**: dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: Additional reviewers also observed `python/test_ship.py` lacks broad driver/goto-rebase/cap/transient coverage, while marking it out of scope relative to their runtime focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt, dyn-ci-rebase-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_31: [OUT_OF_SCOPE] Postmerge unexpected-verification behavior matches bash
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: nit
- **Concern**: `postmerge` returning `OK` on unexpected main verification is a pre-existing/bash-matching behavior, not a Python-only regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_36: [OUT_OF_SCOPE] Bash postbump state validation uses legacy fields
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: latent
- **Concern**: Bash postbump state validation still references legacy `BUMP_TYPE` / `NEW_VERSION` fields, a pre-existing cross-path consistency risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_38: [OUT_OF_SCOPE] Run-log post-flush ordering test is absent
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: nit
- **Concern**: The plan-requested `flush_logs_post` call-order regression test is missing, but this reviewer marked it out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_39: [OUT_OF_SCOPE] Commit-failed skip behavior is consistent for Phase 7
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: nit
- **Concern**: `REFRESH_SKIP_COMMIT_FAILED` being non-fatal matches the current ship-driver Phase 7 path, despite older review expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_42: [OUT_OF_SCOPE] CI fixer push mode diverges after rebase
- **Reviewer(s)**: dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: `stage_and_push` uses normal `git push` where bash uses force-push after rebase or `CI_FIX_REBASE_PENDING`; reviewer marked this as pre-existing but amplified by Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_43: [OUT_OF_SCOPE] CI-fix parity divergences predate cutover docs
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: latent
- **Concern**: Prior Python CI-fix divergences remain behaviorally relevant once the Python ship path is enabled, but are not introduced solely by the cutover docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_47: [OUT_OF_SCOPE] Legacy exit constants are unused but confusing
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: `EXIT_BAIL` / `EXIT_STALL` remain near the correct outcome map and could mislead future callers, though this was marked out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_48: [OUT_OF_SCOPE] Default bash selection remains intact
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: Documentation preserves the default `bash` path and optional `python` strangler-fig selection; no repo script flips the default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_49: [OUT_OF_SCOPE] Positive Python state fallback work landed
- **Reviewer(s)**: dyn-cutover-docs-output.txt
- **Severity**: nit
- **Concern**: `write-final-report.sh` and `oos-disposition-checkpoint.sh` gained `finalize-state.sh` fallbacks, and `SECURITY.md` documents the Python stdout/finalize-state boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-docs-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_53: [OUT_OF_SCOPE] `test-merge-pr` linting doc row is stale
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: The existing `test-merge-pr` docs still mention removed same-version race-gate machinery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_54: [OUT_OF_SCOPE] Shard-balance comment says `ship-pr` was removed
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: A Makefile shard-balance comment says `test-ship-pr` was removed entirely in favor of Python, while `scripts/ship-pr.sh` remains the default bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


