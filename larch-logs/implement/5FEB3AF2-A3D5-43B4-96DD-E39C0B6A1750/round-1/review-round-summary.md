# Review Round 1

- Mode: `diff`
- 6 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: Launcher short-output whitelist diverges from validator
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The degraded-response whitelist in `launch-review.sh` uses weaker substring and shape checks than the validator. This can both degrade validator-accepted compact outputs such as pretty-printed JSON or inline TSV, and incorrectly accept prose that merely mentions `"no_issues_found": true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Bash 3.2 collector contract doc omits Case 5b
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-collect-agent-bash32.md` omits Case 5b from the documented harness catalog, hiding always-on degraded sentinel coverage from maintainers using the contract doc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Security docs still describe Cursor review as plan mode
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Security and operator docs still describe legacy Cursor plan-mode behavior and omit the active `--mode ask`, dual read-only mode notes, `CURSOR_DEGRADED_RESPONSE`, and collector sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: NS-retry success paths can promote sentinel outputs to OK
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results.sh` assigns `STATUS=OK` on NS-retry success paths without re-running `_classify_sentinel_status`, so a retry output beginning with `CURSOR_DEGRADED_RESPONSE` can be promoted to OK on paths that otherwise classify sentinels as non-OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Waterfall integration tests do not exercise high-token degraded Cursor output
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The waterfall Cursor stub hardcodes `outputTokens=1`, so integration tests never exercise the degraded-response heuristic for high-token narration-only Cursor output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Validator test case does not assert required STATUS line
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-validate-research-output.sh` Case 19h checks exit code 5 but not the required `STATUS=CURSOR_EMPTY_RESPONSE` stdout contract, so CI could miss a broken status emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


