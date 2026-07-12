# test-step-18.sh

Offline harness for `step-18.sh`.

## Coverage

- Gate phase no-stall and stall early-exit behavior.
- `_stall_layer_active` predicate: empty and `false` are inactive; any other non-empty value is active.
- Finalize phase invokes `final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR" --step17-emitted "$STEP17_EMITTED"` and never emits `STALL_RECOVERY_REQUIRED`.
- Step 18b non-zero rc does not skip closing token/timing marks or teardown.
- Marker `cat` failure under `set +e` does not skip closing token/timing marks or teardown.
- Successful marker body emission writes exactly one balanced marker pair, no duplicate raw body, and touches `.step17-emitted` before teardown.
- Both explicit Step 17 values are forwarded. `false` overrides a stale sentinel for refresh decisions, while `true` creates `.step17-emitted` before Step 18b.
- Orchestrator behavior is represented by marker extraction from captured stdout only, including the missing-marker warning pin in `SKILL.md`.
- Teardown tail records are relayed on stdout.
- `_restore_finalize` runs for missing finalize-state, ship stall/bail truthy values, and `STALL_STEP` mismatch, and skips for aligned state.
- Exact teardown argv includes `--state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"`.
- Closing token/timing marks and optional restore run before teardown.
- Post-terminal recovery proceeds directly to finalize without re-running the gate.
- Stall KVs, markers, and teardown tail KVs remain on stdout.

## Edit in sync

Update this harness with `step-18.sh`, `step-18.md`, `skills/implement/SKILL.md`, `make test-implement-structure`, `scripts/test-implement-timing-rehydration.sh`, and `scripts/test-render-cost-line-callsites.sh`.
