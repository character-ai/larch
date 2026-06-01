# oos-disposition-checkpoint.sh

Step 8+ OOS checkpoint helper for `/implement`. Computes disposition-gate inputs (fork/repo flags, commit range, `oos-issues.ndjson` discovery, design-OOS path, non-security block count, ndjson precondition), invokes `oos-disposition-gate.sh`, and logs failures via `append-tool-failure.sh`. The orchestrator calls this script and branches on its exit code; it does **not** clear `OOS_PENDING`, write `run-statistics`, or re-enter `--resume-phase pr-create` (see NEVER #17 / #18 in `skills/implement/SKILL.md`).

## Invocation

```text
oos-disposition-checkpoint.sh --implement-tmpdir DIR [--design-tmpdir DIR]
```

- `--implement-tmpdir` — Required. Session tmpdir (`$IMPLEMENT_TMPDIR`) containing `ship-pr-state.sh`, `session-id`, accepted-OOS markdown, `oos-issues-created.md`, and `larch-logs/implement/`.
- `--design-tmpdir` — Optional. Overrides `DESIGN_TMPDIR` for resolving `oos-accepted-design.md` (`<dir>/oos-accepted-design.md`). When omitted, falls back to `design-export/oos-accepted-design.md` under the implement tmpdir, then `<implement-tmpdir>/oos-accepted-design.md`.

Git mode: `100755` (direct path invocation from `SKILL.md` and the harness).

## Input resolution

No unguarded global `set -e` over fallible probes. Defaults (`_forked=false`, `_repo_unavail=false`, `_oos_range=HEAD`) are set before git/`find`/`grep` probes. Deliberate validation failures (ambiguous ndjson, missing ndjson precondition, bad CLI) tee to `oos-disposition-checkpoint.stderr.log`, log, and exit `2`. Only the gate subprocess runs under `set +e` with stderr redirected to `oos-disposition-gate.stderr.log`.

Commit range: `merge-base HEAD origin/main..HEAD` when merge-base is non-empty; `origin/main..HEAD` when `origin/main` resolves but merge-base is empty; `HEAD` when `origin/main` is absent.

## Exit codes

| Code | Meaning |
|------|--------|
| 0 | Gate passed or skipped (`--fork-mode` / `--repo-unavailable` via state file). |
| 1 | Disposition gap (gate exit 1). Logged with `--site step-8-oos-checkpoint`, `--output-file` = gate stderr log. |
| 2 | Validation/setup (gate exit 2, or pre-gate input-resolution / CLI failure). Logged with `--site step-8-oos-checkpoint-validation`; pre-gate paths use the checkpoint stderr log, gate failures use the gate stderr log. |

Gate exit 2 is **not** collapsed into exit 1 (unlike the prior inline orchestrator block).

## Logging (`log_checkpoint_failure`)

Every non-zero exit calls `append-tool-failure.sh` best-effort (`|| true`) then `exit` with the saved checkpoint rc:

- `--log "$IMPLEMENT_TMPDIR/execution-issues.md"` (required)
- `--site` — `step-8-oos-checkpoint` (rc 1) or `step-8-oos-checkpoint-validation` (rc 2 and pre-gate exit 2)
- `--tool oos-disposition-checkpoint.sh`
- `--exit-code`, `--category "Tool Failures"`, `--output-file`, `--redact`

Stderr logs:

- `$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log` — pre-gate / CLI diagnostics
- `$IMPLEMENT_TMPDIR/oos-disposition-gate.stderr.log` — gate subprocess only (created/truncated before gate invocation)

## Gate contract

Argument wiring matches the former inline `SKILL.md` block: `--fork-mode`, `--repo-unavailable`, `--oos-issues-ndjson`, `--accepted-files`, `--filed-urls-file`, `--filed-urls-strict-file`, `--commit-range`. See `oos-disposition-gate.md` for gate semantics.

## Harness

`skills/implement/scripts/test-oos-disposition-gate.sh` (sibling `test-oos-disposition-gate.md`; Makefile target `test-oos-disposition-gate`) covers both the gate and this checkpoint.
