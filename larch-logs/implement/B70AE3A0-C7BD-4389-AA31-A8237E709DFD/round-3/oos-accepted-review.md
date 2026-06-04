### FINDING_11: [OUT_OF_SCOPE] URL recovery rejects GitHub Enterprise hosts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: `_repo_matches_pr_url` requires a `github.com` URL shape, so successful PR creation on GitHub Enterprise hosts can fail recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-create-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_13: [OUT_OF_SCOPE] Step 8 prose still references bash state routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Post-invoke text still references `ship-pr-state.sh` for all implementations, which can mislead Python-path orchestration that should rely on JSON-only routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Direct `ship.py` invocation lacks a version guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Scripts or operators invoking `ship.py` directly can bypass the `/implement` Python 3.11 guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_25: [OUT_OF_SCOPE] Python ship path does not initialize quiet routing like bash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Python ship path does not call `larch_quiet_init`, so quiet/progress routing can differ from `ship-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_27: [OUT_OF_SCOPE] Volatile classifier implementation matches the plan
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the volatile classifier and cleanup posture correctly match the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_28: [OUT_OF_SCOPE] ndjson-only substantive delta coverage is absent
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: Tests cover canonical `token-report.json` commits but not an ndjson-only substantive delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_29: [OUT_OF_SCOPE] Scrubbed volatile sidecar cleanup is intentional
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that scrubbed refresh sidecars are intentionally restored/cleaned instead of committed and have test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_32: [OUT_OF_SCOPE] Missing stdout-invalid/stderr-real URL recovery test
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover the case where stdout contains a regex-matching but invalid PR URL while stderr contains the real PR URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_33: [OUT_OF_SCOPE] Recorded gh fixture is not live CLI coverage
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: nit
- **Concern**: The recorded acceptance gate catches flag reintroduction but not live `gh` CLI drift in unrecorded fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_34: [OUT_OF_SCOPE] Closed-PR noop check is duplicated
- **Reviewer(s)**: dyn-merge-race-output.txt
- **Severity**: nit
- **Concern**: `_merge_noop_if_pr_closed` is invoked twice back-to-back before merge logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-race-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_35: [OUT_OF_SCOPE] Force-push recovery test misses changed-head scenario
- **Reviewer(s)**: dyn-merge-race-output.txt
- **Severity**: latent
- **Concern**: Existing merge recovery tests do not exercise the case where the PR head OID changes from the pre-recovery snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-race-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_37: [OUT_OF_SCOPE] Stdout JSON contract appears sound
- **Reviewer(s)**: dyn-stdio-quiet-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that `emit_result` remains the sole stdout printer and tests assert single-line JSON stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdio-quiet-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_38: [OUT_OF_SCOPE] Python floor was propagated across many core surfaces
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the 3.11 floor is correctly reflected across core Python config, CI matrices, implement skill guard, and report-token wrapper surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_39: [OUT_OF_SCOPE] Runtime already implicitly required Python 3.11
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that existing runtime imports already required Python 3.11, so the documented floor aligns with latent import reality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_40: [OUT_OF_SCOPE] `run-analysis.sh` version probe lacks a structural pin
- **Reviewer(s)**: dyn-py311-floor-output.txt
- **Severity**: latent
- **Concern**: There is no structural grep equivalent pinning the `run-analysis.sh` Python version probe, so future edits could remove it unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-floor-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_5: [OUT_OF_SCOPE] Duplicate CI breadcrumbs are noisy
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: nit
- **Concern**: Both `ship.py` and `ci_monitor.py` emit CI poll breadcrumbs, creating redundant progress lines during long waits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


