# test-design-multi-round-integration.sh

Offline cross-script harness for one-pass `python/cli.py plan-review run` output, automatic multi-round Step 3 re-entry, and `design-log-publish.sh` fail-closed rules.

## Invocation

```bash
make test-design-multi-round-integration
```

## Stubs

The first legacy shell-override branch exits 0 with a skip message when the retired `LARCH_PLAN_REVIEW_*_SH` path is unavailable. The active coverage is the Python Step 3 loop and design-log publish path; see `python/test_plan_review.py` for current plan-review unit coverage.

## Coverage

- `python/cli.py plan-review run` still runs one round per entry and reaches a terminal status without revising `plan.txt`
- `round-summary.env` materialized under `plan-review/round-1/` with the per-entry terminal status
- Automatic continuation chains `plan-review-continuation.sh`, `python/cli.py plan-review step3-state --auto-continuation-entry`, and a second `plan-review run --no-preview` entry
- Round 2 uses the review round cursor, consumes the shared review-round counter once, preserves round-1 artifacts, and defers Gate C while continuing
- Round 2 fails if the materialized embedded loop script leaves stale `.step3-review-result.env` in place before dispatch
- Raw reviewer outputs remain excluded from `round-N/` snapshots
- `findings-classification.tsv` survives terminal round snapshots
- `design-log-publish.sh` publishes the same sorted `plan-review/` file list produced by the loop snapshot
- `design-log-publish.sh` rejects `unknown.bin` under `round-1/` (`PUBLISH_OK=false`)
- Symlink under `plan-review/` rejected fail-closed

## Related harnesses

- `python/test_design_log_publish_flow.py`
- `python/test_plan_review.py`
- `python/plan_review.py` `_LEGACY_ASSETS` for the embedded Step 3 loop body
