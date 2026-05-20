# launch-cursor-ci.sh

Launches Cursor for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-cursor-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.
`--plan-file`, when present, must be an absolute path; if the file exists, its content is inserted into the vendor prompt as design-plan context.
`--conflict-files`, when present with `--role resolve-conflict`, must be a comma-separated list of repo-relative paths (no `..` segments, no absolute paths); the launcher injects the list into the vendor prompt as unresolved-path context.

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, wraps it through `cursor-wrap-prompt.sh`, and runs Cursor through `run-external-agent.sh --capture-stdout-only`. It writes retry metadata via `lib-cursor-launcher-common.sh`, emits timing with `--timing-task-kind cursor-ci-fix`, and writes a best-effort `${OUTPUT}.token-record` sidecar from Cursor JSON usage. Cursor auth setup is shared with `launch-review.sh --tool cursor`: after the Darwin preflight, the helper best-effort pre-reads the `cursor-user` / `cursor-access-token` keychain service into `CURSOR_API_KEY` so the Cursor child receives `--api-key` when the service is readable. The spawn site also uses `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and outer auth retry wrapper; auth detection reads `${OUTPUT}.diag`, where `run-external-agent.sh --capture-stdout-only` routes Cursor stderr. Before the auth-retry loop the launcher calls `cursor_launcher_setup_private_config_dir` to export a fresh private `CURSOR_CONFIG_DIR` (seeded from `~/.cursor/cli-config.json` when present), eliminating the `cli-config.json` rename race when multiple CI-fix invocations run in parallel; cleanup runs inline after the loop via `cursor_launcher_cleanup_private_config_dir`.

When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `${OUTPUT}.diag` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including an auth verdict and the final auth-loop attempt count.

## Harness

`scripts/test-launch-cursor-ci.sh` covers argv validation, output path validation, role validation, and token-record normalization shape.

## Edit In Sync

Keep this file aligned with `scripts/launch-codex-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
