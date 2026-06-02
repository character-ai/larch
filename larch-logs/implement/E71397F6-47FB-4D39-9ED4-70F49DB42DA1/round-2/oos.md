### FINDING_11: [OUT_OF_SCOPE] Non-Python reviewers also flagged the Python Closes plan gap
- **Reviewer(s)**: dyn-teardown-flow-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt, dyn-bash-portability-output.txt, dyn-harness-wiring-output.txt
- **Severity**: important
- **Concern**: Reviewers focused on other surfaces separately noted that `compose_pr_body` no longer delegates to `tracking_issue.link_pr_closes` and that the current tests encode the split. This duplicates the in-scope Python Closes concern but was explicitly marked outside those reviewers’ scopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-flow-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt, dyn-bash-portability-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] Positive Step 17→18b and harness wiring observations
- **Reviewer(s)**: dyn-teardown-flow-output.txt, dyn-bash-portability-output.txt, dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: Several reviewer notes were confirmations rather than defects: Step 17→18b main wiring aligns, added Bash remains Bash 3.2-compatible, Makefile/shard wiring looks sound, and coverage is not stub-only everywhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-flow-output.txt, dyn-bash-portability-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] Clear-stall exit-code contract needs orchestrator attention
- **Reviewer(s)**: dyn-stall-recovery-output.txt
- **Severity**: latent
- **Concern**: Reviewer noted that `clear-stall` exit 0 with `CLEARED=false` is documented, so orchestrators must parse `CLEARED` rather than exit code alone. This is related context for the symlink/session-only gaps but was tagged out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-recovery-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_4: [OUT_OF_SCOPE] Bash and Python still both own `Closes` composition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-stall-recovery-output.txt
- **Severity**: latent
- **Concern**: Reviewers noted pre-existing cross-surface duplication between Bash `ship-pr.sh` and Python `tracking_issue.link_pr_closes`. This is separate from the Python-only reconciliation work unless Bash parity is added to scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-stall-recovery-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Branch includes unrelated Step 18/stall-recovery/log/version churn
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-teardown-flow-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers flagged that the branch carries non-Python work, Step 18/stall-recovery helpers, larch-log churn, version/docs changes, or run-artifact deletions beyond the narrow Python Closes reconciliation scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-teardown-flow-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt, dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] `ensure_pr` can still accept bodies that bypass compose-time redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` accepts caller-built PR body strings and applies only `link_pr_closes` plus optional update handling. Bodies that never pass through `compose_pr_body`’s fail-closed redaction remain a Phase 7 integration concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Step 18b tmpdir env sourcing follows an existing trust-boundary pattern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.sh` sources `$tmpdir/plugin-root.env` when `CLAUDE_PLUGIN_ROOT` is unset, inheriting the existing session-tmpdir trust-boundary risk. Reviewer marked it pre-existing and not introduced by this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] `update_pr_body` lacks full-body Mermaid sanitization symmetry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `update_pr_body` does not have the same full-body Mermaid sanitization behavior as `compose_pr_body`; reviewer marked this as a pre-existing ensure/update path asymmetry to track separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

