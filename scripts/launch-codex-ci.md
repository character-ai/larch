# launch-codex-ci.sh

Launches Codex for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.
`--plan-file`, when present, must be an absolute path; if the file exists, its content is inserted into the vendor prompt as design-plan context.
`--conflict-files`, when present with `--role resolve-conflict`, must be a comma-separated list of repo-relative paths (no `..` segments, no absolute paths, each segment must match `^[A-Za-z0-9._/-]+$`); the launcher validates the CSV then injects it into the vendor prompt inside `<<<CONFLICT_PATHS>>>` / `<<<END_CONFLICT_PATHS>>>` delimiters.
`--failure-log`, when present, must be an absolute path to an **existing** regular file under `$IMPLEMENT_TMPDIR` (the environment variable must be set). A capped, `redact-secrets.sh`-filtered excerpt is injected into the prompt inside `<<<FAILURE_LOG_EXCERPT>>>` / `<<<END_FAILURE_LOG>>>` delimiters. The `fix` role prompt also carries the **local reproduction invariant** (re-run the same failing commands or harness after fixing).

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, then runs `codex exec` through `run-external-agent.sh`. It emits timing with `--timing-task-kind codex-ci-fix` and writes a best-effort `${OUTPUT}.token-record` sidecar when token usage can be scraped. The spawn site uses `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and outer auth retry wrapper; wrapper chatter and Codex startup stderr are captured to `${OUTPUT}.sidecar` so auth retries can be classified without leaking progress text into the final `KEY=VALUE` stdout line.

When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `${OUTPUT}.sidecar` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including an auth verdict and the final auth-loop attempt count.

## Harness

`scripts/test-launch-codex-ci.sh` covers argv validation, output path validation, role validation, and token-record normalization shape.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/launch-claude-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
