# test-refresh-run-logs.sh

Offline behavioral test harness for `scripts/refresh-run-logs.sh`.

See `scripts/refresh-run-logs.md` for the primary contract.

## Harness notes

- The temporary `CLAUDE_PLUGIN_ROOT` stub copies `scripts/run-log-terminal-outcomes.inc.bash` alongside `write-final-report.sh` so the latter’s `source` line matches production layout (CI and minimal envs).
- Each scratch git repo sets **local** `user.name` / `user.email` only under that tempdir so `git commit` succeeds on hosts with no global identity (e.g. GitHub Actions).

## Coverage

- **Happy path** — pre-merge state file → helper commits updated log files (`REFRESH_COMMITTED` key present in stdout).
- **Post-merge skip** — `MERGE_RESULT=merged` or `MERGE_RESULT=admin_merged` in state → helper exits 0 with `REFRESH_SKIPPED=true REASON=post-merge`.
- **Fail-closed** — state file absent → helper exits 0 with `REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed`.

## Makefile wiring

```text
make test-refresh-run-logs
```
