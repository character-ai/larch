# lib-implement-round-cap.sh

Shared library for `/implement` Step 5 **effective round-cap inflation** from prior degraded review rounds.

## Bash compatibility

Targets **Bash 3.2** (macOS login shell). Uses only POSIX arithmetic `for` loops and string tests.

## `count_prior_degraded_rounds(implement_tmpdir, current_round)`

### Arguments

1. `implement_tmpdir` — absolute or normalized path to `$IMPLEMENT_TMPDIR` (must contain `round-N/` review artifacts when rounds have run).
2. `current_round` — positive integer **N** for the round about to execute. Prior rounds counted are **1 … N−1**.

### Read paths

For each `round` in `1 .. (current_round - 1)`:

- If `$implement_tmpdir/round-${round}/review-and-fix.env` exists and is readable, read `DEGRADED_ROUND=`.
- Treat missing file or unreadable path as non-degraded for that index.

### Return value

Prints a single decimal integer line to **stdout** (no trailing diagnostics): the number of prior rounds whose `DEGRADED_ROUND` resolved to `true`.

### Validation behavior

The helper does **not** validate that `current_round` is numeric; callers must enforce positive integer semantics. Non-integer `current_round` may produce unexpected loop bounds — callers normalize first.

## CLI (direct execution)

Direct execution exposes the degraded-round counter without sourcing the
library:

```bash
scripts/lib-implement-round-cap.sh --count-prior-degraded <IMPLEMENT_TMPDIR> <current_round>
```

The CLI prints one decimal integer to stdout and exits `0` on success. It exits
`2` with a stderr usage line when the flag is missing or unknown, the argument
count is wrong, or `<current_round>` is not a positive integer. The direct-entry
guard uses `BASH_SOURCE[0] == $0`, so sourcing the file remains inert and only
defines `count_prior_degraded_rounds`.

## Consumers

- `scripts/run-step5-review.sh` — `--mode single` pre-inflates `--round-cap` before dispatching `--mode diff`.
- `skills/review-and-fix/scripts/review-and-fix.sh` — `--mode loop` applies the **base** cap from `--round-cap` and inflates with this helper **inside** the loop so MAV resume re-invocations cannot double-inflate.
