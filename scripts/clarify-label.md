# clarify-label.sh contract

## Purpose

Idempotently adds or removes the `needs-design-clarification` label on an issue via `gh issue edit`, only when the label set would change.

## Interface

```
clarify-label.sh --issue <N> --action add|remove [--create-if-missing] [--repo OWNER/REPO]
```

When `--create-if-missing` is set together with `--action add`, the script runs `gh label create needs-design-clarification` (idempotent via `|| true`) before `gh issue edit --add-label`, so the label exists on the repo even when it has never been created.

## Output Contract

- `CHANGED=true|false`, `ACTION=add|remove`, `LABEL=needs-design-clarification`, exit 0.
- `gh` failure: `FAILED=true`, `ERROR=…`, exit 2.

## Test Harness

Offline coverage lives in `scripts/test-clarify-state.sh` and `scripts/test-clarify-comment.sh` (Makefile `test-clarify-state` / `test-clarify-comment` targets). This script is thin `gh` delegation; those harnesses exercise marker parsing, state derivation, and comment posting envelopes.

## Edit-in-sync

If stdout keys change, add or update a harness and this file.
