### FINDING_3: Stale Step 18 harness comment
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Harness Parity Auditor
- **Severity**: major
- **Concern**: `test-write-final-report.sh` retains a reference to deleted `test-step-18.sh`, which can violate removed-path documentation requirements and retired-script lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan to retarget the comment to `python/tests/implement/test_implement_shell_scripts.py` without retaining the deleted path
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/test-write-final-report.sh to retarget the comment at python/tests/implement/test_implement_shell_scripts.py (or delete the comment if redundant after step-18.md is updated).
  - From Codex-Pragmatic: Update this retained harness to remove or retarget the obsolete Step 18 harness reference
  - From Cursor-Requirements: Retarget the comment to python/tests/implement/test_implement_shell_scripts.py (Step 18 node group) in the same reference sweep as Makefile, agent-lint, and docs/linting.md.
  - From Codex-Requirements: Update the comment to name the new pytest Step 18 coverage or remove the obsolete sentence
  - From Cursor-dyn-Harness Parity Auditor: Retarget the comment to python/tests/implement/test_implement_shell_scripts.py (Step 18 finalize/marker node group) or drop it during the reference sweep.


### FINDING_6: Historical fixture references will fail retired-script lint
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: Tracked plan-fidelity calibration fixtures retain retired harness-path literals that the planned retired-script lint will detect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add both fixture diffs to the updated files and replace the retired harness reference with the new pytest module path
  - From Codex-Pragmatic: Add a narrowly tested retired-script-lint exclusion for the historical plan-fidelity fixture corpus, preserving its replay contents


### FINDING_14:
- **Reviewer(s)**: Codex-dyn-Harness Parity Auditor
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/test_fixtures/plan-fidelity-calibration/diffs/66A96EAD-3088-4750-AE3A-64A0E11EABBD_FINDING_10.diff:2324; python/test_fixtures/plan-fidelity-calibration/diffs/E79F3F0B-4459-48FB-8241-5DDB90ABF050_FINDING_1.diff:1626; python/larch/lint/migration_lint.py:268-329
- **Concern**: [SCOPE-REDUCTION] The plan adds the token harness to the retired-script manifest but omits two tracked calibration fixtures that retain its full path.. Scenario: `make lint-retired-scripts` scans tracked files outside `larch-logs` and will report both fixture literals after the harness is deleted.
- **Proposed resolution**: Add the two fixture updates needed to replace the retired harness reference with the new pytest coverage reference, then preserve their intended calibration assertions.


