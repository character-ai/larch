# clarify-state.sh contract

## Purpose

Fetches issue comments (`gh api --paginate --slurp` + `jq -s 'add // []'`), reads the first line of each body for `larch:clarify-request` / `larch:clarify-response` markers, and emits semantic `STATE` per `docs/issue-anchored-plan.md`.

## Interface

```
clarify-state.sh --issue <N> [--repo OWNER/REPO]
```

## Output Contract

- `LAST_REQUEST_ID=<n or empty>`
- `LAST_RESPONSE_ID=<n or empty>`
- `STATE=clean|awaiting-response|response-pending|ambiguous`
- `gh` / `jq` failure: `FAILED=true`, `ERROR=…`, exit 2.

## Test Harness

```
bash scripts/test-clarify-state.sh
```

`make test-clarify-state` (shard `test-harnesses-17`).

## Edit-in-sync

Update `scripts/test-clarify-state.sh` and this file when derivation rules change.
