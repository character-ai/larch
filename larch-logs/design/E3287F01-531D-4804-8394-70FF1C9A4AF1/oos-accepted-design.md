### OOS_1: _summarize still treats absent targets as 0 during gaps; reappear-after-gap summary not in scope
- **Description**: _summarize still treats absent targets as 0 during gaps; reappear-after-gap summary not in scope. Scenario: After _build_revisions clears stale last_values, detailed rows for a reappearing target get previous=None, but _summarize advance(..., snapshot_values.get(target, 0)) can still drive accumulators to 0 while the target is absent and never re-seed on reappear; summary totals can diverge from detailed ledger for disappear-then-reappear histories
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/lint/skill_closure_ledger.py:272-296
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6233
