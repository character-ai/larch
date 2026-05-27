# lib-voter-coverage.sh

## Purpose

`scripts/lib-voter-coverage.sh` contains source-only helpers for plan-voter coverage accounting and stdout status KV emission. It keeps effective-judge counting, degraded-panel warnings, and the interleaved voter status block reusable without coupling callers to a global `$DESIGN_TMPDIR`.

## Sourced From

- `scripts/dispatch-plan-voters.sh`
- Future plan-voter dispatchers that need the same coverage/status contract

## Function Reference

### `voter_coverage_compute_effective_judges <status-path-parse-rate triples...>`

Accepts one tab-delimited triple per voter: `<status>\t<path>\t<parse_rate_status>`. Prints the integer count of voters whose status is not `failed`, whose parse-rate status is not `NOT_SUBSTANTIVE`, and whose output path is non-empty.

### `voter_coverage_emit_degraded_warning_if_needed <effective_judges> <expected_judges>`

Emits the degraded plan-review panel warning through `larch_err` and `emit_kv DEGRADED_PANEL_WARNING` only when `effective_judges < expected_judges`. Callers pass the expected judge count explicitly; the helper does not infer panel size.

### `voter_coverage_emit_status_block <v1 path> <v1 tool> <v1 status> <v1 parse-rate> <v2 path> <v2 tool> <v2 status> <v2 parse-rate> <v3 path> <v3 tool> <v3 status> <v3 parse-rate> <plan-voter-paths-file>`

Emits the complete voter status KV block in the established interleaved order: Voter 1 path/tool/status/parse-rate, Voter 2 and 3 paths, conditional `VOTER_PATHS_FILE`, then Voter 2 and 3 tool/status/parse-rate fields. This is a single block-level helper so downstream parsers keep the same key order and `VOTER_PATHS_FILE` placement.

## Invariants

- No global mutable state.
- Does not read `$DESIGN_TMPDIR`; callers pass every path explicitly.
- Assumes the caller has sourced `scripts/lib-quiet.sh` and run `larch_quiet_init`.
- Preserves the emitted voter path/tool/status/parse-rate fields verbatim; it does not inspect or transform review severity data.
- Per-round routing safe: callers pass per-round paths when a dispatcher is operating under a per-round `--design-tmpdir`.

## Harness

`scripts/test-dispatch-plan-voters.sh` exercises this library through the dispatcher stdout contract, including effective-judge degradation, conditional `VOTER_PATHS_FILE`, and byte-order-sensitive status KV emission.
