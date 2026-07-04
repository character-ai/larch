### FINDING_1: `--since-tag` tag validation ignores resolved `--root`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `--since-tag` ref validation can run against the ambient checkout instead of the resolved `--root`, so the tag check and the history walk can disagree and produce empty or wrong post-tag summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the Tag filtering section, require tag rev-parse --verify (and any follow-on git calls) through the same ProcRunner/git._run path with cwd=resolved root, matching log_path_commits and show_file.


