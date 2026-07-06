# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: scripts/lint-bash32.sh boundary misses shell operators
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The new left-boundary check does not catch `if` or `elif` after `&&`, `||`, `|`, or `&`, so an unsafe `command grep` probe can still evade the rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Broaden the left boundary to shell separators or use token-aware parsing while still excluding the subshell form.


### FINDING_5: scripts/test-lint-bare-grep-probe.sh fixture strings trigger the new rule
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The new bash32 grep-family rule matches intentional fixture strings in `scripts/test-lint-bare-grep-probe.sh`, so `make lint-bash32` would fail on existing test data in a residual-bash-paths file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add lint-bash32 suppressions to those fixture lines or narrow the rule to ignore quoted fixture payloads.


