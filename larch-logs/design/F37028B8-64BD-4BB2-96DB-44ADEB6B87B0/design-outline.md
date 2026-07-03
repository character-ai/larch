## Proposed Design Outline

### Goals
- Guarantee Step 8+ (ship-pr) execution-issues.md warnings from the architectural-guidelines drop-notice path reach the committed run-log batch, even when no other CI-fix/rebase retry happens before merge.
- Stop fully swallowing append failures in `_log_guidelines_ship_warning` so a failed append is visible to operators.

### Non-goals
- Rearchitecting the general run-log flush/commit pipeline (`flush_logs_pre`, Step 7a flush, Step 18 teardown safety net) beyond closing this one gap.
- Fixing every `suppress(Exception)` pattern in `ship_guidelines.py` / `architectural_guidelines.py`, only the one the issue names.
- Changing the post-merge teardown's existing guard (skip commit when `post_merge_sentinel` exists or branch is main/master); that guard is correct and must stay intact.

### Approach sketch
- Close the flush-timing gap (OOS_1) without adding a stand-alone git push that would retrigger CI (avoid regressing #5217 / #5186): make the warning ride an already-scheduled push instead of adding a new one.
- Likely touches ordering between `_invalidate_guidelines_note` (`ship.py`) and the CI-fix "normal" push path (`ci_monitor.py`'s `stage_and_push`), and/or the pre-merge transition in the merge loop.
- Replace the fully-silent `suppress(Exception)` in `_log_guidelines_ship_warning` (OOS_5) with a fail-loud fallback (per ARCHITECTURAL_GUIDELINES.md G-Py-4), keeping its best-effort contract: it must never raise and abort ship-pr.

### Surfaces in scope
- python/larch/implement/ship_guidelines.py
- python/larch/implement/ship.py
- python/larch/implement/ci_monitor.py
- Corresponding test files under python/tests/implement/

### Open questions
- Exact mechanism for closing the flush-timing gap without a new push: decided during plan drafting and plan review (Step 2b/Step 3), per discussion-round1.md Decisions 1 and 3.
