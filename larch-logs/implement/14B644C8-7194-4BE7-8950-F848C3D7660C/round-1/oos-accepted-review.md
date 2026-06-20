### OOS_1: [OUT_OF_SCOPE] plan_review_tally module docstring still claims 22-column classification TSV
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `python/plan_review_tally.py` module docstring still references a 22-column classification TSV while runtime output is 23 columns including `scope`. Misleading for contributors reading the producer contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update docstring to 23 columns.


### OOS_2: [OUT_OF_SCOPE] Plan-listed weighted scoreboard and scope-drift test assertions still missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scoring-integrity-output.txt
- **Severity**: nit
- **Concern**: Plan-listed weighted scoreboard and `scope=oos` assertions (e.g. `[OUT_OF_SCOPE]` on `FINDING_N`, `_scope_drift`, comma vs pipe attribution) were not added beyond header width checks. Regression risk on the highest-traffic tally path is not locked by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add the planned scoreboard and scope assertions from the implementation plan.
  - From dyn-scoring-integrity-output.txt: Several plan-listed `python/test_review_tally.py` weighted-scoreboard / `scope=oos` assertions (e.g. `[OUT_OF_SCOPE]` on `FINDING_N`, `_scope_drift`, comma vs pipe attribution) do not appear in the diff; regression coverage for inline scoreboard weighting is thinner than the plan claims.


### OOS_3: [OUT_OF_SCOPE] Plan-listed progress_report Top reviewers fixtures missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Legacy no-scope TSV and whitespace-separated `finding_reviewers` design fixtures from the plan are missing from `python/test_progress_report.py`. Edge-case regressions in Top reviewers attribution may slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add the planned legacy and whitespace-separated finding_reviewers fixtures.
  - From cursor-specialist-testing-output.txt: Add targeted progress_report integration tests if end-to-end Top reviewers behavior needs stronger pinning.


### OOS_4: [OUT_OF_SCOPE] plan_review_tally module docstring column count drift (maintainer doc only)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/plan_review_tally.py` module docstring still references a 22-column classification TSV. Runtime header is 23 columns including `scope`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update the docstring to 23 columns including scope.
  - From cursor-specialist-testing-output.txt: Update docstring to 23-column schema.


### OOS_5: [OUT_OF_SCOPE] docs/linting.md still references 21-column plan-review schema
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still references a 21-column plan-review schema for `test-findings-classification` while the harness enforces 23 fields at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update column count reference to 23.


