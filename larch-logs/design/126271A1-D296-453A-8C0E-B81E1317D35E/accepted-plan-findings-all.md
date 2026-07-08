### FINDING_2: Baseline file validation must allow test paths
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Copying the tempfile lint's `larch/` path guard would reject valid test baselines under `python/tests/**/test_*.py` and `python/test_*.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Anchor paths at python/ and validate file as a normalized tests/**/test_*.py or test_*.py path; do not reuse the larch/ prefix guard from lint_tempfile_dir.py
  - From Cursor-Innovation: Anchor paths at python/ and validate file as a normalized tests/**/test_*.py or test_*.py path; do not reuse the larch/ prefix guard from lint_tempfile_dir.py
  - From Cursor-Pragmatic: Validate baseline file paths as python/-relative tests/**/test_*.py (or top-level test_*.py), not larch/** only.


### FINDING_5: Keep the classifier attribute-specific
- **Reviewer(s)**: Codex-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: A module-wide structural shortcut would be too broad if it skips the lint whenever the facade module has any top-level `def`, `class`, or assignment, because unrelated top-level code should not mask the patched attribute's own binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Lint Ratchet Specialist: Classify only the patched attribute's own binding. Ignore unrelated module-level defs, classes, and assignments.


### FINDING_6: Resolve imported-module attribute chains
- **Reviewer(s)**: Codex-dyn-Lint Ratchet Specialist
- **Severity**: major
- **Concern**: The resolver must handle imported-module attribute chains, not just bare imported names, or it will miss existing `monkeypatch.setattr(ship.run_logs, ...)` patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Lint Ratchet Specialist: Resolve attribute chains rooted in imported modules, then apply the same import-only binding check to the resolved repo module.


