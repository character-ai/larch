### FINDING_17: [OUT_OF_SCOPE] General ledger appends can fail closed under flock contention
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing flock fail-closed behavior can drop unrelated ledger rows under contention, not just deferred round timing rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Publish and pause timing render helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: Publish and pause paths have near-duplicate timing render helpers. Fixes to cleanup, validation, stale sidecars, or env hygiene can diverge, and pause-path failure/quarantine coverage is weaker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-publish-artifacts-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] mav-resume-past-cap resume envelope reports ROUNDS_COMPLETED=0
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: nit
- **Concern**: Entry-time `mav-resume-past-cap` sets `ROUNDS_COMPLETED=0` even when resuming after real rounds, causing telemetry-only skew.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] No additional deferred-handoff gaps identified
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: nit
- **Concern**: Reviewer reported no other pre-existing deferred-handoff gaps beyond the in-scope handoff findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Pre-publish timing render failure can still allow committed logs without timing JSON
- **Reviewer(s)**: dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: If pre-publish timing render or validation fails, publish can still proceed without staging `timing-report-final.json`; post-publish summary may later render fresh timing only in tmpdir, leaving committed logs permanently missing per-round timing. Related test coverage does not fully assert the warning/no-artifact path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-artifacts-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] render-final-summary timing rerender can diverge from published artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-artifacts-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` still performs its own timing rerender after publish, with different temp/stderr behavior and potential mismatch from already-published timing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-artifacts-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Pause/resume timing test uses weak/non-canonical fixture validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pause/resume timing tests use a non-canonical design step label and do not validate rendered round content strongly enough, so wrong labels or empty renders could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

