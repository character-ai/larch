# launch-codex-ci.sh

Launches Codex for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, then runs `codex exec` through `run-external-agent.sh`. It emits timing with `--timing-task-kind codex-ci-fix` and writes a best-effort `${OUTPUT}.token-record` sidecar when token usage can be scraped. The spawn site uses `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and outer auth retry wrapper; wrapper chatter and Codex startup stderr are captured to `${OUTPUT}.sidecar` so auth retries can be classified without leaking progress text into the final `KEY=VALUE` stdout line.

When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `${OUTPUT}.sidecar` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including an auth verdict and the final auth-loop attempt count.

Gemini is intentionally not added in v1. This is a scoped CI-fix launcher pair for the two active state-machine vendor slots.

## Harness

`scripts/test-launch-codex-ci.sh` covers argv validation, output path validation, role validation, and token-record normalization shape.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
