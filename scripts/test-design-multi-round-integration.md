# test-design-multi-round-integration.sh

Offline cross-script harness for multi-round `plan-review-loop.sh` output and `design-log-publish.sh` fail-closed rules.

## Invocation

```bash
make test-design-multi-round-integration
```

## Stubs

PATH-style overrides via `LARCH_PLAN_REVIEW_*_SH` env vars (see `skills/design/scripts/test-plan-review-loop.sh`).

## Coverage

- Multi-round loop with `--round-cap 2` reaches `LOOP_STATUS=cap-hit`
- `round-summary.env` materialized under `plan-review/round-1/`
- Raw reviewer outputs remain excluded from `round-N/` snapshots
- `design-log-publish.sh` publishes the same sorted `plan-review/` file list produced by the loop snapshot
- `design-log-publish.sh` rejects `unknown.bin` under `round-1/` (`PUBLISH_OK=false`)
- Symlink under `plan-review/` rejected fail-closed

## Related harnesses

- `scripts/test-design-log-publish.sh`
- `skills/design/scripts/test-plan-review-loop.sh`
- `scripts/test-lib-design-round-artifacts.sh`
