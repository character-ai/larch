## Proposed Design Outline

### Goals
- Log rendered prompt bytes plus estimated tokens per dispatch (specialist reviewer, voter, plan-review reviewer/voter, aggregator, `review.fix_coder`), plus each slot's static agent-file bytes, into a committed run-log artifact.
- Add a `token measure-panel-cost` command that aggregates committed logs into per-source-file panel-tier bytes/tokens and ranks by realized bytes times frequency.
- Keep instrumentation best-effort: a logging failure must never block or fail the underlying dispatch.

### Non-goals
- No change to rendered prompt content or SKILL.md orchestration behavior.
- `/implement` Step 2's feature-writing coder (`dispatch_step2.py`) stays out of scope; only `review.fix_coder` counts as "implementer."
- No new hard-required completeness-audit entry in `docs/run-logs-required-files.tsv`; the new artifact follows the same best-effort convention as the existing panel-manifest.

### Approach sketch
- Add one small shared logging helper in the Python report/token layer, called at each existing "write rendered prompt to file" call site (reviewer, voter, plan-review reviewer/voter, aggregator, fix_coder).
- Log counts only (bytes plus estimated tokens), never raw prompt text, consistent with the existing committed-artifact deny-glob policy.
- New artifact rides alongside `review-panel-manifest` / `code-voter-slots` rather than reshaping their existing ad hoc row schemas.
- Verify and wire a commit path so `/design`'s plan-review rows actually reach `larch-logs/`, since today's plan-review manifest is not committed.
- Extend `python/cli.py token` with `measure-panel-cost`, following the existing `measure-references-heatmap` per-source-file shape.

### Surfaces in scope
- `python/larch/review/review_dispatch_panel.py`, `agent_voters.py`, `plan_review_panel.py`, `review_aggregate.py`, `coder_runner.py`
- `python/larch/report/tokens.py` (new aggregate verb)
- `python/larch/report/run_log_batch.py` (new batch registration)
- `docs/run-logs.md`
- New/updated Python tests under `python/tests/report/` and `python/tests/review/`

### Open questions
- None.
