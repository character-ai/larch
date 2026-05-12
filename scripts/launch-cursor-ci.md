# launch-cursor-ci.sh

Launches Cursor for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-cursor-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, wraps it through `cursor-wrap-prompt.sh`, and runs Cursor through `run-external-agent.sh --capture-stdout-only`. It writes retry metadata via `lib-cursor-launcher-common.sh`, emits timing with `--timing-task-kind cursor-ci-fix`, and writes a best-effort `${OUTPUT}.token-record` sidecar from Cursor JSON usage.

## Harness

`scripts/test-launch-cursor-ci.sh` covers argv validation, output path validation, role validation, and token-record normalization shape.

## Edit In Sync

Keep this file aligned with `scripts/launch-codex-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
