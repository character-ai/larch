# Review Round 5

- Mode: `diff`
- 3 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_14: Missing no-claims citation sidecar test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/research.py:539-542`: missing no-claims sidecar test required by the plan and old harness Test 1. Readable synthesis with zero URL/DOI/file-line claims could stop writing the `_No citable provenance` sidecar without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a prose-only report test asserting sidecar body and `SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0`.


### FINDING_16: Duplicate eval id rejection lacks failing fixture test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/research_eval.py:364-366`: duplicate eval id rejection is implemented but not covered by a failing fixture test. Duplicate `### eval-id` entries could be reintroduced without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal eval-set with duplicate ids; assert `validate_eval_set` false or smoke exit 1.


### FINDING_17: Planner CLI `missing_arg` exit 2 path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_research.py:49-58`: planner CLI `missing_arg` exit 2 path is not tested though required by the plan exit-code matrix. Omitted `--raw` or `--output` could map to wrong exit code and break orchestrator routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add CLI cases without required flags asserting exit 2 and `REASON=missing_arg`.


