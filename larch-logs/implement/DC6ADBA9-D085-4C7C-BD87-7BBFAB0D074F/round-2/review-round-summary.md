# Review Round 2

- Mode: `diff`
- 13 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: combine-issues fetch treats non-list JSON as success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `fetch_main` coerces non-list `gh` JSON, such as an API error object or `null`, into an empty issue list and exits successfully instead of reporting `ERROR=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_19: map-runs matches parent issues by substring
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `map-runs` can match `ISSUE_NUMBER=123` against `#12` or silently choose among tied candidates, instead of exact matching and reporting ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: map-runs suppresses gh pr view failures
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Auth or network failures from `gh pr view` can produce blank or fallback TSV rows without the documented `MAP_GH_PR_VIEW_FAILED` diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: release-finish lacks pytest coverage for deleted shell harness paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `make test-release-finish` runs `test_release.py`, but `release_finish.py` has no pytest coverage for idempotent tag, release, fallback, and promote paths previously covered by the deleted shell harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: classify-bump head/worktree version mismatch guard is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `--head` worktree/plugin mismatch guard could regress, causing release prepare to classify against the wrong current version without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_24: audit preflight allow-concurrent bypass is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The documented `--allow-concurrent` override for recent audit-report concurrency checks lacks a regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: analyze-issues lenient and coordinator forwarding paths are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `load_issues` skip threshold, `--lenient` suppression, duplicate first-wins behavior, and coordinator forwarding lack tests after shell harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_28: release finish cannot reliably resume after remote lightweight tag push
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: A rerun after tag push can miss an existing remote lightweight tag, try to push the tag again, and exit before release edit or promotion retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_29: promote-latest quiet routing can hide stderr failures
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: With inherited `LARCH_QUIET_ACTIVE`, `promote-latest` can route `gh release list` failure diagnostics to the quiet log instead of stderr, violating the stderr-only failure contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: audit scan lost NO_ISSUES_FOUND timing failure
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The codex-generalist-waste scan no longer fails runs with `NO_ISSUES_FOUND` and timing over the 120 second threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: close-priors accepts malformed issue-list JSON
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `close-priors` treats invalid successful `gh issue list` JSON as an empty list, so it may exit 0 or continue without emitting the documented `ISSUE_LIST_FAILED=true` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: combine-issues apply creates orphan combined issues for empty sources
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `apply` accepts an empty parsed source issue list and can create a combined issue with no source issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: OOS header detection misses awk-compatible whitespace
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/oos_disposition.py` misses valid `### OOS_` headers with spaces or tabs after `###`, changing silent-drop behavior from fail to skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


