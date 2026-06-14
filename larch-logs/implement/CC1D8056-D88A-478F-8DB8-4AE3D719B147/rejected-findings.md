### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Validation-mode JSON `no_issues_found` preamble short-circuit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Validation-mode JSON `no_issues_found` short-circuit requires the trimmed body to start with `{`; there is no full-body retry after preamble lines. A short review with a preamble line before `{"no_issues_found": true}` fails the thin-body gate or needs filler words instead of exiting 0 like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After first-line checks, retry `_json_no_issues` on full trimmed text when any line starts with `{`; add preamble+JSON pytest.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Makefile lint shards run full `test_research.py` including budget sleep tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Five lint targets all run full `python/test_research.py` with no pytest filter, so budget sleep tests run on every shard instead of only the budget harness. Shard 16/17/18 etc. each pay ~1s+ real-sleep budget tests that used to live only in `test-validate-citations-budget.sh`; shard balance regresses and failures are harder to localize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Give each Makefile harness a focused `pytest -k` selection; keep one full-file run under `py-test`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_15: No negative test for eval harness exit 1 on schema validation failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/research_eval.py:610-611`: no negative test for eval harness exit 1 when eval-set or baseline schema validation fails. `validate_eval_set`/`validate_baseline_json` gate could break while smoke still passes on committed good fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add corrupt eval-set/baseline fixtures and assert eval research exits 1.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: Structured JSONL repair silently skips invalid lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Structured JSONL repair silently skips invalid lines and passes if any record normalizes. Truncated JSONL with one good row and a broken tail passes structured mode and under-reports findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed on unrecoverable JSONL lines or partial repair; match legacy strictness.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

