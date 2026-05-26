### FINDING_3: Breadcrumb monitor test docs omit required test mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-breadcrumb-monitor.md` documents `LARCH_BM_TEST_TIMEOUT_SECONDS` without also documenting the required `LARCH_BM_TEST_MODE=1`, so contributors following that doc alone get the production timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



