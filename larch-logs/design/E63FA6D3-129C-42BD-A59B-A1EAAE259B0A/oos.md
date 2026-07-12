### FINDING_2: Run publication from the state worktree
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `pr create` and related Python logic use process CWD rather than `--root`; invoking them from `ANALYSIS_ROOT` can target the wrong branch or fail clean-worktree checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require an explicit subshell rooted at `STATE_WORKTREE` around `write-state`, marker `git commit --only`, `cli.py pr create`, and `gh pr merge`; extend `_structure_learn_from_bugs_specialized.py` to assert that pattern (for example `( cd "$STATE_WORKTREE" &&`) adjacent to those commands, not merely the token `STATE_WORKTREE` elsewhere in the skill.
  - From Cursor-Pragmatic: Require an explicit subshell ( cd "$STATE_WORKTREE" && ... ) around write-state, marker commit, python3 ... pr create, and post-create validation; keep git -C "$ANALYSIS_ROOT" only for worktree add/remove lifecycle; add a structural assertion that pr create is not launched from ANALYSIS_ROOT cwd.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: Preserve fetched proposal history
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Writing reconciled state without incorporating proposal history from the fetched default branch can erase newer proposals from concurrent runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Merge proposal history from the fetched marker with this run's reconciled inputs using stable-ID conflict rules before `write-state`; fail closed on conflicts.
  - From Codex-Requirements: Before writing, require every fetched marker proposal to remain compatibly represented and ordered in the reconciled input. Fail closed on missing or conflicting records, and assert this guard in the structural test.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Reuse `design_log_publish_flow.py` instead of a large inline Bash fragment
- **Description**: Reuse `design_log_publish_flow.py` instead of a large inline Bash fragment. Scenario: The design log-publish path already isolates marker/log commits in a disposable worktree with push + PR recovery semantics (`python/larch/design/design_log_publish_flow.py`). Re-implementing that flow as prose in `SKILL.md` duplicates a proven pattern and increases drift risk across three call sites.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

