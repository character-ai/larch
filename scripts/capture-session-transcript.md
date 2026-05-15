# capture-session-transcript.sh contract

## Purpose

`scripts/capture-session-transcript.sh` is the Step 18 wrapper for capturing the Claude Code session transcript into the `session-transcript` larch-log batch. It replaces prompt-side skip branches with one best-effort command that always emits and records a terminal status.

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
- `write-failed` — `larch-log.sh write` failed.
- `suppressed-no-logs-commit` — write succeeded and `--no-logs-commit true` skipped commit.
- `suppressed-post-merge-sentinel` — write succeeded but `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists; commit intentionally skipped because the PR has already merged.
- `commit-failed` — write succeeded and `larch-log.sh commit` failed.
- `captured` — write and commit both succeeded.

The wrapper may also append non-terminal `Warnings` entries before the final status:

- `source-file-recovered-via-discovery` — the Step 0 source snapshot was missing but fallback discovery found a recent transcript under `$HOME/.claude/projects`.

For every status, including `captured`, the wrapper appends a `Warnings` entry to the execution-issues log via `append-execution-issue.sh`. Append failure is swallowed so transcript capture never becomes fatal to cleanup.

Malformed argv emits `SESSION_TRANSCRIPT_STATUS=usage-error` and exits 0 before log capture begins; regular `/implement` callers should never hit this branch.

## Callers

Primary caller: `skills/implement/SKILL.md` Step 18. The wrapper must run before `scripts/implement-finalize.sh teardown` because teardown removes `$IMPLEMENT_TMPDIR`.

## Edit-in-sync

Update `skills/implement/SKILL.md` Step 18 and `scripts/test-capture-session-transcript.sh` when changing flags, status names, or the write/commit ordering. The harness is wired through `make test-capture-session-transcript` and `test-harnesses-4`. Keep this file synchronized with `scripts/larch-log.md` when the `session-transcript` batch contract changes.
