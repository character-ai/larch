# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: awk `-f` scripts are misclassified as inline program text
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The awk lint can still inspect the first file operand after `-f` as though it were program text, which false-positives valid `awk -f filter.awk "$1"` fences and misses the plan’s positional-parameter exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Track whether the awk invocation uses `-f`; when the source is supplied by `-f`, do not inspect subsequent file operands as the program. Add a regression test for `awk -f filter.awk "$1"` returning clean.


### FINDING_2: empty suppression markers should not silence the lint
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: A suppression marker with no reason can still bypass the new lint, which weakens the justification requirement for bootstrap exceptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Parse the text after the marker and require `strip()` to be non-empty before suppressing, otherwise report a lint error for an unjustified suppression.


### FINDING_4: wrapped awk commands need continuation normalization
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: A continued awk command can retain the literal backslash and hide bare field references from the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Strip shell line-continuation backslashes when building `logical`, or otherwise normalize continued shell lines before `shlex.split`, and add a test in `python/tests/lint/test_lint_skill_awk_field_refs.py` for a wrapped `awk -F= \` command.


