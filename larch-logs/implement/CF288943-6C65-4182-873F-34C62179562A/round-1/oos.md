### FINDING_2: [OUT_OF_SCOPE] Avoid duplicate parametrization loading
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_case_parameters()` is invoked twice during parametrization, unnecessarily doubling fixture loading and parsing at collection time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
