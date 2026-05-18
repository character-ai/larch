# `scripts/test-harness-timer.sh`

Regression harness for `scripts/harness-timer.sh`. See `scripts/harness-timer.md` for the
primary contract, output format, and parser-acceptance rules.

## Tests

1. `sleep 0.5` — asserts timing matches `^0\.[4-6][0-9]s$` (allows ±100 ms slop for sleep precision).
2. `sleep 2` — asserts timing matches `^[12]\.[0-9]{2}s$`.
3. `false` — asserts exit code 1 is mirrored AND a `LARCH_HARNESS_TIMING` line is emitted.
