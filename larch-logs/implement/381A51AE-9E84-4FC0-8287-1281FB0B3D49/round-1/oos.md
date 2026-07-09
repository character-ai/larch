### FINDING_1: risk-integration: python/tests/state/test_bootstrap.py:1185-1286
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No resume-path regression test for skipping progress activate. Plan edge case requires resume behavior unchanged; activation is branch-gated in bootstrap.py but only the fresh-setup path is tested, so a misplaced call would not fail CI. Add `test_phase_infra_resume_skips_progress_activate` with `resume_plan_tail=True` and pre-seeded session env; assert no progress activate call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] risk-integration: Makefile:858-865
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: New bootstrap progress tests omitted from harness `-k` filters. Local `make test-implement-bootstrap` runs would skip the new tests even though `make py-test` covers them. Extend harness `-k` filters to include `phase_infra_progress` when maintaining those targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

