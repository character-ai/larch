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


### FINDING_8: vendor local exhausts test is helper-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `vendor_verify_local_exhausts` calls `_verify_failed_jobs_locally` directly rather than running vendor and then verify through the full waterfall. `run_ci_fix_vendor` could skip verification after a winning tier, or pass the wrong TSV/plumbing, while this test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


