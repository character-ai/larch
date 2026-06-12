# test-render-review-phase-detail.sh

Regression harness for `scripts/render-review-phase-detail.sh` (issue #3774). See
`scripts/render-review-phase-detail.md` for the full contract.

Covers: per-round table counts (suggestions made/accepted, OOS proposed/accepted,
reviewers launched) and the Total row; round dirs without `round-meta.json` are
skipped; top-reviewers attribution by `vendor/archetype` (panel-manifest map plus
basename-derive fallback); failed-slot counting from `round-meta.json` `.collector`
`STATUS != OK` blocks; per-round Time from `timing-ledger.tsv` round rows and the
`—` em dash when no ledger is present; the single-source dollar-line invariant (no
`$` / `💰` in output, cost cells are `—`); the singular `reviewer` schema fallback;
the no-completed-rounds case (`No review rounds completed.`, exit 0), including
in-flight round directories without completed metadata; usage errors (exit 2);
stdout mode; Mermaid reviewer timing Gantt charts, `--no-gantt` suppression,
vendor rows selected by overlap regardless of skill column, sanitized labels,
deterministic ids, the 25-task cap, and malformed timing row tolerance;
per-round VENDOR cost from token-ledger timestamp windows (in-window priced,
out-of-window excluded, empty window = `$0.00`); and a regression assertion that
a forced `python/report_tokens_cost.py` subprocess failure surfaces a labeled
`FAIL:` diagnostic rather than a bare non-zero abort (#3781).

Makefile target `test-render-review-phase-detail`; shard `test-harnesses-2`.
