# review-and-fix.sh Contract

`skills/review-and-fix/scripts/review-and-fix.sh` has two modes:

1. Fixer-enumeration mode for the internal `/review-and-fix` skill.
2. `/implement` orchestrator mode, selected by `--implement-tmpdir`, which runs one `review-core.sh` round and emits a bounded machine contract for the parent prompt to apply accepted fixes.

Flags:

- `--findings-file FILE`
- `--review-tmpdir DIR`
- `--session-env-path FILE`

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `FINDING_ID=<id>` once per accepted finding
- `REVIEW_AND_FIX_STATUS=complete|no-findings`
- `FIX_COUNT=N`
- `FINDING_IDS_FILE=<path>` when findings exist

The script does not apply edits. The `/review-and-fix` prompt wrapper reads each `$REVIEW_TMPDIR/FINDING_N.fixer.env`, validates `PATH_VALID=true`, applies code edits with Edit/Write tools, then records the outcome through `call-fixer.sh --mark-applied` or `--mark-skipped`.

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
- `2`: wholesale rejection; parent `/implement` treats this as blocking.
- `3`: accepted findings exist. The parent applies fixes from `APPROVED_FIXES_FILE`, then runs relevant checks and decides whether to call the script for the next round.

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

The script writes `$IMPLEMENT_TMPDIR/review-and-fix-summary.json` atomically with `schema_version=1`, aggregate accepted/rejected counts, `rounds_completed`, latest approved-fixes path, latest round directory, and accumulated OOS artifact paths. Accepted OOS markdown is accumulated at `$IMPLEMENT_TMPDIR/accumulated-oos.md` and mirrored to `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for existing Step 9a.1 consumers; a JSONL audit copy is appended at `$IMPLEMENT_TMPDIR/accumulated-oos.jsonl`.

Harness: `skills/review-and-fix/scripts/test-review-and-fix.sh`, wired through `make test-review-and-fix`.
