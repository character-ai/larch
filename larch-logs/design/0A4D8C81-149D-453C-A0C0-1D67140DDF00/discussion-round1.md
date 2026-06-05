## Decision 1: Finding-count requirement strength
- **Question**: Are per-round accepted/rejected finding counts hard-required alongside duration_seconds, or best-effort?
- **Resolution**: BOTH hard-required. Per-round `duration_seconds` AND accepted/rejected counts are mandatory for /implement Step 5 and /design Step 3. The feature is not done until counts appear for both skills.
- **Source**: user

## Decision 2: /design plan-review per-round entry shape
- **Question**: What fields should each /design Step 3 plan-review per-round entry contain?
- **Resolution**: duration_seconds + accepted + rejected + OOS count (plan-review voting yields accepted/rejected/out-of-scope, so OOS is reported separately for design). /implement uses duration + accepted + rejected (no OOS field needed for code review).
- **Source**: user

## Decision 3: Scope ladder
- **Question**: How far should the change reach beyond timing-report.json + run-log flush + tests?
- **Resolution**: JSON + run-log flush + tests ONLY. Emit `rounds` in timing-report.json and the committed timing-report batch; add/extend test coverage. NO changes to the human-readable markdown `## Per-Step Durations` table; NO changes to downstream analysis tooling (/report-tokens etc.). These are explicit non-goals.
- **Source**: user

## Decision 4: Backward compatibility (hard constraint)
- **Question**: Must the new per-round data preserve the existing timing-report.json shape?
- **Resolution**: Yes — `rounds` MUST be a purely additive field on the existing per_step entry. Existing consumers (python/report_tokens_scan.py, scripts/measure-realized-cost.sh, scripts/verify-run-log-completeness.sh) must continue to parse timing-report.json unchanged. No existing field renamed or removed.
- **Source**: codebase

## Decision 5: Counts must survive into the committed report (hard constraint)
- **Question**: Where does per-round count/duration data live so it reaches the committed timing-report batch?
- **Resolution**: timing-report.json is rendered from the session timing-ledger TSV (scripts/timing-report.sh reads the ledger). Per-round duration AND counts must therefore be carried in the ledger itself (round-scoped rows), not only in tmpdir tally artifacts (review-tally.env / findings-classification.tsv), so the data is self-contained and survives flush. Ledger rows are fixed at 13 tab-columns (timing-report.sh row_ok() skips NF!=13), so any new round row kind must fit 13 columns and stay Bash 3.2-portable.
- **Source**: codebase
