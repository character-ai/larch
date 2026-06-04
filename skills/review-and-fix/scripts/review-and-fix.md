# review-and-fix.sh Contract

`skills/review-and-fix/scripts/review-and-fix.sh` has two modes:

1. Accepted-findings mode for the internal `/review-and-fix` skill, selected by `--findings-file`.
2. `/implement` orchestrator mode, selected by `--implement-tmpdir`, which runs one `review-core.sh` round and applies in-scope accepted fixes through coder dispatch. Issue-anchored `/implement` supplies `PLAN_FILE` from Preflight materialization; the outer `/implement` argv surface is positional `<issue-N>` only (no removed `--session-env` / `--issue` tokens on `/implement` itself — caller env merges via `SESSION_ENV_PATH` at Step 0).

Flags:

- `--findings-file FILE`
- `--review-tmpdir DIR`
- `--session-env-path FILE`

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `REVIEW_AND_FIX_STATUS=complete|no-findings|coder-failed|coder-main-agent-required|main-agent-vote-required|no-changes|fix-applied|converged-small-changes`
- `FIX_COUNT=N`
- `CODER_TOOL=none|codex|cursor`
- `CODER_STATUS=skipped|applied|no-changes|failed|main-agent-required|submodule-violation`
- `CODER_LOG_FILE=<path>` when a coder ran
- `CODER_COMMIT_SHA=<sha>` when the script committed the round's accepted-fixes
- `SUBMODULE_SCRUB_COUNT=N`
- `SUBMODULE_REVERT_COUNT=N`

`CODER_STATUS=applied` means the coder dispatch exited 0 AND `git status --porcelain` reports a non-empty working tree after submodule revert — i.e., real edits landed in the repo. `CODER_STATUS=no-changes` covers the case where the dispatcher exited 0 but the working tree is clean (sandbox blocked writes, coder declined every finding, etc.). The orchestrator must treat `no-changes` as terminal: a re-run of the same review would produce the same fixed point.

The script applies edits by dispatching Codex, then Cursor. The main agent does not apply review fixes with Edit/Write. `run_coder_dispatch()` acquires the per-tool KeyChain serial lock (`external_serial_lock_acquire` from `lib-cursor-launcher-common.sh` → `lib-external-launcher-common.sh`) immediately before each coder spawn and releases it asynchronously via `external_serial_lock_release_after`. The Codex branch creates a temp `CODEX_HOME`, copies `~/.codex/config.toml` when present, runs `external_prepare_codex_auth`, and passes trusted-project plus auth `-c` overrides before `--output-last-message`; non-empty `OPENAI_API_KEY` therefore uses argv-only `openai-larch-env` auth, while unset or empty falls back to the login `auth.json` symlink after stripping larch-owned env-key artifacts from copied config. The branch removes the temp home before returning or falling through to Cursor. It runs `codex exec --json --output-last-message "$round_dir/coder-codex.log" -- ...`, redirects JSONL stdout to the local-only `coder-codex.events.jsonl`, keeps wrapper diagnostics in `coder-codex.wrapper.log`, forwards `--stderr-sink "$codex_wrapper_log"` so `${round_dir}/coder-codex.log.stderr-tail` reads agent stderr on failure, and parses best-effort usage counters into the sanitized token-ledger raw bucket `codex_review_fix`. Telemetry runs even when Codex exits non-zero so failed attempts can still contribute usage; the Codex exit code remains authoritative for whether the dispatcher falls through to Cursor. Env-key failures append a redacted one-line record before Cursor fallback.
Telemetry parse diagnostics are written to the dedicated local-only `coder-codex.sidecar` file rather than the publishable wrapper log, so malformed JSONL does not leak parser spill into committed run-log surfaces.

## `/implement` orchestrator mode

Flags:

- `--implement-tmpdir DIR`
- `--mode diff`
- `--round-num N`
- `--session-env-path FILE`
- `--diff-file FILE`
- `--commit-count N`
- `--plan-file FILE`
- `--feature-file FILE`
- `--run-id ID`
- `--codex-available true|false`
- `--cursor-available true|false`
- `--dynamic-archetypes 0-8` (default: `6` in orchestrator mode when `--implement-tmpdir` is set, `0` in standalone mode)
- `--no-dynamic-archetypes` (equivalent to `--dynamic-archetypes 0`)
- Convergence (hardcoded): one non-degraded round with ≤5 non-nit accepted findings and no
  Important findings in that round triggers early-termination with
  `REVIEW_AND_FIX_STATUS=converged-small-changes`. Nit-severity accepted findings are excluded
  from the non-nit count (`accepted-findings.md` population only). Degraded rounds never qualify.

