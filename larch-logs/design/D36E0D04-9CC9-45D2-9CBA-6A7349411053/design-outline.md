## Proposed Design Outline

### Goals
- Reduce per-reviewer OOS volume by hard-capping at 3 items (both `/design` and `/implement` paths).
- Raise the OOS materiality bar in the rubric and reviewer prompt instructions.
- Extend the judge-side rule to reject OOS that fails the materiality bar, not only duplicates.

### Non-goals
- No change to scoring math or voting thresholds.
- No change to in-scope finding limits or severity routing.
- No restructuring of how OOS items are voted on or filed.

### Approach sketch
- Add "automatic NO" heuristics to `skills/shared/oos-acceptance-rubric.md` (brief bullet list under backlog-relative question).
- Add "report at most 3 OOS observations" instruction to `skills/shared/reviewer-templates.md`; regenerate the four generated agent files; hand-edit the four hand-maintained agent files.
- Enforce cap in `python/plan_review_round.py:_compose_findings_from_collector` by tracking per-reviewer (slot) OOS count and dropping excess beyond 3.
- Enforce same cap in `python/review_pipeline.py:collect_findings` for `/implement` code-review path.
- Extend `python/findings_ledger.py:prompt_section` judge-side rule to reference the materiality bar explicitly.

### Surfaces in scope
- `skills/shared/oos-acceptance-rubric.md`
- `skills/shared/reviewer-templates.md`
- `agents/reviewer-*.md` (4 generated + 4 hand-maintained)
- `python/plan_review_round.py`
- `python/review_pipeline.py`
- `python/findings_ledger.py`
- `python/test_plan_review_round.py` (new test for the cap)
- `python/test_review_aggregate.py` (new test for the `/implement` cap path)

### Open questions
- None.
