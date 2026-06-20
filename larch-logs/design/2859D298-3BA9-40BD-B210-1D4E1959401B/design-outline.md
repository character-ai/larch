## Proposed Design Outline

### Goals
- Resolve all 14 bundled review/plan-review pipeline robustness items in one plan, applyable piecemeal.
- For each "investigate-or-close" item: pin a concrete defect with a minimal fix plus regression test, or document a no-defect closure with rationale and make no change.
- Wire the real secret-scrub violation count into `_commit_run` so the rotation warning stops being inert (Item 14).

### Non-goals
- Re-splitting the combined issue back into separate issues.
- Refactoring the review/plan-review pipeline beyond each item's minimal targeted fix.
- Forcing speculative edits or pinning tests for items that close as no-defect.

### Approach sketch
- Step 2b triages each item against the current working tree by reading the cited symbol/anchor (line numbers drifted; navigate by symbol), then classifies real-defect vs no-defect.
- Confirmed code fixes land as single-function edits: negative-clamp `_straggler_floor` (`agent_waterfall.py`), JSON-shape guard (`compose_review.py`), thread real scrub count into `_commit_run` (`run_logs.py`).
- Coverage items add targeted pytest cases to existing harnesses; docs item reconciles zero-yield-pruning operator text at the three cited surfaces.
- Each of the 14 items gets its own plan subsection with its own files + tests.

### Surfaces in scope
- `python/agent_waterfall.py`, `python/compose_review.py`, `python/run_logs.py`, `python/redact.py`, `python/design_log_publish_flow.py`
- `python/plan_review.py`, `python/plan_review_panel.py`, `python/review_pipeline.py`, `python/review_and_fix.py`, `python/review_tally.py`
- Test harnesses (`python/test_*.py`) and operator text (`skills/implement/scripts/step-5-review.sh`, `skills/review/references/heavy-worker.md`, `docs/point-competition.md`)

### Open questions
- Item 9 (panel/voter prior-state injection) has no concrete file captured; its in-scope surface and whether it is intended must be re-derived at Step 2b, and it may resolve to a documented non-goal.
