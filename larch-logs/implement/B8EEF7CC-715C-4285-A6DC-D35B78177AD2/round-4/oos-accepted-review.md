### FINDING_17: [OUT_OF_SCOPE] legacy exit-code aliases remain beside Outcome map
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `python/config.py` still defines legacy `EXIT_BAIL` / `EXIT_STALL` constants alongside `OUTCOME_EXIT_MAP`, creating maintainability risk but not a current runtime regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_21: [OUT_OF_SCOPE] test_ship coverage gaps beyond proven defects
- **Reviewer(s)**: dyn-bash-parity-output.txt, dyn-ci-handback-output.txt
- **Severity**: latent
- **Concern**: Additional `test_ship.py` coverage gaps remain for transient retry semantics, CI rebase conflict handoff, post-merge ordering, SKILL dual-path orchestration, and CI-fix JSON handbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt, dyn-ci-handback-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] stale refresh skip constant remains
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: nit
- **Concern**: `REFRESH_SKIP_STATE_FILE_MISSING` remains in `REFRESH_SKIP_MERGE_OK` even though the state-file-less path no longer emits that skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_31: [OUT_OF_SCOPE] finalize tests miss failure-mode coverage
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: latent
- **Concern**: Finalize tests do not cover partial postmerge, cleanup guard refusal, stash/sentinel failure modes, or teardown log flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_32: [OUT_OF_SCOPE] postmerge flush uses pre-postmerge context
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: latent
- **Concern**: `_postmerge_should_flush()` uses pre-postmerge `ctx`, so flush can proceed after failed postmerge based on earlier merge state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


