# Step 18 coverage (Rust parity)

Offline coverage for `step-18.sh` lives in
`crates/larch-cli/src/implement_terminal_commands.rs` (Step 18 gate,
snapshot, publication, and marker nodes plus Step 19 restore, teardown, and
ordering nodes).

## Coverage

- Gate phase no-stall and stall early-exit behavior.
- The stall-layer predicate: empty and `false` are inactive; any other non-empty value is active.
- Logs-flush phase invokes `final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR" --step17-emitted "$STEP17_EMITTED"` and never emits `STALL_RECOVERY_REQUIRED`.
- Step 18b non-zero rc does not skip closing token/timing marks or terminal publication.
- An unreadable `summary-final.md` does not skip closing token/timing marks or terminal publication.
- Successful marker body emission writes exactly one balanced marker pair, no duplicate raw body, and touches `.step17-emitted` before publication.
- Both explicit Step 17 values are forwarded. `false` overrides a stale sentinel for refresh decisions, while `true` creates `.step17-emitted` before Step 18b.
- Orchestrator behavior is represented by marker extraction from captured stdout only. Missing-marker and no-Read SKILL.md prose pins remain owned by structure/callsite harnesses.
- Step 19 teardown tail records are relayed on stdout.
- Step 19 restore runs for missing finalize-state, ship stall/bail truthy values, and `STALL_STEP` mismatch, and skips for aligned state.
- Step 19 exact teardown argv includes `--state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"`.
- Closing token/timing marks and publication finish before Step 19 restore and teardown.
- Post-terminal recovery proceeds directly to logs flush without re-running the gate.
- Stall KVs, markers, and Step 19 teardown tail KVs remain on stdout.

## Edit in sync

Update the Step 18 tests in `crates/larch-cli/src/implement_terminal_commands.rs` with `step-18.sh`, `step-18.md`, `skills/implement/SKILL.md`, `make test-implement-structure`, `scripts/test-implement-timing-rehydration.sh`, and `scripts/test-render-cost-line-callsites.sh`.
