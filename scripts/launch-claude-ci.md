# launch-claude-ci.sh

Launches the Claude Code CLI for `/implement` **write-capable** CI subwork from `scripts/ship-pr.sh` (recovery waterfall tier and other call sites). This launcher is a sibling of `launch-cursor-ci.sh` / `launch-codex-ci.sh`. Unlike `launch-claude-subprocess.sh`, it does **not** inject the read-only reviewer baseline preamble.

## Interface

```text
launch-claude-ci.sh --role fix|resolve-conflict --output PATH --run-id ID --repo OWNER/REPO [--plan-file PATH] [--conflict-files CSV] [--failure-log PATH] [--timeout SECONDS] [--timing-task-kind KIND] [--model MODEL]
```

Only `fix` and `resolve-conflict` are supported (no bump-classify / changelog-draft).

`--output` must be an absolute path using the same narrowed safe alphabet as other CI launchers.
`--plan-file`, when present, must be an absolute path; if the file exists, its content is inserted as optional design-plan context.
`--conflict-files` is valid only with `--role resolve-conflict` and must be a comma-separated list of repo-relative paths validated by `larch_validate_vendor_conflict_csv` from `lib-external-launcher-common.sh`.
`--failure-log`, when present, must be an absolute path to an **existing** regular file under `$IMPLEMENT_TMPDIR`. A capped excerpt piped through `scripts/redact-secrets.sh` is injected into the prompt inside `<<<FAILURE_LOG_EXCERPT>>>` / `<<<END_FAILURE_LOG>>>` delimiters. The `fix` role prompt includes the **local reproduction invariant** (re-run the same failing commands or `scripts/relevant-checks.sh` / the failing harness after fixing).

Timing defaults to `--timing-task-kind claude-ci-fix` (allow-listed in `scripts/lib-timing-kinds.sh`).

## Behavior

The launcher builds a fixed, delimiter-fenced prompt, then invokes `claude --print` (model defaults to `claude-sonnet-4-6`, overridable via `--model`). Failures best-effort append through `append-tool-failure.sh` when `IMPLEMENT_TMPDIR` is set, consistent with other CI launchers.

## Harness

`scripts/test-launch-claude-ci.sh` covers argv validation, `--failure-log` rules, redaction hook presence, and prompt persona pins (no read-only subprocess baseline marker). See `scripts/test-launch-claude-ci.md`.

## Edit In Sync

Keep this file aligned with `scripts/launch-cursor-ci.sh`, `scripts/launch-codex-ci.sh`, `scripts/lib-timing-kinds.sh`, and the launcher argv tests.
