### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:844-853
- **Concern**: The plan pins Cursor assessment workspace to the validated evidence directory but does not pin Codex read access to that same directory.. Scenario: REQUESTS_JSON carries absolute diff_path and knowledge_path values under $IMPLEMENT_TMPDIR/architectural-assessment-evidence-*/. Today Codex review launches with -C set to the repository and --add-dir set to the launcher output parent, so an assessment-mode Codex lane cannot read those evidence files, will return empty or invalid JSON, and the backup lane will not produce a real assessment.
- **Proposed resolution**: In assessment mode, pass the validated evidence directory as Codex --add-dir (keep repository -C for dirty-tree baseline), and add a launcher test that the prompt paths are inside the granted add-dir roots.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:805-853
- **Concern**: The plan pins Cursor assessment workspace to the validated evidence directory but does not give Codex read access to that same evidence tree.. Scenario: Codex review launch only `--add-dir`s `output.parent` (`sandbox_dir`). If per-lane result artifacts live outside the validated evidence directory, Codex cannot read `diff_path` / `knowledge_path` from `REQUESTS_JSON`, so the lane returns empty or unparseable output even when Cursor is down and Codex is the intended backup.
- **Proposed resolution**: In assessment mode, pass the validated evidence directory to Codex (extra `--add-dir`, or colocate launcher output under that directory), and add `test_launch_review.py` coverage that Codex `--add-dir` includes the evidence tree.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:821-862
- **Concern**: Assessment mode does not say to replace Codex review trusted-instructions with assessment constraints.. Scenario: Codex assessment still writes `_CODEX_REVIEW_STRICT_PREAMBLE` into `trusted-instructions.txt`, which frames the task as read-only code review rather than the compact assessment JSON contract. That can push Codex toward review-shaped output, so the coordinator treats a real backup attempt as malformed and advances prematurely.
- **Proposed resolution**: In assessment mode, skip or swap the review trusted-instructions for assessment-only constraints aligned with `architectural-assessment-agent.md`, and test that Codex assessment launches do not inject the review preamble.
