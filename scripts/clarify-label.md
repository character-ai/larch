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

No dedicated harness yet; behavior is thin `gh` delegation.

## Edit-in-sync

If stdout keys change, add or update a harness and this file.
