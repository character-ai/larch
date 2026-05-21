# scripts/test-clarify-state.sh contract

Regression harness for `scripts/clarify-state.sh`. The stub `gh api` prints JSON from `$COMMENTS_JSON` (array of `{ "body": "..." }` objects).

## Wiring

`make test-clarify-state` (shard `test-harnesses-17`).

## Edit-in-sync

Update when `STATE` derivation or comment-fetch path changes.
