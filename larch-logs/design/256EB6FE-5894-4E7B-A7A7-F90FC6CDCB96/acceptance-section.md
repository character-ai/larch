## Acceptance

- `/voter-calibration --era all` segments the committed-log corpus into pre- and post-incentive eras and renders both an `## Agreement Table` and a `## Voter Severity Scoreboard` per era, so panel `High Rate` and `Calibration Score` are directly comparable across the incentive boundary.
- `--era pre` / `--era post` filter to a single era; `--era-since-date YYYY-MM-DD` sets a deterministic boundary that overrides auto-detection.
- The default (no `--era`) invocation is unchanged and byte-stable; every existing `test-voter-calibration.sh` assertion still passes.
- Auto-boundary degrades cleanly to a "pass `--era-since-date`" message with exit `0` (no traceback) when `gh` or `git` is missing, the repo is unresolved, the incentive issue is unshipped, or `closedAt` is unparseable.
- Runs whose `manifest.json` lacks a parseable `started_at` are excluded from both eras and counted in the report.
- `make test-voter-calibration && make lint && make py-lint && make py-test` all pass.
