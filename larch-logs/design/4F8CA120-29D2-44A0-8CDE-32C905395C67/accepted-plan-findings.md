### FINDING_1: Codex assessment lane lacks access to validated evidence
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: In assessment mode, Codex is not granted read access to the validated evidence directory containing `diff_path` and `knowledge_path`. The backup lane may therefore produce empty or malformed output instead of a real assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In assessment mode, pass the validated evidence directory as Codex --add-dir (keep repository -C for dirty-tree baseline), and add a launcher test that the prompt paths are inside the granted add-dir roots.
  - From Cursor-Requirements: In assessment mode, pass the validated evidence directory to Codex (extra --add-dir, or colocate launcher output under that directory), and add `test_launch_review.py` coverage that Codex `--add-dir` includes the evidence tree.


