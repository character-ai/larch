# review-and-fix.sh Contract

`skills/review-and-fix/scripts/review-and-fix.sh` has two modes:

1. Accepted-findings mode for the internal `/review-and-fix` skill, selected by `--findings-file`.
2. `/implement` orchestrator mode, selected by `--implement-tmpdir`, which runs one `review-core.sh` round and applies in-scope accepted fixes through coder dispatch.

Flags:

- `--findings-file FILE`
- `--review-tmpdir DIR`
- `--session-env-path FILE`

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `REVIEW_AND_FIX_STATUS=complete|no-findings|coder-failed`
- `FIX_COUNT=N`
- `CODER_TOOL=none|codex|cursor|claude-subagent`
- `CODER_STATUS=skipped|applied|failed|submodule-violation`
- `CODER_LOG_FILE=<path>` when a coder ran
- `SUBMODULE_SCRUB_COUNT=N`
- `SUBMODULE_REVERT_COUNT=N`

The script applies edits by dispatching Codex, Cursor, then a Claude subagent fallback. The main agent does not apply review fixes with Edit/Write.

## `/implement` orchestrator mode

Flags:

- `--implement-tmpdir DIR`
- `--mode diff`
- `--panel simple|hard`
- `--round-num N`
- `--session-env-path FILE`
- `--diff-file FILE`
- `--commit-count N`
- `--plan-file FILE`
- `--feature-file FILE`
- `--run-id ID`
- `--codex-available true|false`
- `--cursor-available true|false`

Orchestrator mode invokes `skills/review/scripts/review-core.sh` once with `--output-dir "$IMPLEMENT_TMPDIR/round-N"`. On round 1 it captures `$IMPLEMENT_TMPDIR/pre-review-untracked.txt` via `scripts/snapshot-untracked.sh` so Step 6 can detect review-created untracked files.

Exit codes:

- `0`: no accepted findings remain for this round.
- `2`: wholesale rejection, panel failure, coder failure, or submodule violation; parent `/implement` treats this as blocking.
- `3`: a coder applied accepted findings. The parent runs relevant checks and decides whether to call the script for the next round.

Additional output keys:

- `REVIEW_CORE_STATUS`
- `ROUND_NUM`
- `ACCEPTED_COUNT`
- `REJECTED_COUNT`
- `FIX_COUNT`
- `APPROVED_FIXES_FILE`
- `REJECTED_FINDINGS_FILE`
- `REVIEW_ROUND_DIR`
- `REVIEW_AND_FIX_SUMMARY_FILE`
- `ACCUMULATED_OOS_FILE`
- `CODER_TOOL`
- `CODER_STATUS`
- `CODER_LOG_FILE`
- `SUBMODULE_SCRUB_COUNT`
- `SUBMODULE_REVERT_COUNT`
- `SKIPPED_FINDING_COUNT` — count of unique `FINDING_N` ids that the coder logged as
  `SKIPPED:` and that still produced a non-empty extracted in-scope finding block; duplicate
  `SKIPPED:` lines and orphan ids with no matching `### FINDING_N:` block do not increase the
  count. Defaults to 0 when the coder did not run or reported no qualifying skips. Consumed by
  the `/implement` Step 5 bulk-skip-ratio gate.

`FIX_COUNT` is the post-submodule-scrub count actually dispatched to the coder, not the
pre-scrub accepted in-scope count. This keeps the `/implement` bulk-skip-ratio denominator
aligned with the findings file the coder actually saw.

The script writes `$IMPLEMENT_TMPDIR/review-and-fix-summary.json` atomically with `schema_version=2`, aggregate accepted/rejected counts, `rounds_completed`, latest approved-fixes path, latest round directory, accumulated OOS artifact paths, and coder/submodule status fields. Accepted OOS markdown is accumulated at `$IMPLEMENT_TMPDIR/accumulated-oos.md` and mirrored to `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for existing Step 9a.1 consumers; a JSONL audit copy is appended at `$IMPLEMENT_TMPDIR/accumulated-oos.jsonl`. That mirror copy is load-bearing: if the copy fails, the round fails instead of silently leaving the legacy mirror stale.

Submodule guard layers:

1. `scripts/scrub-submodule-paths.sh` removes findings whose paths are under submodule roots.
2. The coder prompt includes a submodule prohibition block.
3. After coder dispatch, changed paths under submodule roots are reverted with `git checkout -- <path>` and reported as `CODER_STATUS=submodule-violation`.

Harness: `skills/review-and-fix/scripts/test-review-and-fix.sh`, wired through `make test-review-and-fix`.
