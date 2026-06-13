# Review Round 3

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_12: Tier B dry-run lacks no-gh-call assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan requires Tier B dry-run to make no `gh` calls, but only Tier A dry-run asserts that. If dry-run checks move after resolver or helper calls, consumer dry-run could start using network or `gh` without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Tier B helper create-failure fallback is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The stall-recovery harness does not cover the plan-required Tier B helper create-failure fallback. If cross-repo `gh issue create` fails, `compose-report` should fall back to `chat-print`; an integration bug could drop the artifact or emit the wrong status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Tier A dedup marker is not tested through issue parse-input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness does not verify that the Tier A HTML signature marker survives `/larch:issue parse-input`. If parse-input strips the marker, filed Tier A issue bodies lose dedup identity and later dev-clone stalls can create duplicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


