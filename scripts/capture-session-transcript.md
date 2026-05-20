# capture-session-transcript.sh contract

## Purpose

`scripts/capture-session-transcript.sh` is the Step 7a (pre-bump log flush) wrapper for capturing the Claude Code session transcript into the `session-transcript` larch-log batch. It runs before the version bump so the transcript is part of the same PR tree that CI validates. The transcript is truncated at the pre-bump boundary (Steps 8+ are not included). The script replaces prompt-side skip branches with one best-effort command that always emits and records a terminal status.

## Interface

```text
capture-session-transcript.sh \
  --source-file <path> \
  --log-root <dir> \
  --skill <skill> \
  --run-id <run-id> \
  --no-logs-commit <true|false> \
  --execution-issues-log <path>
```

`--source-file` is the output from `token-claude-source.sh` or the snapshotted source file path from session env. The wrapper reads the first `TRANSCRIPT_PATH=` line without sourcing the file. If the source file is empty, missing, or zero-byte and `IMPLEMENT_TMPDIR` points at the active run tmpdir, the wrapper probes the encoded project directory for the current git repo under `$HOME/.claude/projects` for the newest non-symlink `*.jsonl` newer than `$IMPLEMENT_TMPDIR/session-id` (stable reference written once at Step 0; falls back to the tmpdir itself when session-id is absent). When git is unavailable, the probe widens to all of `$HOME/.claude/projects`. `--log-root`, `--skill`, and `--run-id` are forwarded to `larch-log.sh write` and `larch-log.sh commit`. `--no-logs-commit true` suppresses only the commit; the write still runs.

## Statuses

The script always exits 0 and prints exactly one `SESSION_TRANSCRIPT_STATUS=<status>` line. Status values:

- `source-file-missing` — `--source-file` was empty or not a regular file.
- `transcript-path-missing` — the source file had no `TRANSCRIPT_PATH=` line.
- `transcript-file-missing` — `TRANSCRIPT_PATH` did not point to a regular file.
- `render-failed` — `scripts/render-session-transcript.py` exited non-zero. The raw `.jsonl` is not flushed; the run continues. Stderr is truncated into the warning message.
- `render-empty` — the renderer produced an empty file (suspect input). Flush is skipped; the run continues.
- `write-failed` — `larch-log.sh write` failed.
- `suppressed-no-logs-commit` — write succeeded and `--no-logs-commit true` skipped commit.
- `commit-failed` — write succeeded and `larch-log.sh commit` failed. The warning text preserves a trimmed copy of `larch-log.sh` stderr so policy refusals (for example default-branch or post-merge guards) are distinguishable from a literal `git commit` failure. This is also the loud-failure outcome when the script is accidentally invoked post-merge on the default branch.
- `captured` — write and commit both succeeded.

The wrapper may also append non-terminal `Warnings` entries before the final status:

- `source-file-recovered-via-discovery` — the Step 0 source snapshot was missing but fallback discovery found a recent transcript under `$HOME/.claude/projects`.

For every status, including `captured`, the wrapper appends a `Warnings` entry to the execution-issues log via `append-execution-issue.sh`. Append failure is swallowed so transcript capture never becomes fatal to cleanup.

Malformed argv emits `SESSION_TRANSCRIPT_STATUS=usage-error` and exits 0 before log capture begins; regular `/implement` callers should never hit this branch.

## Rendering

Before flush, the wrapper renders the raw Claude Code session JSONL through `scripts/render-session-transcript.py` and flushes the filtered JSONL instead of the raw one. The renderer drops harness-injected slash-command expansions, housekeeping records, and routine tool outputs, keeping the user/assistant conversation plus tool outputs that report errors or warnings, in a stable machine-readable schema (header + one record per turn). See `scripts/render-session-transcript.md` for the filter rules and full schema. The `session-transcript` larch-log batch ships as `.jsonl` (declared in `scripts/larch-log-batches.sh`).

## Callers

Primary caller: `skills/implement/SKILL.md` Step 7a (pre-bump log flush), invoked before `larch-log.sh commit` so the transcript lands in the same flush commit as token/timing reports.

Secondary caller: `scripts/refresh-run-logs.sh` (Triggers A-C), which re-captures the transcript on each CI retry push so the merged PR carries the most recent transcript.

## Edit-in-sync

Update `skills/implement/SKILL.md` Step 7a pre-bump flush section, `scripts/refresh-run-logs.sh`, and `scripts/test-capture-session-transcript.sh` when changing flags, status names, or the write/commit ordering. The harness is wired through `make test-capture-session-transcript` and `test-harnesses-7`. Keep this file synchronized with `scripts/larch-log.md` when the `session-transcript` batch contract changes.
