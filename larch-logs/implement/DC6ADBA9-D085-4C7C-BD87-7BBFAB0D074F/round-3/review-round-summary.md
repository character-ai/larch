# Review Round 3

- Mode: `diff`
- 11 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: promote validation exits with the wrong status
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `promote_main` returns `_err(...) + 1` for invalid `--repo` or semver, so validation failures exit 2 instead of the legacy exit 1 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: analyze-issues skill links deleted script contracts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-completeness-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/analyze-issues/SKILL.md` still says logic lives in `scripts/` and points at deleted contract docs instead of the Python modules and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-completeness-output.txt: Address the concern above.


### FINDING_13: map-runs can use stale local fallback after PR body fetch failure
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `map-runs` falls back to local manifest matching even when `gh pr view` fails for the PR body, allowing stale local runs to be mapped after auth or network failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: prior cumulative counters parse prose outside frontmatter
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prior cumulative counters are parsed from the whole prior report body instead of only YAML frontmatter, so prose, examples, or tables can contaminate future totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: release finish origin-vs-repo guard lacks pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `release finish` origin/repo mismatch guard is implemented but untested, so regressions could allow tags or releases against the wrong remote without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: resolve-prs stdout order and error behavior lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `resolve-prs` six-key stdout order and unknown-argv stderr-only exit 1 are not asserted, risking breakage for positional parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: release skill script index still points at deleted helpers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-cutover-completeness-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/SKILL.md` still lists deleted release `.sh` helpers, retired contract docs, and old harness paths instead of the live `python/cli.py release *` verbs and pytest coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-cutover-completeness-output.txt: Address the concern above.


### FINDING_25: promote-latest loses jq parity for null or missing booleans
- **Reviewer(s)**: dyn-wire-contract-output.txt
- **Severity**: important
- **Concern**: `promote-latest` coerces missing or null `isPrerelease` and `isLatest` fields to `"false"`, while the retired jq path emitted an empty string. This can incorrectly take the already-latest early exit and change emitted KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-wire-contract-output.txt: Address the concern above.


### FINDING_4: close-priors upfront failure reasons drift from the documented tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-wire-contract-output.txt
- **Severity**: important
- **Concern**: `close-priors` no longer preserves fixed stdout `REASON=` tokens for upfront failures. `gh issue list` failures can emit stderr text instead of `gh issue list failed`, and temp/body setup failures can emit an `OSError` instead of `mktemp failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-wire-contract-output.txt: Address the concern above.


### FINDING_7: mangled category stats lost jq catstr parity
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_mangled_rows` only counts non-canonical categories when `category` is a string. Numeric or boolean categories no longer count as `oos-category-mangle`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: combinable filter misses locked titles without whitespace
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The migrated combine filter excludes `[LOCKED]` only when whitespace follows the prefix. Titles like `[LOCKED]Do not combine` can become eligible and later be closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


