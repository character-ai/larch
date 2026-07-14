### FINDING_3: [OUT_OF_SCOPE] Report validation does not enforce prevention-field requirements
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-proposal-contract
- **Severity**: major
- **Concern**: `validate_report_contract` checks headline placement and prose markers but does not mechanically validate Host, Size budget, Cheaper alternative, or the 150/400-line conditional requirements before publication or filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Exact threshold boundaries are not pinned
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The structure harness does not pin exclusive 150- and 400-line boundary behavior, allowing a future edit to change `>` semantics to `>=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Proposal JSONL lacks prevention metadata
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Published proposal JSONL does not carry prevention metadata, so marker publication cannot verify Host or size claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Architectural guideline lacks the independent-estimate rule
- **Reviewer(s)**: dyn-dyn-proposal-contract
- **Severity**: minor
- **Concern**: `G-Prevent-1` does not state that threshold triggers must use an independently computed estimate, so future deduplication may not recognize the stronger anti-self-disarm rule as existing guideline coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Filing-mode enforcement remains prose-only
- **Reviewer(s)**: dyn-dyn-proposal-contract
- **Severity**: minor
- **Concern**: Filing-mode completeness is enforced by orchestrator prose without a Python filing-body validator, so enforcement depends on agent judgment unless a mechanical backstop is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Structure checks cannot detect empty or dishonest field values
- **Reviewer(s)**: dyn-dyn-proposal-contract
- **Severity**: minor
- **Concern**: Substring-based structure pins cannot detect semantically empty Host values, blank Size budgets, or dishonest under-reporting; this limitation remains in the existing harness design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-contract: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
