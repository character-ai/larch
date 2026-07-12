### OOS_1: Reuse `design_log_publish_flow.py` instead of a large inline Bash fragment
- **Description**: Reuse `design_log_publish_flow.py` instead of a large inline Bash fragment. Scenario: The design log-publish path already isolates marker/log commits in a disposable worktree with push + PR recovery semantics (`python/larch/design/design_log_publish_flow.py`). Re-implementing that flow as prose in `SKILL.md` duplicates a proven pattern and increases drift risk across three call sites.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/learn-from-bugs/SKILL.md
- **Phase**: design



