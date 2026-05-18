# `scripts/test-harness-timer.sh`

Regression harness for `scripts/harness-timer.sh`. See `scripts/harness-timer.md` for the
primary contract, output format, and parser-acceptance rules.

## Tests

1. `sleep 0.5` — asserts timing is formatted as `N.NNs` and falls within `0.40s-0.79s`.
2. `sleep 2` — asserts timing is formatted as `N.NNs` and falls within `1.90s-4.99s`.
3. `false` — asserts exit code 1 is mirrored AND a `LARCH_HARNESS_TIMING` line is emitted.