Orchestrator mode invokes `skills/review/scripts/review-core.sh` once with `--output-dir "$IMPLEMENT_TMPDIR/round-N"`, `--panel hard` (fixed internally — not a public `review-and-fix.sh` argv token), and `--dynamic-archetypes "$DYNAMIC_ARCHETYPES"`. `DYNAMIC_ARCHETYPES` is resolved in priority order: `--dynamic-archetypes` / `--no-dynamic-archetypes` CLI args > **non-empty** `LARCH_DYNAMIC_ARCHETYPES_MAX` in the process environment (an empty export is ignored so session-env can supply the cap) > `LARCH_DYNAMIC_ARCHETYPES_MAX` in session-env > `6` (default when `--implement-tmpdir` is set) > `0` (standalone default). On round 1 it captures `$IMPLEMENT_TMPDIR/pre-review-untracked.txt` via `scripts/snapshot-untracked.sh` so Step 6 can detect review-created untracked files, and writes `$IMPLEMENT_TMPDIR/pre-review-head.txt` (current HEAD SHA) so `check-review-changes.sh --head-baseline` can detect the per-round commits this script makes during Step 5. When `--run-id` is set, both pre-review snapshot files are also flushed to the `pre-review-untracked` and `pre-review-head` run-log batches under `$IMPLEMENT_TMPDIR/larch-logs`.

Round mode (`round_num > 0`) owns commits inside `apply_findings_with_coder` after submodule revert. The coder prompt invariant ("Do NOT commit; the parent handles commits") is preserved: the bash script — not the coder — owns the commit. When `git status --porcelain` is dirty, the script stages only paths from the post-dispatch tracked delta (`coder-stage-paths.txt` manifest) via `git add -- <path>` (submodule paths were already reverted) and calls `scripts/git-commit.sh --only --pathspec-from-file "$round_dir/coder-stage-paths.txt" -m "Address code review feedback (round N)"`, emitting `CODER_COMMIT_SHA`. Pre-existing snapshotted paths the coder left unchanged are excluded from the outside-manifest fail-closed check, warned via `larch_err`, and left uncommitted. Only genuinely-new tracked dirt outside the manifest still fails closed at the pre-commit guard (`CODER_STATUS=failed`, return `2`). Untracked-only porcelain with an empty manifest (coder created only new files, no tracked delta) also fails closed at `stage_round_dirty_paths` (`CODER_STATUS=failed`, return `2`) — round mode does not use `git add -A`. When the tree is clean after dispatch, it emits `CODER_STATUS=no-changes` with no commit. Findings mode (no `round_num`) skips round commits; the parent caller owns staging and commit.

