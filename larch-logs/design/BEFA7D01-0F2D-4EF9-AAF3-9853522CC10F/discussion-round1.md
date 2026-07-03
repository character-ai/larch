## Decision 1: Exception-suppression replacement is in scope
- **Question**: Should replacing the blanket `contextlib.suppress(Exception)` in `_flush_review_batches_for_result` (review_and_fix.py:524) with logged-warning / execution-issue surfacing be part of this fix?
- **Resolution**: Yes — include it, alongside adding the two missing flush call sites at the `cap-hit` and `complete` terminal paths.
- **Source**: user

## Decision 2: Drop the dead `_read_kv` branch, do not add a CODE_REVIEW_LINE producer
- **Question**: The issue's suggested fix #4 ("Optional cleanup") offers two alternatives for `final_report.py:686`: produce `CODE_REVIEW_LINE` in the ship handoff, or drop the dead `_read_kv` branch. Is this cleanup in scope, and if so which alternative?
- **Resolution**: In scope — drop the dead `_read_kv(path=ship, key="CODE_REVIEW_LINE")` branch at `final_report.py:686` so the tally-file derivation (`_derive_review_line(run_dir=..., filename="code-review-tally.json")`) is the single documented source. Do not add a `CODE_REVIEW_LINE` producer.
- **Source**: user

## Decision 3: mav-resume-past-cap round-count fidelity is out of scope
- **Question**: The `mav-resume-past-cap` path at `review_and_fix.py:600` already flushes but with a stub (`rounds_completed=0, result=None`) instead of real prior-round counts. Should this design investigate/fix that gap?
- **Resolution**: Out of scope. Leave line 600's stub flush unchanged. This bug fix targets only the missing-flush regression on the `cap-hit` and `complete` terminal paths, not this separate, unconfirmed concern.
- **Source**: user

## Decision 4: No historical run-log backfill
- **Question**: Should already-committed 2026-07-03 run-log directories (e.g. `larch-logs/implement/1FA74504-.../`, `008C3B6D-.../`) be backfilled with the missing `code-review-tally.json` / `review-findings-full.jsonl` via a one-off log-only PR?
- **Resolution**: Out of scope. Code fix only — tolerate the historical gap in already-committed run logs; per-round artifacts already retain the underlying data.
- **Source**: user
