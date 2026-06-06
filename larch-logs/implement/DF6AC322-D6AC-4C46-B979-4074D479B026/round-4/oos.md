### FINDING_10: [OUT_OF_SCOPE] Breadcrumb fd 4 write failures can drop messages silently
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: latent
- **Concern**: `BreadcrumbWriter.emit()` marks breadcrumbs routed even when fd 4 write fails, preventing stderr fallback when quiet routing is miswired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-routing-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] Pre-existing broad output allow already covered unphased dynamic Codex output
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: The prior broad `*-output-*.txt` allow already included unphased `dyn-*-codex-output.txt`; the gap was documentation/regression coverage rather than a live exclusion bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] Phased dynamic Codex fixtures may be forward-looking
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: Current dispatch wiring appears to emit unphased dynamic Codex basenames, so phased fixtures/docs may be forward-looking unless another producer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_13: [OUT_OF_SCOPE] No concrete finalize-state quoting incompatibility found
- **Reviewer(s)**: dyn-state-kv-output.txt
- **Severity**: nit
- **Concern**: Python/bash finalize-state quoting changes appeared internally consistent for normal keys; no concrete incompatibility was identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-kv-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] Dynamic Codex catch-all also violates the plan from ship-cutover review
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: The ship-cutover reviewer independently flagged the same `dyn-*-codex-output-*.txt` catch-all as outside that review’s scope but contrary to the attached plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] Finalize-state merged writer uses sorted key order
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: nit
- **Concern**: `write_finalize_state_merged()` emits sorted keys instead of the canonical finalize-state key ordering, creating multiple on-disk shapes for the same contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Pre-existing broad sidecar globs can include vote-prompt-shaped sidecars
- **Reviewer(s)**: dyn-artifact-globs-output.txt
- **Severity**: latent
- **Concern**: Existing broad sidecar allows may retain `.meta`/`.json` siblings for vote-prompt-shaped basenames because the `*-vote-prompt.txt` deny only covers the `.txt` basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-globs-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] Existing open PRs keep their current base
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: latent
- **Concern**: `python/pr.py` reuses the base of an existing open PR and does not correct a previously mis-based PR; reviewer notes this matches bash behavior and was not introduced by the current change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_22: [OUT_OF_SCOPE] Python OOS/resume re-entry restarts full driver
- **Reviewer(s)**: dyn-pr-base-output.txt
- **Severity**: latent
- **Concern**: Python ship resume re-invocations restart from checks rather than resuming from persisted `PHASE`, causing extra latency and possible duplicate side effects if phases are not idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-base-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Branch mixes unrelated dynamic-log and Python ship changes
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch combines dynamic Codex log contract work with unrelated Python ship/finalize/test changes, increasing review burden and making CI failures harder to attribute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Python ship cutover security review remains pending
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The documented Phase 7 security review for the Python ship path has not been completed, leaving possible trust-boundary gaps outside the larch-log artifact-policy scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] `shell_unquote_simple` handles only single-quoted state values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/refresh-run-logs.sh` may parse double-quoted or complex escaped finalize-state values incorrectly if such values are introduced later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

