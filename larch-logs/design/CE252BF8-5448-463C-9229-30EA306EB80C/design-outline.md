## Proposed Design Outline

### Goals
- Remove all em-dashes from user-facing emitted strings in `python/larch/report/` and `python/larch/git/`.
- Update downstream parsers that detect em-dashes in the H2 run-summary heading.
- Keep existing tests green by updating string assertions and hardcoded heading fixtures.

### Non-goals
- Changing em-dashes in code comments, docstrings, or non-emitted strings.
- Changing em-dashes in files outside `python/larch/report/` and `python/larch/git/`.
- Restructuring the run-summary format beyond separator replacement.

### Approach sketch
- Audit `python/larch/report/` and `python/larch/git/` for em-dashes in f-strings and `print` calls.
- Replace each with colon, comma, or period depending on context.
- For the H2 heading (`## /{skill} run {run_id} — {outcome}`), use `: ` as the separator.
- Update `final_report.py` parser (`endswith("— stalled")` → `endswith(": stalled")`).
- Update `design_summary.py` fallback heading writer to match.
- Update all test fixtures and split-on-em-dash test helpers.

### Surfaces in scope
- `python/larch/git/pr_body.py`
- `python/larch/report/report_tokens_cost.py`
- `python/larch/report/run_logs.py`
- `python/larch/report/progress_report.py`
- `python/larch/report/_progress_report_live.py`
- `python/larch/report/final_report.py` (parser update)
- `python/larch/report/run_log_flush.py`
- `python/larch/report/tokens.py`
- `python/larch/report/gc_run_logs.py`
- `python/larch/report/cleanup_implement_logs.py`
- `python/larch/design/design_summary.py`
- Test files under `python/tests/` that assert on em-dash heading strings.

### Open questions
- None.
