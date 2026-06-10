# Review Round 2

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Harness copies bogus non-file command words
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-dispatch-plan-review-panel.sh` copies literal non-files named `python3`, `render`, and `plan-review`, causing `test-dispatch-plan-review-panel` / Makefile harness execution to abort under `set -e` before the intended dispatch assertions run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Renderer substitution safety fixture targets missing/unscanned path
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-renderer-substitution-safety.sh` writes PR3051 fixtures into a missing `python` directory and an unscanned path, so the test can fail before linting or fail to exercise the intended linter coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: Specialist render cache key omits effective diff mode
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` builds specialist render cache keys before effective auto-classified diff mode is known, allowing stale cached prompts to be reused when the same diff path changes classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Plan-review tmpdir validation lost allowlist semantics
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` now accepts empty, current-directory, or arbitrary non-session design tmpdirs because validation only checks basic path shape instead of the previous session/tmp allowlist contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Voter scope-anchor validation lost common-shape size/path contract
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` accepts oversized scope-anchor files instead of enforcing the shared common-shape validator and 64 KiB / 65536-byte cap, allowing large tmp/repo anchors to be inlined into voter prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Generate check omits registry and git-tracking validations
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` no longer enforces the old non-empty `generators.tsv` registry and git-tracked-output checks, so an empty registry can silently disable generated-artifact drift enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


