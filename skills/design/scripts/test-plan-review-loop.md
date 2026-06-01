# test-plan-review-loop.sh

Offline regression harness for `plan-review-loop.sh`.

**Makefile**: `test-plan-review-loop`

## Coverage (smoke)

- `plan-review-loop.sh` parses argv and fails closed on missing required inputs.
- Script remains executable and syntactically valid (`bash -n`).

Stub cases cover zero findings, a real single-finding tally, panel-failed
header-only artifacts, a tally-failure degraded `voting-tally.md`, and
canonical-slot preservation when the middle voter fails. The
`stderr-tail-fd2` case asserts a failing collector's stderr tail reaches loop
FD 2 and `plan-review-collector.stderr` (guards the `plan-review-loop.sh` tee).

## PATH `STUB_BIN` backstop (#3338)

After `TMP` is created, the harness prepends `$TMP/bin` to `PATH` with minimal
executable stubs for `codex`, `cursor`, and `claude`. `run_loop` defaults
`LARCH_PLAN_REVIEW_REVISE_SH` to the real `revise-plan-with-waterfall.sh`, which
can invoke `launch-review.sh` and reach installed-but-unhealthy external
binaries; script-level `LARCH_PLAN_REVIEW_*_SH` stubs do not cover every path.
The PATH backstop guarantees `make lint` never launches a real external binary
even when a script-level stub is missing. Per-section `LARCH_PLAN_REVIEW_*_SH`
overrides still call their stub scripts by absolute path and are unaffected.
The `real panel dispatch` case prepends a section-local `EXTSTUB` ahead of this
global backstop when it needs specialized cursor/codex behavior.
