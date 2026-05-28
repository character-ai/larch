# test-persist-implement-run-flags.sh

Offline harness for `scripts/persist-implement-run-flags.sh`.

## Coverage

- `--emergency-requested true` writes `EMERGENCY_REQUESTED=true`.
- `--emergency-requested false` writes `EMERGENCY_REQUESTED=false`.
- Omitted `--emergency-requested` defaults to `EMERGENCY_REQUESTED=false`.
- Invalid emergency values exit **2**.

The harness is invoked by `make test-persist-implement-run-flags` and is part
of the `test-harnesses-8` shard.
