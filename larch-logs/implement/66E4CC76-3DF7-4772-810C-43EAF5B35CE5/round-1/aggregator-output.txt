### FINDING_1: [OUT_OF_SCOPE] vendor verify ignores non-fixable TSV rows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_verify_failed_jobs_locally` diverges from `run_per_job_local_fix_loop` by skipping non-fixable TSV rows. Mixed fixable and unfixable failures can let vendor verification pass the fixable jobs, push, and then fail CI again on unfixable jobs. The duplicated loop structure makes this drift easier to preserve or reintroduce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: duplicated vendor rc routing blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The duplicated `vendor_rc` case blocks at the two vendor call sites can drift. A future routing fix for rc `2` or `4` could be applied to only one branch, selectively regressing the `gh_logs_rc!=0` or normal path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: vendor sweep regression test is helper-only and misses outer retry behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `vendor_verify_sweep_regression` exercises `_verify_failed_jobs_locally` in isolation rather than the full `ship-pr.sh` vendor path. Regressions in `run_ci_fix_vendor`, rc `4` routing, push suppression, or `per_job_verification_retry` outer retry behavior could pass the helper test while breaking the integrated flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: missing ci-merge vendor head-changed coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_head_changed` covers the `ci-initial` `10-head-changed` path but not the `ci-merge` `12-head-changed` path. Vendor verification during merge-phase CI could stall with the wrong step token without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: local fix iteration limit lacks robust bounds
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_CI_LOCAL_FIX_ITER` / `_RCC_MAX_ITER` lacks robust normalization and upper bounds. Huge numeric values can trigger excessive local check and external-agent iterations, while values like `00` can normalize to zero attempts and skip the inner fix loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: vendor head-changed test depends on shared counter coupling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_head_changed` depends on a shared lint-fix counter across per-job and verify passes. If the per-job path stops calling the lint-fix loop, the test may no longer prove vendor verify head-changed routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: max-iteration clamp test bypasses env call-site path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `rcc_max_iter_invalid_env_clamp` tests `_RCC_MAX_ITER` directly instead of exercising `LARCH_CI_LOCAL_FIX_ITER` through the same assignment path used by per-job and verify flows. Invalid env handling at real call sites could regress while the direct harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: vendor local exhausts test is helper-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `vendor_verify_local_exhausts` calls `_verify_failed_jobs_locally` directly rather than running vendor and then verify through the full waterfall. `run_ci_fix_vendor` could skip verification after a winning tier, or pass the wrong TSV/plumbing, while this test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: gh-logs-failed rc=2 test mocks the wrong layer
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_rc2_on_gh_logs_failed_branch` stubs `run_ci_fix_vendor` instead of forcing real verify head-changed behavior. The `gh-run-logs` failed branch could route rc `2` correctly in the mock while real verify never returns rc `2` there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
