# test-design-multi-round-integration.sh

Offline cross-script harness for one-pass `plan-review-loop.sh` output, automatic multi-round Step 3 re-entry, and `design-log-publish.sh` fail-closed rules.

## Invocation

```bash
make test-design-multi-round-integration
```

## Stubs

PATH-style overrides via `LARCH_PLAN_REVIEW_*_SH` env vars (see `python/test_plan_review.py`).

## Coverage

- `plan-review-loop.sh` still runs one round per entry and reaches a terminal status without revising `plan.txt`
- `round-summary.env` materialized under `plan-review/round-1/` with the per-entry terminal status
- Automatic continuation chains `plan-review-continuation.sh`, `design-step3-state.sh --auto-continuation-entry`, and a second `run-step3-review.sh --no-preview` entry
- Round 2 uses the review round cursor, consumes the shared review-round counter once, preserves round-1 artifacts, and defers Gate C while continuing
- Raw reviewer outputs remain excluded from `round-N/` snapshots
- `findings-classification.tsv` survives terminal round snapshots
- `design-log-publish.sh` publishes the same sorted `plan-review/` file list produced by the loop snapshot
- `design-log-publish.sh` rejects `unknown.bin` under `round-1/` (`PUBLISH_OK=false`)
- Symlink under `plan-review/` rejected fail-closed

## Related harnesses

- `scripts/test-design-log-publish.sh`
- `python/test_plan_review.py`
- `python/test_plan_review.py`
