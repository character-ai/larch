# Review Round 4

- Mode: `diff`
- 7 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_10: Missing release prepare output contract tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_release.py` lacks plan-required tests for release prepare `LATEST_COUNT` and `pr-list.tsv` header or column order, risking silent breakage for release consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Missing malformed oos-issues.ndjson audit test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_audit_runs.py` does not cover the plan-required malformed `oos-issues.ndjson` error row behavior, so NDJSON parse failures can stop emitting the documented scan error without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: category-stats malformed JSONL behavior diverges from bash
- **Reviewer(s)**: dyn-wire-contract-parity-output.txt
- **Severity**: important
- **Concern**: On malformed `review-findings-full.jsonl`, Python computes category aggregate fields from partially parsed rows and omits the bash-style `detail`, instead of forcing `mangled:0` with a stronger partial-data signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-wire-contract-parity-output.txt: Address the concern above.


### FINDING_3: Codex waste scan lost timing-report fallback
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `codex-generalist-waste` no longer reads `timing-report.json`, so a round-1 Codex run with `NO_ISSUES_FOUND` and over-threshold duration can pass when `wrapper_logs.codex` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: combine-issues leaks raw gh failure output
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `combine_issues.py` prints raw `gh issue create` stdout/stderr on create or parse failures, which can leak tokens or private issue text into stderr, chat, or logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Audit skill docs reference deleted shell helpers
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-wire-contract-parity-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/audit-runs/SKILL.md` still directs operators to deleted audit shell helpers and retired contract docs instead of the Python `audit-runs` CLI verbs and live Python tests or contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-wire-contract-parity-output.txt: Address the concern above.


### FINDING_9: Missing pacific-timestamp tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_audit_runs.py` lacks plan-required coverage for `pacific_timestamp_main`, so timestamp format, `PACIFIC_TIMESTAMP_SOURCE`, UTC fallback, and unknown argv behavior can regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


