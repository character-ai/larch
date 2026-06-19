### OOS_18: [OUT_OF_SCOPE] Stale CI workflow comments describe single-process pylint
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-lint-surface-output.txt
- **Severity**: nit
- **Concern**: Comments in `.github/workflows/ci.yaml:586-588` still describe single-process pylint duplicate-code checking ("must run single-process" because `-j>1` is incorrect). The branch replaces that with the parallel pair-comparison runner via `python/cli.py lint duplicate-code`, so operator-facing workflow docs are misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update comment to match the parallel pair-comparison runner.
  - From dyn-lint-surface-output.txt: Update the `python-lint-duplicate-code` job comments to describe the new runner (PyLinter ingestion, pair-parallel `combinations`, pinned pylint 4.0.5) and drop the obsolete `-j 1` rationale.


