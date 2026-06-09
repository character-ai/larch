# Review Round 5

- Mode: `diff`
- 3 accepted, 11 rejected (5 neutral)

## Accepted Findings

### FINDING_16: Deleted write-design-env harness cases lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-write-design-current-env.sh` cases for legacy symlink warning, partial codex override with binary clear, and malicious prior export recovery were not ported, leaving write-design-env refresh/preservation regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Missing XDG cache/session-root acceptance test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test proves `write-env` accepts output under an `XDG_CACHE_HOME` session root while `write-design-env` still places its symlink under `Path.home()/.cache`, leaving path-predicate regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: /design prompt prose still names retired bash helpers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Runtime `/design` SKILL prose still references deleted bash helper scripts in Step 0a and the already-planned/brainstorm branch, so an agent or operator following the prose can invoke removed scripts instead of the session CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


