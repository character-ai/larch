# Discussion Round 1 — issue #5992 (difficulty-calibration analyzer)

## Decision 1: Skills covered by the analyzer
- **Question**: Which run-log skill roots does the analyzer join: implement only, or implement + design + review?
- **Resolution**: All three. `difficulty-rating.json` is committed for `implement/`, `design/`, and `review/` run dirs, and the gc keep set retains it for all three (`python/larch/report/gc_run_logs.py` COMMON_KEEP; `docs/run-logs.md`). The issue asks for a per-skill confusion matrix, which requires multiple skills.
- **Source**: codebase

## Decision 2: Read-only diagnostic posture
- **Question**: May the analyzer change thresholds, panels, or points?
- **Resolution**: No. Diagnostic only, mirroring `/voter-calibration`: reads committed `larch-logs/` only, mutates nothing, affects no live panel behavior. Explicit in the issue acceptance.
- **Source**: user (issue body)

## Decision 3: Realized-difficulty formula is fixed
- **Question**: Is the realized-difficulty formula open for redesign?
- **Resolution**: No. The issue pins it: HARD if the run escalated, tripped the substantiality gate, or accepted >= 3 in-scope findings; TRIVIAL if it accepted 0; else MODERATE. Severities are excluded on purpose (174/188 accepted findings in the backtest window were major or higher, so severity does not discriminate).
- **Source**: user (issue body)

## Decision 4: Degraded-input tolerance
- **Question**: What must the analyzer tolerate?
- **Resolution**: Pre-initiative runs with absent `difficulty-rating.json` or absent classification batches, and gc-slimmed dirs that keep only the consumer-core set. `difficulty-rating.json` is in the keep set for all three skills, so slimmed dirs still join; missing per-round TSVs must degrade gracefully (skip, count as unratable, never crash).
- **Source**: user (issue body) + codebase (`docs/run-logs.md` keep sets)

## Decision 5: Join inputs exist in committed logs
- **Question**: Do all four join inputs exist as committed artifacts?
- **Resolution**: Yes. (a) `difficulty-rating.json` per run dir; (b) findings-classification TSVs: `implement/<run>/round-N/findings-classification.tsv`, `design/<run>/plan-review/round-N/findings-classification.tsv`, `review/<run>/review-findings-classification-round-N.tsv` (globs already used by `python/larch/issue/_ground_truth.py`); (c) token/timing: `token-report.json`/`timing-report.json` (implement), `token-report-final.json`/`timing-report-final.json` (design); (d) `larch-logs/rejected-analysis-verdicts.tsv` sidecar (`python/larch/issue/rejected_analysis.py` VERDICT_SIDECAR, documented in `docs/run-logs.md`).
- **Source**: codebase
