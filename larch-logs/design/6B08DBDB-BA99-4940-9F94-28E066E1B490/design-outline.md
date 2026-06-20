## Proposed Design Outline

### Goals
- Harden 13 independent runtime-robustness items across the review, CI agentic-fix, finalize, step-18, execution-issues, step_7a, stall-recovery, and design-OOS execution paths.
- Land minimal, targeted fixes for the 8 concrete items, with regression tests for every behavioral change.
- Resolve each of the 5 investigate-or-close items during design: pin a concrete fix where a real defect exists, else document a no-defect verdict for deliberate close.

### Non-goals
- No re-split of #4743 into separate issues; it was combined via `/combine-issues --oos` to cut issue count.
- No refactors beyond each item's minimal fix, and no cross-item coupling (items stay independently implementable).
- No changes to run-log, sentinel, or exit-code contracts beyond what a specific item requires.

### Approach sketch
- Per item: read the cited surface, confirm the defect against the current working tree (line numbers in the issue may have drifted; navigate by symbol), then apply the smallest fix.
- Concrete fixes target `python/review_and_fix.py` (Items 1, 8, 12), `python/ci_monitor.py` + `python/ci_agentic_fix.py` (Items 3, 4), `skills/implement/scripts/step-18.sh` (Item 5), `python/step_7a.py` (Item 9), and `python/design_oos.py` (Item 13).
- Investigate-or-close (Items 2, 6, 7, 10, 11): trace the cited region; fix-and-test on a real defect, else record the no-defect conclusion in the plan.
- Extend the matching pytest harness (`python/test_*.py`) for each behavioral fix; bash-script fixes keep Bash 3.2 portability and the wrapped-grep rules.

### Surfaces in scope
- `python/review_and_fix.py`, `python/ci_monitor.py`, `python/ci_agentic_fix.py`, `python/step_7a.py`, `python/execution_issues.py`, `python/design_oos.py`, `python/stall_recovery.py`
- `skills/implement/scripts/step-18.sh`, `skills/implement/references/stall-recovery.md`
- Matching pytest harnesses under `python/` (for example `python/test_execution_issues.py`)

### Open questions
- None.
