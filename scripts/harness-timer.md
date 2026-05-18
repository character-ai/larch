# `scripts/harness-timer.sh`

## Purpose

Wraps a single regression-harness test invocation to emit per-test timing.
Called by every `test-*` recipe in `Makefile` so individual test durations
appear in CI job logs, enabling data-driven shard rebalancing.

## Usage

```bash
bash scripts/harness-timer.sh <test-name> <command> [args…]
```

`<test-name>` is the Make target name (passed via `$@` in Makefile recipes).
`<command>` and optional `[args…]` are forwarded verbatim.

## Output

After `<command>` completes, the script prints one tab-separated line to stdout
(columns separated by `\t`):

```
LARCH_HARNESS_TIMING<TAB><test-name><TAB><N>s
```

`LARCH_HARNESS_TIMING` is the sentinel prefix used by log parsers and CI
analysis tools to locate per-test timing rows.

## Invariants

- Exit code mirrors `<command>`'s exit code.
- Timing line is printed even when `<command>` fails, so partial shard runs
  still contribute data.
- Duration uses `date +%s` (second granularity); sufficient for shard
  rebalancing purposes.

## Makefile Wiring

Every `test-*` recipe line of the form `\tbash <script>` is wrapped as
`\tbash scripts/harness-timer.sh $@ bash <script>`, where `$@` is Make's
automatic variable for the current target name.

Multi-bash recipes (e.g. `test-harness-shards-coverage`, `test-render-skill`,
`test-quick-mode-docs-sync`) emit one timing line per bash invocation, both
labeled with the same target name; consumers should sum them.

## Regression Harness

No dedicated harness; covered indirectly by the existing
`scripts/test-harness-shards-coverage.sh` (which validates Makefile structure
after any recipe changes) and by running any shard target and grepping for
`LARCH_HARNESS_TIMING` in its output.

## Edit-In-Sync

Changes to the output format, argument contract, or Makefile wiring must
update this file and `docs/linting.md "Refreshing harness shard balance"` in
the same PR.
