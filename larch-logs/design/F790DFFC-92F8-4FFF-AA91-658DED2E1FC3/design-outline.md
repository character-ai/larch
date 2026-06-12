## Proposed Design Outline

### Goals
- Fix `review-implement-step5-loop.sh` to emit a timing row when lint stalls with `main-agent-required`.
- Add runtime execution coverage for the ship-pr lint-fix handoff and `SHIP_PR_LEDGER_*` KV fields.
- Add sandbox coverage for the `larch-run.sh` launcher contract (dispatch routing, argv passthrough, bad-path rejection, awk-parity, partial-upgrade tmpdir).

### Non-goals
- Changes to `stall-recovery-report.sh` generic profile flags (item 4, already resolved).
- Full end-to-end ship-pr.sh integration tests.
- Test coverage for Python-side KV parsing.

### Approach sketch
- Item 3: one-line fix in `review-implement-step5-loop.sh` `main-agent-required` case.
- Items 1+2: extend `test-lint-fix-loop.sh` or `test-ship-pr-rebase.sh` with runtime execution for the ship-pr lint-fix handoff KV surface.
- Item 5: extend `test-implement-fence-shape.sh` sandbox section for dispatch, passthrough, rejection, awk-parity, partial-upgrade.

### Surfaces in scope
- `skills/review-and-fix/scripts/review-implement-step5-loop.sh`
- `scripts/test-lint-fix-loop.sh` and/or `scripts/test-ship-pr-rebase.sh`
- `scripts/test-implement-fence-shape.sh`

### Open questions
- None.
