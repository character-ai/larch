### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh
- **Concern**: [SCOPE-REDUCTION] Step 5 MAV bgjob ownership targets the wrong launcher. Scenario: The plan converts `step-5-resume.sh` into a `bgjob start` launcher for `implement-step5-resume`, but the long-running immediate-background fence in `skills/implement/SKILL.md` is `python/cli.py implement checks-step5-resume`, and `dispatch_commit_route.py` already arms `_bg_wait_marker` on that composite. Converting `step-5-resume.sh` would not migrate the MAV/coder resume wait, and would wrongly bgjob-wrap the foreground `--record-only` timing path.
- **Proposed resolution**: Keep `step-5-resume.sh` foreground for `--record-only` and commit-handoff timing. Migrate `implement-step5-resume` by removing `_bg_wait_marker` from `checks_step5_resume_main` and adding orchestrator `bgjob start`/`wait` around the existing `checks-step5-resume` fence in `skills/implement/SKILL.md` and `checks-repair-loop.md`; update `scripts/test-implement-structure.sh` pins accordingly.
