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

## Additional coverage (single-pass status mapping)

- The removed round-cap flag is rejected as an unknown flag.
- Accepted findings are surfaced to Gate B without revising `plan.txt`.
- Zero accepted findings with zero successful collectors maps to `degraded-empty-collector`; a degraded non-empty panel maps to `zero-findings-degraded-panel`.
- Panel failures and tally errors preserve their terminal statuses before collector fallback logic.

## PATH `STUB_BIN` backstop (#3338)

After `TMP` is created, the harness prepends `$TMP/bin` to `PATH` with minimal
executable stubs for `codex`, `cursor`, and `claude`. `run_loop` defaults
script-level `LARCH_PLAN_REVIEW_*_SH` stubs cover the review/vote paths, and the PATH backstop guarantees `make lint` never launches a real external binary when a stub is missing. Per-section overrides still call their stub scripts by absolute path and are unaffected.
The `real panel dispatch` case prepends a section-local `EXTSTUB` ahead of this
global backstop when it needs specialized cursor/codex behavior.

## Scope anchor regressions

The brainstorm case now asserts that `plan-review-scope-anchor.txt` is the binding feature file passed to panel dispatch, while `plan-review-feature-context.txt` retains brainstorm synthesis as non-binding context. Layout expectations include `findings-in-scope.pre-dedup.md` and the staged scope anchor.

## Multi-round regressions (#3869)

The multi-round test runs `plan-review-loop.sh` twice in the same design tmpdir — first with `--round-num 1` (one accepted finding), then with `--round-num 2` (zero findings, convergence). It asserts:

- `round-1/round-meta.json` is written by round 1 with `ACCEPTED_COUNT == "1"`.
- `round-2/round-meta.json` is written by round 2 with `ACCEPTED_COUNT == "0"`.
- `round-1/round-meta.json` is NOT clobbered or deleted when round 2 runs.
- Both rounds produce a timing ledger row at their respective round numbers.

The `revise` field test calls `write-design-round-meta.sh` directly with and without `round-N/revise/revise.env` to verify `revise.{status,tier}` are populated from the env file when present, and `null` when absent.
