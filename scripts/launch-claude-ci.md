# launch-claude-ci.sh

Launches the Claude Code CLI for `/implement` **write-capable** CI subwork from `scripts/ship-pr.sh` (recovery waterfall tier and other call sites). This launcher is a sibling of `launch-cursor-ci.sh` / `launch-codex-ci.sh`. Unlike `launch-claude-subprocess.sh`, it does **not** inject the read-only reviewer baseline preamble.

## Interface

```text
launch-claude-ci.sh --role fix|resolve-conflict --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS] [--timing-task-kind KIND] [--model MODEL]
```

Only `fix` and `resolve-conflict` are supported.

`--output` must be an absolute path using the same narrowed safe alphabet as other CI launchers.
`--plan-file`, when present, must be an absolute path; if the file exists, its path is canonicalized (resolving symlinks via `cd -P`/`pwd -P`) and the content is piped through `python3 python/cli.py redact secrets` before insertion as optional design-plan context.
`--conflict-files` is valid only with `--role resolve-conflict` and must be a comma-separated list of repo-relative paths validated by `larch_validate_vendor_conflict_csv` from `lib-external-launcher-common.sh`.
`--failure-log`, when present, must be an absolute path to an **existing** regular file under `$IMPLEMENT_TMPDIR`. A capped excerpt piped through `python3 python/cli.py redact secrets` is injected into the prompt inside `<<<FAILURE_LOG_EXCERPT>>>` / `<<<END_FAILURE_LOG>>>` delimiters. For **`--role fix` only**, when `${CLAUDE_PLUGIN_ROOT:-<repo>}/skills/shared/ci-fix-failure-patterns.md` exists, the same larch-specific failure-pattern fragment used by the other CI launchers is spliced before the local-reproduction paragraph. The `fix` role prompt includes the **local reproduction invariant** (re-run the same failing commands or `scripts/relevant-checks.sh` / the failing harness after fixing).

Timing defaults to `--timing-task-kind claude-ci-fix` (allow-listed in `scripts/lib-timing-kinds.sh`).

## Behavior

The launcher builds a fixed, delimiter-fenced prompt, then invokes `claude --print --output-format json` (model defaults to `claude-sonnet-4-6`, overridable via `--model`). Failures best-effort append through `python3 python/cli.py run-log append-failure` when `IMPLEMENT_TMPDIR` is set, consistent with other CI launchers. The launcher also calls `append_vendor_failure_diagnostics` (from `scripts/lib-failed-agent-stderr-tail.sh`, sourced at startup) to stage the per-slot failure diagnostic for the `vendor-failure-diagnostics` larch-log batch committed at Step 7a.

**Spawned-Claude token capture (issue #3637)**: a successful run **must** promote a non-empty string `.result` over `${OUTPUT}` (CI-fix collectors and the timing ledger keep seeing prose) and folds the reported `.usage` into the `claude_sub` ledger lane via `token-ledger.sh record-vendor claude_sub … raw=claude_ci` (priced at Claude rates downstream; the single `cache_creation` field collapses into one `cache_create` bucket). **Fail-closed**: an `is_error:true` envelope, an empty/missing/non-string `.result`, or JSON-looking output that cannot be parsed writes a `CLAUDE_JSON_RESULT_INVALID` sentinel, appends a diagnostic to `${OUTPUT}.stderr`, sets `LAUNCHER_EXIT=99`, and records no usage. On the success path the `${OUTPUT}.token-record` sidecar is populated from the real `.usage` counts (`TOOL=claude … RAW=claude_ci`); when the output is genuine non-JSON prose it falls back to a word-count proxy (also `RAW=claude_ci`). The next `python3 python/cli.py run-log refresh` token-report pass picks up the ledger row.

## Machine-readable failure classification

After every run, the launcher prints `emit_kv LAUNCHER_EXIT`, then `external_classify_launch_failure` lines (`LAUNCHER_FAILURE_CLASS` / `LAUNCHER_FAILURE_REASON`) to stdout for `ship-pr.sh`, using `${OUTPUT}.stderr` as the sidecar input. Missing `claude` on `PATH` emits `health`/`binary-missing` with `LAUNCHER_EXIT=127` before exiting **1**.

**Stdout-contract**: the script always exits 0 (except the early exit-1 when `claude` is absent from `PATH`). Callers **must** parse `LAUNCHER_EXIT=` from stdout to distinguish tool success from tool failure; the process exit code is not a reliable signal for the normal exit path.

## Harness

`scripts/test-launch-claude-ci.sh` covers argv validation, `--failure-log` rules, redaction hook presence, and prompt persona pins (no read-only subprocess baseline marker). See `scripts/test-launch-claude-ci.md`.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/launch-codex-ci.sh`, `scripts/lib-timing-kinds.sh`, and the launcher argv tests.
