# Review Round 2

- Mode: `diff`
- 2 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_4: Design remediation harness does not pin invariant retry behavior
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The design remediation harness does not pin invariant marker handling, retry/counter behavior, persistence, or skip-approve blocking for Gate C/outline flows, so those semantics can drift without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add the plan flows and pin gatec/outline remediation counters
  - From codex-specialist-testing: Assert invariant marker handling, retry counters, persistence, bounded remediation, and skip-approve blocking behavior.


### FINDING_5: Implement harness is missing the invariant compose-wrapper fixture
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The architectural-guidelines step harness lacks the invariant-first branch pin and compose-wrapper fixture/metadata contract, so pre-PR invariant violations can bypass the expected CI path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add ci-fix ordering assertions and invariant write-compose fixture
  - From codex-specialist-testing: Add a parallel invariant fixture that writes architectural-invariant-materialize.env, invokes the wrapper, and verifies note plus metadata.


