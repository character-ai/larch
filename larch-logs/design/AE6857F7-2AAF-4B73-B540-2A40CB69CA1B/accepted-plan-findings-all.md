### FINDING_1: Removing `_oos.py` skip-file requires suppression-reason baseline synchronization
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Lint Bypass Auditor, Codex-dyn-Lint Bypass Auditor
- **Severity**: major
- **Concern**: Removing `_oos.py`’s live `pylint: skip-file` pragma without removing or regenerating its existing suppression-reason baseline row leaves a stale baseline entry. The suppression-reason lint and `make py-lint-checks-fast` will then fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `### UPDATED: python/larch/issue/_oos.py` step (or a paired baseline step), drop the stale `larch/issue/_oos.py` / `pylint-skip-file` row or run `make regen-suppression-reason-baseline` after burndown; add that check to the testing strategy.
  - From Cursor-Innovation: Add a firm step under `### UPDATED: python/larch/issue/_oos.py` (or testing strategy): after dropping skip-file, regenerate `python/suppression-reason-baseline.json` via `make regen-suppression-reason-baseline` so the stale `larch/issue/_oos.py` `pylint-skip-file` identity is removed.
  - From Cursor-Pragmatic: In the `_oos.py` deliverable (or a firm `### UPDATED: python/suppression-reason-baseline.json` step), run `make regen-suppression-reason-baseline` after removing the skip-file pragma so the stale `pylint-skip-file` row is dropped; keep the testing strategy’s `make py-lint-checks-fast` step as the verifier.
  - From Cursor-Requirements: Add `### UPDATED: python/suppression-reason-baseline.json` (or an explicit `_oos.py` sub-step) to regenerate via `python/cli.py lint suppression-reason --write` after skip-file removal, and extend testing to confirm suppression-reason passes alongside `make py-lint-checks-fast`
  - From Cursor-dyn-Lint Bypass Auditor: Add an explicit `### UPDATED:` step to drop the `_oos.py` `pylint-skip-file` row from `python/suppression-reason-baseline.json` (or regenerate via `lint suppression-reason --write`) in the same change that removes the pragma.


### FINDING_5: Align malformed-Python testing with engine exit semantics
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The engine maps malformed Python under its existing policies to exit 1 or 0, so the planned new-rule test cannot expect exit 2 without changing engine policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Revise the planned test to assert fail-closed exit 1, or explicitly add and test a new engine error policy.


### FINDING_2: Unreadable-file behavior conflicts with engine exit semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The unreadable-file edge-case requirement conflicts with the existing engine behavior, which returns exit code 2 with stderr and no stdout finding for `ScanError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align edge cases and tests with engine behavior: unreadable paths exit `2` without a stdout finding; reserve exit `1` for live detections such as malformed Python under `syntax_policy=fail`.


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py
- **Concern**: [SCOPE-REDUCTION] Drop unreadable-file exit-1 edge case. Scenario: Edge cases require unreadable tracked files to surface findings with exit 1, but engine.py discovery calls `_load_source`, which raises `ScanError` and `run_rule` returns exit 2 before the rule detector runs. The engine update explicitly keeps discovery and exit codes unchanged, so this edge case cannot be met without new engine behavior.
- **Proposed resolution**: Remove unreadable-file exit-1 language from Edge cases and tests, or document that unreadable paths remain engine exit 2 while malformed Python stays syntax_policy exit 1.


