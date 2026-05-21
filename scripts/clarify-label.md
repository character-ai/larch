# clarify-label.sh contract

## Purpose

Idempotently adds or removes the `needs-design-clarification` label on an issue via `gh issue edit`, only when the label set would change.

## Interface

```
clarify-label.sh --issue <N> --action add|remove [--repo OWNER/REPO]
```

## Output Contract

- `CHANGED=true|false`, `ACTION=add|remove`, `LABEL=needs-design-clarification`, exit 0.
- `gh` failure: `FAILED=true`, `ERROR=…`, exit 2.

## Test Harness

No dedicated harness yet; behavior is thin `gh` delegation.

## Edit-in-sync

If stdout keys change, add or update a harness and this file.
