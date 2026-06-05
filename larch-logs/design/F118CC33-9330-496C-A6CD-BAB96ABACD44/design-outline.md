## Proposed Design Outline

### Goals
- Remove every HARD/SIMPLE workflow-classification code path from `/implement`.
- Remove the workflow dimension from `/report-tokens` implement reports (scan, tables, warnings).
- Preserve current effective behavior: always-HARD semantics (7200s launcher timeout) become the only path.

### Non-goals
- No change to `/design`'s SIMPLE/HARD tier system or its artifacts (`design_classification`, `workflow_path` in design run-params, design summary Path bullet).
- No change to report-tokens `--skill=design` SIMPLE/HARD split.
- No migration or rewrite of committed historical run logs.

### Approach sketch
- Delete `--workflow` from `step2-implement.sh` (fix timeout at 7200s) and the hardcoded `--workflow HARD` pass in `run-step2-dispatch.sh`.
- Drop `WORKFLOW_PATH` from `persist-implement-run-flags.sh` / `implement-bootstrap.sh` persist sites and the `timing-ledger.sh workflow-path` implement call.
- `write-final-report.sh` stops resolving WORKFLOW_PATH; shared `render-run-summary.sh` omits the Path bullet when `--workflow-path` is absent (design keeps passing it).
- `report_tokens_scan.py` skips workflow extraction for implement; renderer/models drop implement workflow grouping and columns; design labels stay.
- Update SKILL.md prose, sibling `.md` contracts, and test pins (`test-implement-structure.sh:310`, format/report harnesses).

### Surfaces in scope
- `skills/implement/` (SKILL.md, `scripts/step2-implement.sh`, `run-step2-dispatch.sh`, `write-final-report.sh` + siblings/tests)
- `scripts/` shared helpers: `implement-bootstrap.sh`, `persist-implement-run-flags.sh`, `render-run-summary.sh`, `timing-report.sh` (implement-facing output only)
- `python/report_tokens_{scan,models,render,plot,issue}.py` + tests; `skills/report-tokens/SKILL.md`
- `docs/run-logs.md` summary-format prose

### Open questions
- None.
