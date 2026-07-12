# Review Round 1

- Mode: `diff`
- 9 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Detector fields are not type-validated
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Malformed detector fields such as `message=None` or non-string symbols can raise `TypeError` instead of producing exit 2 with a diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Git path records are rewritten or accept malformed content
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Git-discovered paths are stripped or rewritten, potentially collapsing valid whitespace-containing filenames, while malformed records such as embedded NULs can escape the ScanError contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Internal traversal in requested paths is accepted
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Requested paths containing `..` components are resolved and scanned instead of being rejected with exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Source loading lacks use-time trusted-path validation
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-lint-engine-contracts
- **Severity**: major
- **Concern**: A discovered tracked file can be replaced before reading, allowing an outside-repository symlink or non-regular file to be read without ScanError; regression coverage is also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-lint-engine-contracts: Address the concern above.


### FINDING_7: Source read failures lack OSError coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests cover UTF-8 failures but not `OSError` from source reads, leaving the exit-2, empty-stdout behavior unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Finding rule-ID mismatch validation lacks coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no test ensuring a detector-emitted finding with the wrong `rule_id` is rejected with exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Rule configuration edge cases lack coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Multiline rule IDs or suppression tokens and invalid qualified symbols are not covered by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Syntax-error line normalization lacks coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Tests do not pin fallback to line 1 for zero, negative, absent, or out-of-range syntax-error line numbers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Tokenizer indentation failures escape as uncaught errors
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Tokenizer failures such as `IndentationError` are not converted to ScanError and can violate the documented exit contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
