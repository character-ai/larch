# test-voter-calibration.sh contract

`skills/voter-calibration/scripts/test-voter-calibration.sh` is the offline harness for `/voter-calibration`.

It builds a synthetic `larch-logs` fixture with:

- 22-column design TSVs.
- 21-column design TSVs without `body_severity`.
- 21-column code-review TSVs.
- 18-column compact code-review TSVs.
- Neutral rows and single-voter rows that must be excluded.
- A chronic outlier above `--min-votes`.
- YES-vote severity distributions, including Calibration Score output, one all-high voter, and one mixed voter used to verify `--high-severity-threshold`.
- All-high voters score lower than mixed voters at the default high-severity threshold.
- Threshold `>= 1.0` non-penalized scoring is covered by `python/test_voting.py`.

The harness runs the analyzer directly with `CLAUDE_PLUGIN_ROOT` unset. That proves the script bootstraps `python/` imports via `Path(__file__).resolve().parents[3]`, not cwd-only path hacks.

Run with `make test-voter-calibration`.
