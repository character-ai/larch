### FINDING_1: HEAD non-advance check can be bypassed by refresh-run-log commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` compares HEAD after `refresh-run-logs`, so a vendor run that makes no CI-fix commit can still appear to advance HEAD because log commits were created, allowing success paths or retry loops to continue incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Test contract doc undercounts lint harness cases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-awk-multibyte-regex.md` says the harness has 18 cases, but the shell harness implements 19 and the non-awk heredoc false-positive guard is missing from the documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: docs/linting.md understates lint harness coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The `make test-lint-awk-multibyte-regex` row in `docs/linting.md` omits review-round fixtures and no longer reflects the shipped harness scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: Missing #3134 explanatory comments on modified fix-loop cases
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Some #3134-touched `scripts/test-ship-pr.sh` happy-path fix-loop cases lack the required explanation comment, making future edits more likely to revert important sentinel or launcher behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: open_single_quoted_body advances past only the opening quote
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: In `scripts/lint-awk-multibyte-regex.sh`, `open_single_quoted_body` discards `extract_quoted_value` output and advances `rest` by only one character, so certain multi-`-v` awk invocations can fail to detect the following awk body and skip Rule 2 scanning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_16: Hardcoded assert_negative rc argument is non-obvious
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-awk-multibyte-regex.sh` passes literal `0` to `assert_negative` to skip exit-code checking, but that intent is not obvious and could mislead future editors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

