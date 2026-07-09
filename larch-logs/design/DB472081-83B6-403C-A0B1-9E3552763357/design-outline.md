## Proposed Design Outline

### Goals
- Commit a durable `larch-logs/shared/learn-from-bugs-state.json` marker after each `/learn-from-bugs` run.
- Print one advisory suggestion line in `/audit-runs` when closed `[BUG]` backlog exceeds threshold.
- Expose `LEARN_FROM_BUGS_NUDGE_THRESHOLD = 25` in `config.py`.

### Non-goals
- Auto-run `/learn-from-bugs` at any point.
- Modify existing audit-run scan logic, counters, or the filed report body.
- Change the `/learn-from-bugs` Step 5 operator approval gates.

### Approach sketch
- Add `write-state` and `read-state` verbs to `learn_from_bugs.py` (marker read/write + CLI registration).
- Call `write-state` automatically at the end of `/learn-from-bugs` Step 4 (auto-commit, no operator approval).
- Add `bugs-backlog-nudge` verb to `audit_runs.py` that reads the marker, counts closed `[BUG]` issues via `gh`, applies `bug_title_match` filter, and emits a suggestion line when count exceeds threshold.
- Wire `bugs-backlog-nudge` into the `/audit-runs` orchestrator flow (after scan, before report filing).

### Surfaces in scope
- `python/larch/issue/learn_from_bugs.py`
- `python/larch/issue/audit_runs.py`
- `python/larch/core/config.py`
- `python/larch/cli.py`
- `skills/learn-from-bugs/SKILL.md`
- `.claude/skills/audit-runs/SKILL.md`
- `python/tests/issue/test_learn_from_bugs.py`
- `python/tests/issue/test_audit_runs.py`

### Open questions
- None.
