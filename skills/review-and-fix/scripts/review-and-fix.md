# review-and-fix.sh Contract

`skills/review-and-fix/scripts/review-and-fix.sh` has two modes:

1. Accepted-findings mode for the internal `/review-and-fix` skill, selected by `--findings-file`.
2. `/implement` orchestrator mode, selected by `--implement-tmpdir`, which runs one `review-core.sh` round and applies in-scope accepted fixes through coder dispatch.

Flags:

- `--findings-file FILE`
- `--review-tmpdir DIR`
- `--session-env-path FILE`

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `REVIEW_AND_FIX_STATUS=complete|no-findings|coder-failed|main-agent-vote-required|no-changes|fix-applied`
- `FIX_COUNT=N`
- `CODER_TOOL=none|codex|cursor`
- `CODER_STATUS=skipped|applied|no-changes|failed|submodule-violation`
- `CODER_LOG_FILE=<path>` when a coder ran
- `CODER_COMMIT_SHA=<sha>` when the script committed the round's accepted-fixes
- `SUBMODULE_SCRUB_COUNT=N`
- `SUBMODULE_REVERT_COUNT=N`

`CODER_STATUS=applied` means the coder dispatch exited 0 AND `git status --porcelain` reports a non-empty working tree after submodule revert — i.e., real edits landed in the repo. `CODER_STATUS=no-changes` covers the case where the dispatcher exited 0 but the working tree is clean (sandbox blocked writes, coder declined every finding, etc.). The orchestrator must treat `no-changes` as terminal: a re-run of the same review would produce the same fixed point.

The script applies edits by dispatching Codex, then Cursor. The main agent does not apply review fixes with Edit/Write.

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
- `--dynamic-archetypes 0-4` (default: `4` in orchestrator mode, `0` in standalone mode)
- `--no-dynamic-archetypes` (equivalent to `--dynamic-archetypes 0`)

Orchestrator mode invokes `skills/review/scripts/review-core.sh` once with `--output-dir "$IMPLEMENT_TMPDIR/round-N"` and `--dynamic-archetypes "$DYNAMIC_ARCHETYPES"`. `DYNAMIC_ARCHETYPES` is resolved in priority order: `--dynamic-archetypes` / `--no-dynamic-archetypes` CLI args > **non-empty** `LARCH_DYNAMIC_ARCHETYPES_MAX` in the process environment (an empty export is ignored so session-env can supply the cap) > `LARCH_DYNAMIC_ARCHETYPES_MAX` in session-env > `4` (default when `--implement-tmpdir` is set) > `0` (standalone default). On round 1 it captures `$IMPLEMENT_TMPDIR/pre-review-untracked.txt` via `scripts/snapshot-untracked.sh` so Step 6 can detect review-created untracked files, and writes `$IMPLEMENT_TMPDIR/pre-review-head.txt` (current HEAD SHA) so `check-review-changes.sh --head-baseline` can detect the per-round commits this script makes during Step 5. When `--run-id` is set, both pre-review snapshot files are also flushed to the `pre-review-untracked` and `pre-review-head` run-log batches under `$IMPLEMENT_TMPDIR/larch-logs`.

After each round's `apply_findings_with_coder` dispatch finishes successfully and any submodule violations have been reverted, the script checks `git status --porcelain`. If the working tree is dirty, it stages all non-submodule changes via `git add -A` (submodule paths were already reverted, so `-A` cannot resurrect them) and calls `scripts/git-commit.sh -m "Address code review feedback (round N)"`. The commit SHA is emitted as `CODER_COMMIT_SHA`. If the working tree is clean, the script emits `CODER_STATUS=no-changes` with no commit. The coder prompt invariant ("Do NOT commit; the parent handles commits") is preserved: the bash script — not the coder — owns the commit.

Step 5 ledger marks are owned by the parent `/implement` Step 5 preamble, not by `review-and-fix.sh`. Orchestrator mode assumes the parent already emitted the best-effort `Step 5 — code review` token/timing marks before calling `scripts/run-step5-review.sh`.

Exit codes:

