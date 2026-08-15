# test-design-multi-round-integration.sh

Offline cross-script harness for one-pass Rust `plan-review run` output, automatic multi-round Step 3 re-entry, and `design-log-publish.sh` fail-closed rules.

## Invocation

```bash
make test-design-multi-round-integration
```

## Stubs

The first legacy shell-override branch exits 0 with a skip message when the retired `LARCH_PLAN_REVIEW_*_SH` path is unavailable. Active loop coverage lives in `crates/larch-cli/tests/plan_review_loop_commands.rs`; this harness also covers the design-log publish path.

## Coverage

- Rust `plan-review run` still runs one round per entry and reaches a terminal status without revising `plan.txt`
- `round-summary.env` materialized under `plan-review/round-1/` with the per-entry terminal status
- Automatic continuation chains Rust `plan-review continuation`, Rust `plan-review step3-state --auto-continuation-entry`, and a second `plan-review run --no-preview` entry
- Round 2 uses the review round cursor, consumes the shared review-round counter once, preserves round-1 artifacts, and defers Gate C while continuing
- Round 2 fails if the materialized embedded loop script leaves stale `.step3-review-result.env` in place before dispatch
- Raw reviewer outputs remain excluded from `round-N/` snapshots
- `findings-classification.tsv` survives terminal round snapshots
- `design-log-publish.sh` publishes the same sorted `plan-review/` file list produced by the loop snapshot
- `design-log-publish.sh` rejects `unknown.bin` under `round-1/` (`PUBLISH_OK=false`)
- Symlink under `plan-review/` rejected fail-closed

## Related harnesses

- `python/test_design_log_publish_flow.py`
- `crates/larch-cli/tests/plan_review_loop_commands.rs`
- `crates/larch-cli/src/plan_review_commands.rs`
