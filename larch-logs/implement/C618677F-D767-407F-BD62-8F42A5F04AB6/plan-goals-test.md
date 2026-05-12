## Goal
Save the complete Claude Code session transcript (.jsonl) as a committed larch-log batch at the end of each /implement run.

## Goal
Save the complete Claude Code session transcript (.jsonl) as a committed larch-log batch at the end of each /implement run, enabling full post-hoc auditability.

## Implementation Plan

### 1. `scripts/larch-log-batches.sh`
Add one row to `LARCH_LOG_BATCHES`:
```
session-transcript .jsonl replace none
```
`replace` because we want the single latest full transcript, not incremental append. Sanitizer `none` because the existing `larch_log_redact_file` (called by `larch-log.sh write`) handles secrets and tmpdir paths.

### 2. `scripts/larch-log-batches.md`
Add `session-transcript` to the batch list in the doc.

### 3. `scripts/test-larch-logs-batches.sh`
Add `session-transcript` to the expected-batches assertion list.

### 4. `skills/implement/SKILL.md` — Step 18, before teardown
Add a best-effort bash block:
- Read `TRANSCRIPT_PATH` from `$IMPLEMENT_TMPDIR/claude-source.env` (already populated at Step 0)
- If file exists, call `larch-log.sh write --batch session-transcript --input-file "$TRANSCRIPT_PATH"` (auto-redacts)
- Call `larch-log.sh commit --no-push` to flush

All wrapped in `|| true` — never fatal. The `claude-source.env` was snapshotted at Step 0 before any concurrent Claude sessions could race the resolver, so `TRANSCRIPT_PATH` points to exactly this run's transcript.

## Edge Cases
- `claude-source.env` absent or `TRANSCRIPT_PATH` empty → skip silently
- Transcript file missing at commit time → `larch-log.sh write` exits non-zero → `|| true` suppresses
- Redaction pipeline failure → `larch-log.sh write` exits non-zero → suppressed
- Transcript too large to commit → handled by git; operators can `.gitignore` specific paths if needed

## Test Plan
- Run `/relevant-checks` (pre-commit + agent-lint)
- `test-larch-logs-batches.sh` (via `make lint`) will verify the new batch is in the table

## Test plan
- Run /relevant-checks (pre-commit + agent-lint)
- test-larch-logs-batches.sh will verify the new batch is in the table