- `0`: no accepted findings remain for this round (`complete`), OR `main-agent-vote-required` when no voting judges were available and the parent must adjudicate the ballot, OR `no-changes` when the coder dispatch exited 0 but did not modify the working tree (the parent halts the loop — re-running the same review would produce the same fixed point), OR `fix-applied` (`REVIEW_AND_FIX_STATUS=fix-applied`) when a coder applied accepted findings AND the script committed them as `Address code review feedback (round N)` — the parent runs relevant checks and decides whether to call the script for the next round.
- `2`: panel failure, coder failure, or submodule violation; parent `/implement` treats this as blocking.

Compatibility note: out-of-tree callers must detect applied fixes via `REVIEW_AND_FIX_STATUS=fix-applied` on exit `0`. Do not rely on exit `3`; successful fix application no longer uses that exit code.

Additional output keys:

- `REVIEW_CORE_STATUS`
- `ROUND_NUM`
- `ACCEPTED_COUNT` — accepted findings for the current round only.
- `REJECTED_COUNT` — rejected findings for the current round only; strictly `rejected` outcomes only and does not include exonerated or neutral.
- `TOTAL_ACCEPTED_COUNT` — cumulative accepted findings across completed rounds after composing the aggregate review artifact.
- `TOTAL_REJECTED_COUNT` — cumulative rejected findings across completed rounds after composing the aggregate review artifact.
- `EXONERATED_COUNT` — findings with outcome `exonerated` (this round only).
- `NEUTRAL_COUNT` — findings with outcome `neutral` (this round only).
- `TOTAL_EXONERATED_COUNT` — cumulative exonerated findings across completed rounds.
- `TOTAL_NEUTRAL_COUNT` — cumulative neutral findings across completed rounds.
- `FIX_COUNT`
- `APPROVED_FIXES_FILE`
- `REJECTED_FINDINGS_FILE`
- `FINDINGS_FILE`
- `REVIEW_ROUND_DIR`
- `REVIEW_AND_FIX_SUMMARY_FILE`
- `ACCUMULATED_OOS_FILE`
- `CODER_TOOL`
- `CODER_STATUS`
- `CODER_LOG_FILE`
- `CODER_COMMIT_SHA` (only when the round committed a per-round fix commit)
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

The script writes `$IMPLEMENT_TMPDIR/review-and-fix-summary.json` atomically with `schema_version=2`, aggregate accepted/rejected/exonerated/neutral counts, `rounds_completed`, latest approved-fixes path, latest round directory, accumulated OOS artifact paths, coder/submodule status fields, and `coder_commit_sha` (latest round's per-round commit, empty string when the round produced no commit). Accepted OOS markdown is accumulated at `$IMPLEMENT_TMPDIR/accumulated-oos.md` and mirrored to `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for existing Step 9a.1 consumers; a JSONL audit copy is appended at `$IMPLEMENT_TMPDIR/accumulated-oos.jsonl`. That mirror copy is load-bearing: if the copy fails, the round fails instead of silently leaving the legacy mirror stale.

When an orchestrator round exits `0` (cap-reached, clean, or fix-applied) and `--run-id` is non-empty, the script best-effort flushes the Step 5 implement run-log batches:

- `review-findings-full` via `scripts/compose-review-findings.sh` followed by `scripts/larch-log.sh write`.
- `code-review-tally` via `scripts/write-tally.sh`, with a body containing aggregate counts derived from the composed `[code-review/accepted]` / `[code-review/rejected]` sections, sanitized review round summaries with stale per-round count bullets removed, rejected code-review findings, and the latest round voting tally when present.

Batch flushing is intentionally non-blocking: failures are suppressed so review status remains governed by the review and fix results.

Submodule guard layers:

1. `scripts/scrub-submodule-paths.sh` removes findings whose paths are under submodule roots.
2. The coder prompt includes a submodule prohibition block.
3. After coder dispatch, tracked changes under submodule roots are reverted with `git checkout -- <path>`, untracked files under submodule roots are removed, and the round is reported as `CODER_STATUS=submodule-violation`.

Harness: `skills/review-and-fix/scripts/test-review-and-fix.sh`, wired through `make test-review-and-fix`.
