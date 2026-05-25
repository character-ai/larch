# Review Round 3

- Mode: `diff`
- 6 accepted, 9 rejected (7 exonerated)

## Accepted Findings

### FINDING_10: Parser exit and empty-ID cases lack direct tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `parse-judge-vote-and-rating.sh` lacks direct tests for unreadable files and missing ID lines, so failures can be masked by callers that tolerate parser errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Main-agent vote instructions omit rating-axis tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent adjudication instructions do not require the same rating-axis tokens as panel judges, so main-agent re-tally can populate votes while leaving rating columns empty and uncertainty inferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Plan-review loop does not reconcile classification TSV after tally failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` handles tally errors without normalizing the classification TSV state, so stub and real tally failures can leave different artifacts that diverge from `voting-tally.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: MainAgent fallback populates v1 forensic columns
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When panel slots are empty, the MainAgent voter file is mapped into `v1`, conflicting with the stated convention that MainAgent is not mapped to any `vN` column and confusing `v1=Claude` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: lib-vote-tally docs omit main-agent-vote-required
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `classify_result` documentation and tests do not fully lock the new `main-agent-vote-required` outcome for zero-eligible rows, risking downstream callers or regressions that still assume `rejected`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Plan text still describes zero-judge rows as rejected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The issue plan or acceptance text still expects `rejected` for zero-judge rows while the code emits `main-agent-vote-required`, causing downstream filters, analytics, or harness expectations to disagree with landed semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


