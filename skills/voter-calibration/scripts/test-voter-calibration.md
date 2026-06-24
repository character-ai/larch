# test-voter-calibration.sh contract

`skills/voter-calibration/scripts/test-voter-calibration.sh` is the offline harness for `/voter-calibration`.

It builds a synthetic `larch-logs` fixture with:

- 22-column design TSVs.
- 21-column design TSVs without `body_severity`.
- 21-column code-review TSVs.
- 18-column compact code-review TSVs.
- Neutral rows and single-voter rows that must be excluded.
- A chronic outlier above `--min-votes`.
- YES-vote severity distributions, including one all-high voter and one mixed voter used to verify `--high-severity-threshold`.

The harness runs the analyzer directly with `CLAUDE_PLUGIN_ROOT` unset. That proves the script bootstraps `python/` imports via `Path(__file__).resolve().parents[3]`, not cwd-only path hacks.

Run with `make test-voter-calibration`.
