# Review Round 1

- Mode: `diff`
- 3 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_1: `_classify_path()` broader than retired Bash `classify-diff-mode.sh` globs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-parity-contract-output.txt
- **Severity**: important
- **Concern**: Python path classification for docs, scripts, and test paths is broader than the deleted Bash `case` globs. Nested paths such as `docs/guide/chapter.md` or `pkg/tests/nested/foo_test.py` can classify as `docs-only` or `test-only` where Bash returned `generic`, changing dynamic scout skip and specialist prompt routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Match Bash case globs exactly (single-segment * where Bash used it) and add nested-path parity tests
  - From cursor-specialist-edge-cases-output.txt: Restrict directory test matching to one segment before /tests|/test and one filename segment; add nested-path parity test expecting generic.
  - From dyn-parity-contract-output.txt: Port the Bash `case` patterns literally (single-segment `*` semantics), or add parity tests for nested paths and adjust regexes until they match the old script byte-for-byte.


### FINDING_10: Missing `larch-logs`-only commit-log exclusion regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pytest gather-branch-context coverage dropped the `larch-logs`-only commit-log exclusion case from the deleted Bash harness. `/review` diff mode can include run-log-only commits in `commit-log.txt` while still excluding them from `diff`/`file-list`, breaking scout-skip and operator commit-count semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Restore the old fixture: add a commit touching only larch-logs/** and assert it is absent from commit-log.txt while code commits remain.


### FINDING_3: Poll interval parser rejects Bash-compatible positive decimals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Python `wait-reviewers` poll interval parser rejects positive decimal forms accepted by the retired Bash helper, including leading-dot values like `.5` and `.05` and trailing-dot forms like `1.`. `WAIT_FOR_REVIEWERS_POLL_INTERVAL=.5` (or similar) now makes `agent wait-reviewers` exit `1` before waiting, so collector callers can fail instead of collecting ready reviewer outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Accept leading-dot positive decimals and add a pytest parity case
  - From codex-specialist-correctness-output.txt: Accept Bash-compatible decimal forms, then keep the float(value) > 0 guard to reject zero and malformed values.
  - From cursor-specialist-edge-cases-output.txt: Accept positive decimals with digits on either side of the dot while preserving existing zero and malformed-input rejection.
  - From codex-specialist-testing-output.txt: Allow Bash-compatible positive decimal grammar and add parity tests for .5 and 1.