**Pre-coder carryover snapshots** (issue #3272, relocated for snapshot integrity): immediately before coder dispatch, the script writes `pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, and `pre-coder-path-diffs/*.patch` under `pre_coder_snapshot_dir "$round_dir"`. When the round parent is outside the current repo workspace, this resolves to `$(dirname "$round_dir")/.pre-coder-snapshots/$(basename "$round_dir")`, outside the Codex coder's `--add-dir "$round_dir"` grant. If the round parent is inside `$PWD`, the helper relocates snapshots under `${TMPDIR:-/tmp}/larch-pre-coder-snapshots/<hash>/$(basename "$round_dir")` so the snapshot is outside both the round-dir grant and the repo-root `--add-dir "$PWD"` grant. The `<hash>` is the `cksum` of the resolved round-parent path (disambiguates same-basename round dirs). Relocated dirs live **outside** `IMPLEMENT_TMPDIR`, so `cleanup-tmpdir.sh` does not reap them; the OS `$TMPDIR` policy does. Writers call `clear_stale_pre_coder_snapshot_artifacts` before each regeneration so stale `chmod 0444` files cannot block redirects. After all snapshot writes for a round complete, `harden_pre_coder_snapshot_perms` sets `chmod 0444` on snapshot **files** only (never directories); round cleanup (`rm -rf`) still removes read-only files when the parent directory is writable. `post-coder-head.txt` and `coder-stage-paths.txt` remain in `round_dir` (post-dispatch or coder outputs); `post-coder-head.txt` is written and chmod'd only when `status == fix-applied`. **Sandbox-confinement trust boundary:** snapshot integrity assumes `codex exec --full-auto` confines writes to declared `--add-dir`/workspace roots; relocation and `chmod 0444` are defense-in-depth if the sandbox is more permissive; no CI sandbox-confinement probe. **Invariant:** pre-coder snapshots must stay outside every Codex `--add-dir` / workspace root the dispatcher grants; relocating snapshots under `round_dir` or `$PWD` would let a hostile coder tamper with carryover classification.

**Round-mode post-commit residue re-check** (issue #3209, `round_num > 0` only): after the round commit, when `round_has_non_carryover_tracked_residue` finds any tracked path from `capture_round_tracked_paths` that is not pre-coder carryover — **including manifest-listed paths** re-dirtied by hooks — the script performs one guarded follow-up stage-from-manifest plus `git-commit.sh --only --pathspec-from-file "$round_dir/coder-stage-paths.txt" -m "Address code review feedback (round N) — follow-up"` and refreshes `CODER_COMMIT_SHA`. Carryover-only tracked dirt after the primary or follow-up commit skips follow-up and does not fail the round. Follow-up stage or commit failure emits `CODER_STATUS=failed` and returns `2` immediately. If non-carryover tracked residue remains after follow-up, it emits `CODER_STATUS=failed` and returns `2` (fail-closed; no warn-and-continue `applied`). Findings mode skips this block; `ship-pr.sh` Option A backstops persistent residue at the rebase drop site.

Step 5 ledger marks are owned by the parent `/implement` Step 5 preamble, not by `review-and-fix.sh`. Orchestrator mode assumes the parent already emitted the best-effort `Step 5 — code review` token/timing marks before calling `scripts/run-step5-review.sh`.

Exit codes:

- `0`: no accepted findings remain for this round (`complete`), OR `main-agent-vote-required` when no voting judges were available and the parent must adjudicate the ballot, OR `coder-main-agent-required` (#3207) when no external coder could apply the accepted fixes (Codex → Cursor both exhausted) and the parent main agent must apply them itself — the Claude tier of the coder waterfall, OR `no-changes` when the coder dispatch exited 0 but did not modify the working tree (the parent halts the loop — re-running the same review would produce the same fixed point), OR `fix-applied` (`REVIEW_AND_FIX_STATUS=fix-applied`) when a coder applied accepted findings AND the script committed them as `Address code review feedback (round N)` — the parent runs relevant checks and decides whether to call the script for the next round, OR `converged-small-changes` when one non-degraded round had ≤5 non-nit accepted findings and no Important findings in that round (nits excluded from the count) — the parent must stop the review loop.
- `2`: panel failure, coder failure, submodule violation, or persistent tracked porcelain after round-mode follow-up (`CODER_STATUS=failed`); parent `/implement` treats this as blocking.

Compatibility note: out-of-tree callers must detect applied fixes via `REVIEW_AND_FIX_STATUS=fix-applied` on exit `0`. Do not rely on exit `3`; successful fix application no longer uses that exit code.

Additional output keys:

- `REVIEW_CORE_STATUS`
- `ROUND_NUM`
- `ACCEPTED_COUNT` — accepted findings for the current round only.
- `REJECTED_COUNT` — rejected findings for the current round only (operator-facing total: every finding that did not meet the acceptance threshold, including split-panel and exonerated patterns).
- `TOTAL_ACCEPTED_COUNT` — cumulative accepted findings across completed rounds after composing the aggregate review artifact.
- `TOTAL_REJECTED_COUNT` — cumulative rejected findings across completed rounds after composing the aggregate review artifact.
- `EXONERATED_COUNT` — informational sub-count for this round (`exonerated_count ≤ rejected_count`).
- `NEUTRAL_COUNT` — internal split-panel tally for this round (`NEUTRAL_COUNT` KV; not mirrored into `review-and-fix-summary.json`).
- `TOTAL_EXONERATED_COUNT` — cumulative exonerated sub-counts across completed rounds.
- `TOTAL_NEUTRAL_COUNT` — cumulative internal split-panel tally across completed rounds.
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
- `DEGRADED_ROUND=true|false` — `true` when the round's voting panel was degraded (the
  `⚠ Degraded code-review panel` banner was present in `voting-tally.md`) after any applicable
  panel retry. When `true`, the orchestrator should skip counting this round toward the review
  cap and toward the convergence calculation.

`FIX_COUNT` is the post-submodule-scrub count actually dispatched to the coder, not the
pre-scrub accepted in-scope count. This keeps the `/implement` bulk-skip-ratio denominator
aligned with the findings file the coder actually saw.

The script writes `$IMPLEMENT_TMPDIR/review-and-fix-summary.json` atomically with `schema_version=3`, aggregate accepted/rejected/exonerated counts, `rounds_completed`, latest approved-fixes path, latest round directory, accumulated OOS artifact paths, coder/submodule status fields, and `coder_commit_sha` (latest round's per-round commit, empty string when the round produced no commit). Accepted OOS markdown is accumulated at `$IMPLEMENT_TMPDIR/accumulated-oos.md` and mirrored to `$IMPLEMENT_TMPDIR/oos-accepted-review.md` for existing Step 9a.1 consumers; a JSONL audit copy is appended at `$IMPLEMENT_TMPDIR/accumulated-oos.jsonl`. That mirror copy is load-bearing: if the copy fails, the round fails instead of silently leaving the legacy mirror stale.

Rejected code-review markdown is accumulated at `$IMPLEMENT_TMPDIR/rejected-findings.md`. When any round has a non-empty `round-N/rejected-findings-full.md`, the run-root file is rewritten as a full-detail aggregate with a top-level `# Rejected Findings` heading and `## Round N` sections in numeric round order. If no full-detail round files exist, the script falls back to the latest round's compact `rejected-findings.md` ledger for backward compatibility. `$IMPLEMENT_TMPDIR/rejected-findings-full.md` remains the latest round's full-prose artifact for existing tally consumers.

When an orchestrator round exits `0` (cap-reached, clean, or fix-applied) and `--run-id` is non-empty, the script best-effort flushes the Step 5 implement run-log batches:

- `review-findings-full` via `scripts/compose-review-findings.sh` followed by `scripts/larch-log.sh write`.
- `code-review-tally` via `scripts/write-tally.sh`, with a body containing aggregate counts derived from the composed `[code-review/accepted]` / `[code-review/rejected]` sections, sanitized review round summaries with stale per-round count bullets removed, rejected code-review findings, and the latest round voting tally when present.
- `review-scout-manifest` via `scripts/larch-log.sh write` when `SCOUT_STATUS` from `review-core.sh` is non-empty and not `na`. The payload is `{"status":"<status>","dynamic_slots":<N>,"manifest_basename":"<basename>","yield_tsv_basename":"<basename>"}`. Invalid scout payload inputs or flush failure are logged to `execution-issues.md` under `Warnings` and do not fail the round.

Batch flushing is intentionally non-blocking: failures are suppressed so review status remains governed by the review and fix results.

Submodule guard layers:

1. `scripts/scrub-submodule-paths.sh` removes findings whose paths are under submodule roots.
2. The coder prompt includes a submodule prohibition block.
3. After coder dispatch, tracked changes under submodule roots are reverted with `git checkout -- <path>`, untracked files under submodule roots are removed, and the round is reported as `CODER_STATUS=submodule-violation`.

The script emits breadcrumbs at major round-loop and coder-dispatch boundaries through `larch_err`, so they are operator-visible on stderr and mirrored into the quiet log:

- `→ review-and-fix: round N` — on `run_implement_round` entry
- `→ review-and-fix: round N — X accepted, Y rejected` — after review-core tally reads finish
- `→ review-and-fix: dispatching coder (N fixes)` — before `run_coder_dispatch`
- `→ review-and-fix: <tool> applied N fixes (commit <sha>)` — after a successful coder commit
- `⚠ review-and-fix: pre-existing dirty path carried over (not committed): <path>` — when round mode skips unchanged pre-coder carryover dirt
- `⚠ review-and-fix: round N left tracked changes uncommitted after follow-up` — when non-carryover tracked residue remains after the single follow-up commit
- `⚠ review-and-fix: coder dispatch failed (both codex and cursor)` — when both coders fail
- `⚠ review-and-fix: reviewer panel failed (>50% slots)` — on `core_status=panel-failed`
- `⚠ review-and-fix: round N — coder dispatch exited 0 but did not modify the working tree; halting loop` — when the coder reports success but makes no repo changes

Harness: `skills/review-and-fix/scripts/test-review-and-fix.sh`, wired through `make test-review-and-fix`.
