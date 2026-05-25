# Review Round 2

- Mode: `diff`
- 11 accepted, 5 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Tally can diverge between parser vote and `vN_vote`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `tally-plan-review.sh` parses ratings through `parse-judge-vote-and-rating.sh` but re-parses votes separately with `vote_for_id`, so forensic `vN_vote` cells can disagree with `PARSED_VOTE` while `voting_result` uses separate vote-count logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Main-agent recovery drops forensic vote columns
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent recovery re-tallies with only `--voter MainAgent`, but MainAgent is not mapped to `v1`-`v3` TSV columns, so adjudicated rounds can show accepted or rejected results with empty forensic vote and rating cells.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: MainAgent can distort quorum if passed with panel voters
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If MainAgent is combined with panel voters, `eligible_count` and `count_votes_for_id` include it even though the TSV has only fixed `v1`-`v3` panel columns, allowing quorum and `voting_result` to diverge from the intended panel semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Zero-judge rows look like final rejections
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Zero-judge TSV rows use `voting_result=rejected` while panel KV reports `main-agent-vote-required`, so downstream consumers may interpret pending adjudication as a final panel rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Loop harness uses vote-only stubs while asserting parse-rate success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `test-plan-review-loop.sh` stubs voter output with vote-only lines even though production parse-rate now requires four rating axes, so the harness can pass with output production dispatch would reject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Render voter prompt tests do not cover all rating-token contexts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-render-voter-prompt.sh` does not assert rating-token instructions across all planned id-grammar and verification-context combinations, leaving room for prompt regressions to pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Parse-rate gate rejects vote-only or partial-axis outputs that tally can still parse
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `is_substantive_vote_for_id` requires a vote plus all four rating axes, while tally/parser behavior still accepts or records vote-only and partial-axis lines. Legacy or partially compliant judges may be retried, marked failed, or dropped instead of producing degraded but useful forensic rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Plan-review publish path lacks robust symlink handling and coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Symlinked `findings-classification.tsv` files under `plan-review/round-N` are excluded or can be swapped between enumeration and staging, and publish may still succeed without staging the expected forensic TSV. Harness coverage does not fully exercise this inner symlink case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Loop harness does not verify populated forensic TSV on happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-plan-review-loop.sh` asserts header-only TSV output for empty paths but not populated `findings-classification.tsv` output in a normal one-finding tally, so broken voter wiring or output wiring could pass loop tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Vote tally helper docs are missing parity updates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New `count_votes_for_id` and `findings_classification_header` helpers are not reflected in `scripts/lib-vote-tally.md`, increasing drift risk for consumers that duplicate vote-count logic or TSV headers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Tally accepts symlinked voter files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-review.sh` accepts voter files with `-r`, which follows symlinks. A planted symlink under `DESIGN_TMPDIR` could cause host file contents to influence published TSV-derived data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


