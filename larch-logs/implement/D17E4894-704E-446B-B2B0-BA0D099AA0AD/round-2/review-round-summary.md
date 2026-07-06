# Review Round 2

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Tempfile baseline identity is stale
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The `python/tempfile-dir-baseline.json` entry for `lint_mermaid_fences.py` still records `TemporaryDirectory` occurrence 1, but the live scan reports occurrence 2, so `python3 python/cli.py lint tempfile-dir` exits 1 and the fast lint shard stays red.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Regen baseline with occurrence 2 or fix scanner visit order for with-context vs with-body and add regression test.
  - From codex-specialist-correctness: Regenerate or correct the baseline to match the scanner’s live identity, or fix the scanner’s with-context traversal and then commit the matching baseline.
  - From codex-specialist-edge-cases: Regenerate the baseline with occurrence 2 or fix scanner traversal order and regenerate.
  - From cursor-specialist-testing: Regenerate baseline with occurrence 2 and add a unit test for nested TemporaryDirectory plus mkdtemp(dir=) counting
  - From codex-specialist-testing: Regenerate or correct python/tempfile-dir-baseline.json


### FINDING_2: Tempfile walker counts nested `with` bodies before their context expression
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-tempfile-ratchet
- **Severity**: major
- **Concern**: `_ordered_child_nodes` orders `ast.With` children by `lineno`, but `ast.withitem` has none, so a nested `tempfile.*(..., dir=...)` call in the body is counted before the outer `TemporaryDirectory` context expression and occurrence numbering drifts from source order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Visit with context_expr before body or only count unflagged calls; test lint_mermaid_fences main shape.
  - From dyn-dyn-tempfile-ratchet: When ordering children of `ast.With`, sort each `withitem` by `context_expr.lineno` (and `col_offset`), or recurse into the context expression before the `with` body; add a regression test mirroring `lint_mermaid_fences.py:274-282` and regenerate the baseline once live identity is `occurrence: 1`.


### FINDING_6: Direct `subprocess.run` trips the runner ratchet
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The new direct `subprocess.run` call in `run_log_batch.py` violates the existing subprocess-via-runner ratchet, so `python3 python/cli.py lint subprocess-via-runner` exits 1 and `make py-lint-checks-fast` cannot pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Route this git probe through the project’s runner/proc seam, or add a reason-bearing baseline or exemption if this direct call is deliberate.
  - From codex-specialist-edge-cases: Route the git probe through Runner/proc or add a reason-bearing subprocess baseline row if deliberately exempt.
  - From codex-specialist-testing: Route through the approved runner/helper seam or add a reason-bearing baseline row


### FINDING_8: Missing `pytest` import breaks the new compose-review test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The new compose-review test uses `pytest` type annotations without importing `pytest`, so ruff F821 fails before the tempfile-dir lint runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add import pytest to test_compose_review.py
