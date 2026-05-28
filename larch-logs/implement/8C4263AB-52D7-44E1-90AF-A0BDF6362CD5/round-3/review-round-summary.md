# Review Round 3

- Mode: `diff`
- 4 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Indented canonical contains lines are silently skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `parse_contains` uses a fixed `substr(text,9)` offset even though the matcher permits leading whitespace, so indented canonical `contains "$VAR" ...` assertions can be ignored without failing or warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Pin targets can escape repository root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Resolved pin targets are not confined under `REPO_ROOT`, so changed test scripts can add out-of-tree probes and make CI reveal whether host-readable files contain chosen substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: Double-quoted backtick pins are skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The pin verifier skips static double-quoted literals containing backticks, including several `test-design-structure.sh` pins, so local `relevant-checks` can pass while CI later catches drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Missing fixture for single-quoted Markdown-backtick pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The verifier harness lacks a fixture matching the exact single-quoted Markdown-backtick pin shape, so regressions on that real pattern may not fail `make test-check-contains-pins`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


