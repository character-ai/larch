### OOS_1: [OUT_OF_SCOPE] Missing harness coverage for annotate-skipped-empty-stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-contract-ordering-output.txt, dyn-sentinel-count-fidelity-output.txt
- **Severity**: important
- **Concern**: The new empty/missing stdout graceful-skip path lacks direct `test-file-design-oos.sh` coverage. Regressions to non-graceful exits, silent skips, or missing status/WARN output may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-contract-ordering-output.txt, dyn-sentinel-count-fidelity-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Prepare idempotency ignores sentinel-only prior filing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-contract-ordering-output.txt
- **Severity**: important
- **Concern**: `prepare` keys idempotency on `oos-issues-created.md`, not `oos-issue-sentinel`. If annotate was skipped after `/issue` succeeded, a later `/design` can re-invoke `/issue` and duplicate OOS issues because the durable created-file/cache artifacts were never materialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-contract-ordering-output.txt: Address the concern above.


