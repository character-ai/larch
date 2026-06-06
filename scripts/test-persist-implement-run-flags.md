# test-persist-implement-run-flags.sh

Offline harness for `scripts/persist-implement-run-flags.sh`.

## Coverage

- `--emergency-requested true` writes `EMERGENCY_REQUESTED=true`.
- `--emergency-requested false` writes `EMERGENCY_REQUESTED=false`.
- Omitted `--emergency-requested` defaults to `EMERGENCY_REQUESTED=false`.
- Invalid emergency values exit **2**.
- `--self-review-requested true` writes `SELF_REVIEW_REQUESTED=true`.
- Omitted `--self-review-requested` defaults to `SELF_REVIEW_REQUESTED=false`.
- Invalid self-review values exit **2**.
- Both flags combined write both keys correctly.

The harness is invoked by `make test-persist-implement-run-flags` and is part
of the `test-harnesses-8` shard.
