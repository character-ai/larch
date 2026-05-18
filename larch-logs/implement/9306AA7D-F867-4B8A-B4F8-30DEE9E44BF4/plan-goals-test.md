## Goal
Commit voter response files and other high-diagnostic-value review artifacts to larch-logs/implement/<RUN_ID>/round-<N>/

## Implementation Plan

Commit per-round reviewer artifacts and per-run setup files to larch-logs so they survive TMPDIR cleanup and enable post-merge diagnosis of review quality issues.

### Files to create
1. `scripts/lib-redact.sh` — source-able library with two trimmers:
   - `larch_redact_strip_meta_cmd_json INPUT OUTPUT` — strip `CMD_JSON=...` line from .meta sidecars
   - `larch_redact_strip_cursor_json_result INPUT OUTPUT` — strip `.result` field from Cursor JSON sidecars (jq del(.result) with fallback)
2. `scripts/lib-redact.md` — sibling doc
3. `scripts/test-larch-log-write-round.sh` — regression test

### Files to modify
4. `scripts/larch-log.sh` — add `write-round` subcommand:
   - Args: `--log-root D --skill S --run-id R --round N --source-dir DIR`
   - Reads per-round include list from `--source-dir`
   - Applies trimmers (.meta → strip CMD_JSON; cursor .json → strip result)
   - Applies `larch_log_redact_file` (tmpdir + secrets redaction)
   - Writes to `<log_root>/<skill>/<run_id>/round-<N>/`
   - No commit; just writes to larch-logs tmpdir (existing commit picks them up)
5. `scripts/larch-log-batches.sh` — add per-run batch slugs:
   parent-issue, pre-review-head, pre-review-untracked, codex-impl-transcript,
   codex-impl-transcript-prompt, codex-commit-message, codex-impl-manifest-raw
6. `skills/review/scripts/review-core.sh` — call write-round at end of each round
   (after tally+emit complete, before final emit_kv exit)
7. `skills/review-and-fix/scripts/review-and-fix.sh` — flush pre-review-head.txt
   and pre-review-untracked.txt via larch-log.sh write at round 1 init
8. `scripts/run-step1-plan-log.sh` — flush parent-issue.md after plan batch write
9. `skills/implement/SKILL.md` — add Codex transcript file writes to pre-bump flush section
10. `docs/run-logs.md` — document round-<N>/ directory layout and per-file contract

### Sibling docs to update
- `scripts/larch-log.md` — add write-round subcommand
- `skills/review/scripts/review-core.md` — add write-round call note
- `skills/review-and-fix/scripts/review-and-fix.md` — add pre-review snapshot flush note
- `scripts/run-step1-plan-log.md` — add parent-issue.md flush note

### Constraint
New writes land in TMPDIR larch-logs dir only; existing `larch-log.sh commit` (called at Step 7a pre-bump flush) picks them up — no new per-round commit.


## Test plan
- `scripts/test-larch-log-write-round.sh`: verify include list lands, trimmers strip correctly, exclude list stays out, redaction fires; test with and without optional coder files; test round dir naming
- `make lint` (pre-commit + agent-lint passes)
