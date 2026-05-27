### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: duplicated vendor rc routing blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The duplicated `vendor_rc` case blocks at the two vendor call sites can drift. A future routing fix for rc `2` or `4` could be applied to only one branch, selectively regressing the `gh_logs_rc!=0` or normal path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: vendor head-changed test depends on shared counter coupling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_head_changed` depends on a shared lint-fix counter across per-job and verify passes. If the per-job path stops calling the lint-fix loop, the test may no longer prove vendor verify head-changed routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: max-iteration clamp test bypasses env call-site path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `rcc_max_iter_invalid_env_clamp` tests `_RCC_MAX_ITER` directly instead of exercising `LARCH_CI_LOCAL_FIX_ITER` through the same assignment path used by per-job and verify flows. Invalid env handling at real call sites could regress while the direct harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: gh-logs-failed rc=2 test mocks the wrong layer
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_rc2_on_gh_logs_failed_branch` stubs `run_ci_fix_vendor` instead of forcing real verify head-changed behavior. The `gh-run-logs` failed branch could route rc `2` correctly in the mock while real verify never returns rc `2` there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

