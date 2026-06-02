# launch-codex-ci.sh

Launches Codex for `/implement` CI-related subwork from `scripts/ship-pr.sh`.

## Interface

```text
launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS]
```

`--output` must be an absolute path using the same narrowed safe alphabet as `run-external-agent.sh`.
`--plan-file`, when present, must be an absolute path; if the file exists, its content is inserted into the vendor prompt as design-plan context.
`--conflict-files`, when present with `--role resolve-conflict`, must be a comma-separated list of repo-relative paths (no `..` segments, no absolute paths, each segment must match `^[A-Za-z0-9._/-]+$`); the launcher validates the CSV then injects it into the vendor prompt inside `<<<CONFLICT_PATHS>>>` / `<<<END_CONFLICT_PATHS>>>` delimiters.
`--failure-log`, when present, must be an absolute path to an **existing** regular file under `$IMPLEMENT_TMPDIR` (the environment variable must be set). A capped, `redact-secrets.sh`-filtered excerpt is injected into the prompt inside `<<<FAILURE_LOG_EXCERPT>>>` / `<<<END_FAILURE_LOG>>>` delimiters. For **`--role fix` only**, when `${CLAUDE_PLUGIN_ROOT:-<repo>}/skills/shared/ci-fix-failure-patterns.md` exists, the same larch-specific failure-pattern fragment used by `launch-cursor-ci.sh` is spliced before the local-reproduction paragraph. The `fix` role prompt also carries the **local reproduction invariant** (re-run the same failing commands or harness after fixing).

## Behavior

The launcher builds a fixed prompt containing only trusted path and identifier values, then runs `codex exec --json` through `run-external-agent.sh`. It emits timing with `--timing-task-kind codex-ci-fix` and writes a best-effort `${OUTPUT}.token-record` sidecar when token usage can be parsed from `${OUTPUT}.events.jsonl` by `scripts/parse-codex-usage.sh`. The token-record grammar is `TOOL=codex`, `INPUT=<n>`, `OUTPUT=<n>`, `CACHE_READ=<n>`, `TOTAL=<n>`, `RAW=codex_ci_fix`; parse failure appends the parser diagnostic to `${OUTPUT}.sidecar` and leaves the token-record sidecar empty. The spawn site uses `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and outer auth retry wrapper; Codex startup stderr is captured to `${OUTPUT}.sidecar` so auth retries can be classified without leaking progress text into the final `KEY=VALUE` stdout line.

- Inline `PROMPT` body now carries the Codex subprocess-tool prohibition matching `agents/_implementer-base.md` Hard guard #9 (issue #2991): the CI fixer must not spawn persistent interactive subprocess sessions and must use heredocs / pipes / input files for subprocess input. The signature phrase `persistent interactive subprocess` is grep-pinned in `scripts/test-launch-codex-ci.sh`.

When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `${OUTPUT}.sidecar` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including an auth verdict and the final auth-loop attempt count.

## Machine-readable failure classification

After every run (including success), the launcher prints `emit_kv LAUNCHER_EXIT`, then runs `external_classify_launch_failure` from `lib-external-launcher-common.sh` and prints the resulting `LAUNCHER_FAILURE_CLASS` / `LAUNCHER_FAILURE_REASON` lines to stdout. On a non-zero exit it first calls `external_launcher_mirror_quota_from_events` so a usage-limit/quota condition that `codex exec --json` reported only on its stdout events stream (`${OUTPUT}.events.jsonl`) is mirrored into `${OUTPUT}.sidecar`; otherwise the verdict and `external_classify_launch_failure` would miss it and report a generic non-auth failure rather than `quota`/`health` (#3390). `ship-pr.sh` captures stdout/stderr into its phase fail file and consults `LAUNCHER_FAILURE_CLASS` when deciding whether to short-circuit the codex→cursor→claude waterfall when the rotated first tier reports `LAUNCHER_FAILURE_CLASS=other` (non-health). When `command -v codex` fails before launch, the script emits `LAUNCHER_EXIT=127`, classification `health`/`binary-missing`, and the usual `emit_kv OUTPUT` / `TOKEN_RECORD` lines, then exits **1** (not **2** — argv validation failures still use `die`'s exit **2**).

## Harness

`scripts/test-launch-codex-ci.sh` covers argv validation, output path validation, role validation, token-record normalization shape, failed-run token-record capture, and parse-diagnostic sidecar append behavior.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/launch-claude-ci.sh`, `scripts/append-token-record.sh`, `scripts/lib-timing-kinds.sh`, and launcher argv tests.
