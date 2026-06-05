### FINDING_13: [OUT_OF_SCOPE] State-file containment check may not reject symlink escapes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A symlink under the tmpdir could point outside the intended containment boundary unless real paths are resolved and validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] Counter parsing accepts unbounded large values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Corrupt huge counter values can be accepted as valid nonnegative session counters without sane upper bounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Existing fresh-fallback test conflicts with the fresh-counter contract
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: A test intentionally preserving counters on gh-failure fresh fallback conflicts with the plan line that fresh paths ignore stale counters and seed monitor counters at zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Merge/postbump failure paths may return without terminal ship-state stall writes
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Some merge/postbump failure branches still return without writing a terminal `ship-pr-state.sh` stall state, leaving only partial/finalize state in some paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Manifest-gated done routing may reflect plan ambiguity
- **Reviewer(s)**: dyn-cap-loop-output.txt
- **Severity**: latent
- **Concern**: Existing tests encode manifest-gated done routing, but the plan wording appears stricter for gh-skipped versus GitHub-authoritative paths and should be tracked separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cap-loop-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] `effective_run_id()` state preference itself predates this branch
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: nit
- **Concern**: The helper’s preference for state `RUN_ID` is pre-existing; the new concern is its use in resume routing rather than the helper alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] Bash state-file value validation is also incomplete
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: latent
- **Concern**: Bash validates state-file line syntax but lacks value-level charset checks for fields like `BRANCH_NAME` and `PR_URL`; this was not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_26: [OUT_OF_SCOPE] Static review did not run tests or linters
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: nit
- **Concern**: The reviewer did not execute `make py-test` or `make py-lint`; findings are based on static inspection only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] Plan acceptance and regression test matrix is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: Many plan-required cases lack dedicated tests, including cap-at-49/50 behavior, pass/already-merged at cap, stale GitHub/local state overrides, wrong PR head, blocked rebase re-entry, protected branch refusal, detached HEAD refusal, terminal counter round-trips, OOS-artifact resume behavior, and manifest non-done statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt, dyn-cap-loop-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

