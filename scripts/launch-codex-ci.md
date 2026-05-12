# launch-codex-ci.sh

Launches Codex for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, then runs `codex exec` through `run-external-agent.sh`. It emits timing with `--timing-task-kind codex-ci-fix` and writes a best-effort `${OUTPUT}.token-record` sidecar when token usage can be scraped.

Gemini is intentionally not added in v1. This is a scoped CI-fix launcher pair for the two active state-machine vendor slots.

## Harness

`scripts/test-launch-codex-ci.sh` covers argv validation, output path validation, role validation, and token-record normalization shape.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
