# test-refresh-run-logs.sh

Offline behavioral test harness for `scripts/refresh-run-logs.sh`.

See `scripts/refresh-run-logs.md` for the primary contract.

## Coverage

- **Happy path** — pre-merge state file → helper commits updated log files (`REFRESH_COMMITTED` key present in stdout).
- **Post-merge skip** — `MERGE_RESULT=merged` or `MERGE_RESULT=admin_merged` in state → helper exits 0 with `REFRESH_SKIPPED=true REASON=post-merge`.
- **Fail-closed** — state file absent → helper exits 0 with `REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed`.

## Makefile wiring

```text
make test-refresh-run-logs
```
