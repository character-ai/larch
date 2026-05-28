### FINDING_1: HEAD non-advance check can be bypassed by refresh-run-log commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` compares HEAD after `refresh-run-logs`, so a vendor run that makes no CI-fix commit can still appear to advance HEAD because log commits were created, allowing success paths or retry loops to continue incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Rule 2 misses multibyte regex content split across awk body lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.sh` only detects Rule 2 when non-ASCII text and a regex token appear on the same line, so multibyte regex values assigned on one awk body line and consumed by `match()` or similar on another can escape linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Rule 2 skips double-quoted awk program bodies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-awk-multibyte-regex.sh` does not treat double-quoted awk program strings as awk body spans, so forms like `awk "BEGIN { match($0, \"—\") }"` can avoid Rule 2 detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Generic heredoc mode creates a full blind spot for embedded awk
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Generic heredoc handling in `scripts/lint-awk-multibyte-regex.sh` skips all body-line scanning, so embedded awk invocations or `awk -v` content inside non-awk heredocs are invisible to Rule 1 and Rule 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Default ship-pr test launcher now commits in too many scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-ship-pr.sh` changed default `write_stubs` launchers to auto-commit on every `make_repo`, which may affect unlisted test cases that assumed a no-commit launcher and could alter check counts, stall behavior, or exit paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Inner-loop fix tests may have stale assumptions after launcher commit behavior changed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Inner-loop fix cases in `scripts/test-ship-pr.sh` still use the default launcher, so launcher pre-commits before `_stage_and_push` may desync expected `run-relevant-checks` invocation counts from documented exhaustion behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Dynamic POSIX character classes are not covered by lint
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The lint does not detect POSIX `[[:class:]]` usage in dynamic awk regex construction, so an ASCII-only dynamic class regression tied to the original mawk hypothesis could still pass commit-time linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Test shard growth may pressure CI wall time
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The enlarged `test-harnesses-5` and `test-ship-pr-fix-loop` coverage may approach timeout under CI load if shard wall time regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Breadcrumb wording does not match HEAD-based bail logic
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` reports “no commits” even when `refresh-run-logs` may have advanced HEAD, making operator-facing breadcrumbs disagree with the actual HEAD-based logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Noop vendor can still consume retries when unrelated commits advance HEAD
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` can loop through vendor cycles without a CI fix when HEAD advances for unrelated reasons, because retry accounting is not limited to actual `Fix CI failure` commits.
- **Suggested revisions (informational for voters; coder decides)**:
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

### FINDING_15: Inconsistent heredoc indentation in vendor_verify_empty_tsv launcher stub
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In `scripts/test-ship-pr.sh`, one `printf 'X\n' >> sentinel-fix.txt` line in the `vendor_verify_empty_tsv` launcher stub has four leading spaces while surrounding heredoc stub commands use zero indentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_16: Hardcoded assert_negative rc argument is non-obvious
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-awk-multibyte-regex.sh` passes literal `0` to `assert_negative` to skip exit-code checking, but that intent is not obvious and could mislead future editors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
